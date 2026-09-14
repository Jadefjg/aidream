from __future__ import annotations

from ..config import settings


def quota_to_usd(quota: int) -> float:
    return round(quota / settings.quota_per_unit, 2)


def usd_to_quota(amount: float) -> int:
    return int(round(amount * settings.quota_per_unit))


def estimate_chat_quota(model, prompt_tokens: int, completion_tokens: int, group_ratio: float) -> int:
    if model.quota_type == 1:
        dollars = model.model_price * group_ratio
        return max(1, usd_to_quota(dollars))
    input_per_m = 2.0 * model.model_ratio * group_ratio
    output_per_m = 2.0 * model.model_ratio * model.completion_ratio * group_ratio
    dollars = (prompt_tokens / 1_000_000) * input_per_m + (completion_tokens / 1_000_000) * output_per_m
    return max(1, usd_to_quota(dollars))


def mask_key(key: str) -> str:
    if len(key) <= 10:
        return key[:3] + "********"
    body = key[3:] if key.startswith("sk-") else key
    return body[:4] + "********..."
