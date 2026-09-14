from __future__ import annotations

import asyncio
import random
from typing import Any
from collections.abc import AsyncIterator

import httpx
from sqlalchemy.orm import Session

from ..config import settings
from ..models import UpstreamChannel, utcnow


def _csv(value: str) -> set[str]:
    return {x.strip() for x in (value or "").replace("\n", ",").split(",") if x.strip()}


def candidates(db: Session, group: str, model: str) -> list[UpstreamChannel]:
    rows = db.query(UpstreamChannel).order_by(UpstreamChannel.priority.desc(), UpstreamChannel.id).all()
    out = []
    for row in rows:
        if row.status != 1:
            if row.status == 2 and row.last_failure and utcnow() - row.last_failure >= settings.channel_circuit_cooldown_seconds:
                row.status = 1; row.failure_count = 0; db.commit()
            else:
                continue
        groups, models = _csv(row.groups), _csv(row.models)
        if groups and group not in groups and "*" not in groups:
            continue
        if models and model not in models and "*" not in models:
            continue
        out.append(row)
    weighted = []
    for row in out:
        weighted.extend([row] * max(1, min(row.weight, 20)))
    random.shuffle(weighted)
    return sorted(weighted, key=lambda x: x.priority, reverse=True)


def configured(db: Session, group: str, model: str) -> bool:
    return bool(candidates(db, group, model) or (settings.upstream_base_url and settings.upstream_api_key))


async def request_json(db: Session, group: str, model: str, path: str, payload: dict[str, Any], *, timeout: float = 90) -> dict:
    rows = candidates(db, group, model)
    if not rows and settings.upstream_base_url and settings.upstream_api_key:
        rows = [None]
    last: Exception | None = None
    for row in rows:
        base = (row.base_url if row else settings.upstream_base_url).rstrip("/")
        key = row.api_key if row else settings.upstream_api_key
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(f"{base}/{path.lstrip('/')}", headers={"Authorization": f"Bearer {key}"}, json=payload)
                response.raise_for_status()
                if row:
                    row.failure_count = 0
                    db.commit()
                return response.json()
        except Exception as exc:
            last = exc
            if row:
                row.failure_count += 1
                row.last_failure = utcnow()
                if row.failure_count >= settings.channel_circuit_threshold:
                    row.status = 2
                db.commit()
            await asyncio.sleep(0)
    raise last or RuntimeError("没有可用上游渠道")


async def request_bytes(db: Session, group: str, model: str, path: str, payload: dict[str, Any], *, timeout: float = 90) -> tuple[bytes, str]:
    rows = candidates(db, group, model)
    if not rows and settings.upstream_base_url and settings.upstream_api_key:
        rows = [None]
    last: Exception | None = None
    for row in rows:
        base = (row.base_url if row else settings.upstream_base_url).rstrip("/")
        key = row.api_key if row else settings.upstream_api_key
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(f"{base}/{path.lstrip('/')}", headers={"Authorization": f"Bearer {key}"}, json=payload)
                response.raise_for_status()
                return response.content, response.headers.get("content-type", "application/octet-stream")
        except Exception as exc:
            last = exc
            if row:
                row.failure_count += 1
                row.last_failure = utcnow()
                if row.failure_count >= settings.channel_circuit_threshold:
                    row.status = 2
                db.commit()
    raise last or RuntimeError("没有可用上游渠道")


async def stream_request(db: Session, group: str, model: str, path: str, payload: dict[str, Any], *, timeout: float = 90) -> AsyncIterator[bytes]:
    rows = candidates(db, group, model)
    if not rows and settings.upstream_base_url and settings.upstream_api_key:
        rows = [None]
    if not rows:
        raise RuntimeError("没有可用上游渠道")
    row = rows[0]
    base = (row.base_url if row else settings.upstream_base_url).rstrip("/")
    key = row.api_key if row else settings.upstream_api_key
    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream("POST", f"{base}/{path.lstrip('/')}", headers={"Authorization": f"Bearer {key}"}, json=payload) as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes():
                yield chunk
