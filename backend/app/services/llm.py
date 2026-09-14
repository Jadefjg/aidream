import hashlib
import math
import struct
import zlib
from typing import AsyncIterator

from ..config import settings


async def generate_chat_text(model: str, messages: list[dict]) -> str:
    last = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            last = str(msg.get("content") or "")
            break
    last = last.strip() or "你好"
    if settings.upstream_base_url and settings.upstream_api_key:
        import httpx

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{settings.upstream_base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {settings.upstream_api_key}"},
                json={"model": model, "messages": messages, "stream": False},
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
    return (
        f"我是 THINK-AI 本地网关中的 `{model}`。\n\n"
        f"已收到你的问题：\n\n> {last[:800]}\n\n"
        "当前运行的是 1:1 复刻演示环境。若配置 upstream_base_url 与 upstream_api_key，"
        "将自动转发到上游大模型；否则由本地网关返回结构化演示回复，"
        "计费、日志、令牌与额度逻辑与 ThinkAI / New API 保持一致。"
    )


async def stream_chat_text(text: str) -> AsyncIterator[str]:
    buf = ""
    for ch in text:
        buf += ch
        if ch in "，。！？、\n " or len(buf) >= 8:
            yield buf
            buf = ""
    if buf:
        yield buf


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def generate_image_png(prompt: str, width: int, height: int) -> bytes:
    width = max(64, min(width, 1024))
    height = max(64, min(height, 1024))
    seed = int(hashlib.md5(prompt.encode()).hexdigest()[:8], 16)
    rows = []
    for y in range(height):
        row = [0]
        for x in range(width):
            n = (x * 13 + y * 7 + seed) & 255
            row.extend((20 + (n // 5), 40 + (n // 4), 90 + (n // 3)))
        rows.append(bytes(row))
    raw = b"".join(rows)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += _png_chunk(b"IHDR", ihdr)
    png += _png_chunk(b"IDAT", zlib.compress(raw, 6))
    png += _png_chunk(b"IEND", b"")
    return png


def parse_size(size: str, quality: str) -> tuple[int, int]:
    mapping = {
        "1:1": (512, 512),
        "16:9": (640, 360),
        "4:3": (512, 384),
        "3:4": (384, 512),
        "9:16": (360, 640),
        "1024x1024": (512, 512),
        "1792x1024": (640, 360),
        "1024x1792": (360, 640),
    }
    w, h = mapping.get(size, (512, 512))
    scale = {"1k": 1.0, "2k": 1.25, "4k": 1.5}.get(quality, 1.0)
    return int(w * scale), int(h * scale)


def fake_embedding(text: str, dim: int = 8) -> list[float]:
    digest = hashlib.sha256(text.encode()).digest()
    vals = [(digest[i % len(digest)] / 255.0) * 2 - 1 for i in range(dim)]
    norm = math.sqrt(sum(v * v for v in vals)) or 1
    return [round(v / norm, 6) for v in vals]
