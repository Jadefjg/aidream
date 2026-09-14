from __future__ import annotations

import json
import secrets
from ipaddress import ip_address, ip_network

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models import ChannelGroup, Log, ModelPrice, Token, User, utcnow
from .billing import estimate_chat_quota

LOG_TOPUP = 1
LOG_CONSUME = 2
LOG_MANAGE = 3
LOG_SYSTEM = 4
LOG_ERROR = 5
LOG_LOGIN = 7


def resolve_group(token: Token | None, user: User, override: str = "") -> str:
    # API 密钥的分组优先于请求体，避免操练场/客户端用错倍率
    if token and token.group:
        return token.group
    if override:
        return override
    return user.group or "default"


def assert_token_usable(token: Token | None) -> None:
    if not token:
        return
    if token.status != 1:
        raise HTTPException(status_code=401, detail="Incorrect API key provided")
    if token.expired_time not in (-1, 0) and token.expired_time < utcnow():
        raise HTTPException(status_code=403, detail="This token has expired")


def group_ratio(db: Session, name: str) -> float:
    g = db.query(ChannelGroup).filter(ChannelGroup.name == name).first()
    return g.ratio if g else 1.0


def group_models(db: Session, group_name: str) -> list[ModelPrice]:
    rows = db.query(ModelPrice).all()
    return [m for m in rows if group_name in (m.enable_groups or "").split(",")]


def assert_model_in_group(model: ModelPrice, group_name: str) -> None:
    groups = [g for g in (model.enable_groups or "").split(",") if g]
    if groups and group_name not in groups:
        raise HTTPException(status_code=403, detail=f"当前分组「{group_name}」不可用模型 {model.model_name}，请更换令牌分组")


def assert_token_model(token: Token | None, model_name: str) -> None:
    if not token:
        return
    limits = [x.strip() for x in (token.models or "").split(",") if x.strip()]
    if limits and model_name not in limits:
        raise HTTPException(status_code=403, detail=f"该令牌未授权模型 {model_name}")


def assert_token_ip(token: Token | None, ip: str) -> None:
    if not token or not token.subnet or not ip:
        return
    allowed = [x.strip() for x in token.subnet.replace("\n", ",").split(",") if x.strip()]
    if not allowed:
        return
    try:
        addr = ip_address(ip)
    except ValueError:
        return
    for item in allowed:
        try:
            if "/" in item and addr in ip_network(item, strict=False):
                return
            if str(addr) == item:
                return
        except ValueError:
            if item == ip:
                return
    raise HTTPException(status_code=403, detail="请求 IP 不在令牌白名单内")


def add_log(db: Session, **kwargs) -> Log:
    log = Log(**kwargs)
    db.add(log)
    return log


def plan_consume(
    db: Session,
    *,
    user: User,
    token: Token | None,
    model: ModelPrice,
    prompt_tokens: int,
    completion_tokens: int,
    ip: str,
    group: str = "",
    n: int = 1,
) -> tuple[str, int, float]:
    assert_token_usable(token)
    group_name = resolve_group(token, user, group)
    assert_model_in_group(model, group_name)
    assert_token_model(token, model.model_name)
    assert_token_ip(token, ip)
    ratio = group_ratio(db, group_name)
    per_call = estimate_chat_quota(model, prompt_tokens, completion_tokens, ratio)
    quota = per_call * max(1, n)
    if user.quota < quota:
        raise HTTPException(status_code=403, detail="用户额度不足")
    if token and not token.unlimited_quota and (token.remain_quota or 0) < quota:
        raise HTTPException(status_code=403, detail="令牌额度不足")
    return group_name, quota, ratio


def consume(
    db: Session,
    *,
    user: User,
    token: Token | None,
    model: ModelPrice,
    prompt_tokens: int,
    completion_tokens: int,
    stream: bool,
    ip: str,
    group: str = "",
    n: int = 1,
    path: str = "/v1/chat/completions",
) -> tuple[int, str]:
    group_name, quota, ratio = plan_consume(
        db,
        user=user,
        token=token,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        ip=ip,
        group=group,
        n=n,
    )
    user.quota -= quota
    user.used_quota += quota
    user.request_count += 1
    if token:
        token.accessed_time = utcnow()
        token.used_quota = (token.used_quota or 0) + quota
        if not token.unlimited_quota:
            token.remain_quota -= quota
            if token.remain_quota <= 0:
                token.status = 4  # exhausted
    request_id = secrets.token_hex(10)
    add_log(
        db,
        user_id=user.id,
        type=LOG_CONSUME,
        username=user.username,
        token_name=token.name if token else "playground",
        model_name=model.model_name,
        quota=quota,
        prompt_tokens=prompt_tokens * max(1, n),
        completion_tokens=completion_tokens * max(1, n),
        use_time=max(1, completion_tokens // 20),
        is_stream=stream,
        token_id=token.id if token else 0,
        group=group_name,
        ip=ip,
        request_id=request_id,
        other=json.dumps({"group_ratio": ratio, "request_path": path, "n": n}),
    )
    db.commit()
    db.refresh(user)
    if token:
        db.refresh(token)
    return quota, request_id
