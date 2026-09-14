import json
import secrets

from sqlalchemy.orm import Session

from .auth import hash_password
from .config import settings
from .models import ChannelGroup, Log, ModelPrice, Redemption, Token, User, utcnow

GROUPS = [
    ("default", "支持GPT、Gemini等主流模型", 0.4),
    ("Codex（推荐）", "GPT plus渠道", 0.4),
    ("Claude Lite", "第三方Kiro渠道", 0.5),
    ("Claude Max（仅限VIP用户使用）", "Claude 满血渠道", 2.0),
    ("Deepseek-官方", "Deepseek官方直连", 5.44),
    ("GLM-官方", "GLM官方直连", 5.44),
    ("Gemini", "Gemini 第三方渠道", 0.6),
    ("Grok image", "Grok生图模型", 0.5),
    ("Nano Banana Pro", "Nano banana 2，支持1、2、4k", 0.5),
    ("OpenAI-image2生图专用", "支持生成1K/2K", 0.5),
    ("Qwen-阿里", "Qwen官方直连", 6.125),
    ("Super Grok", "Super Grok号池，支持生图", 0.03),
    ("gpt-image-2-1k", "仅支持1k生图（单边分辨率<=1024）", 0.5),
    ("gpt-image-2-2k", "仅支持2k生图（单边分辨率<=2048）", 0.5),
    ("gpt-image-2-4k", "仅支持4k生图", 0.5),
    ("视频模型", "第三方视频模型", 4.25),
    ("视频模型(高质)", "第三方视频模型", 4.4),
    ("ch01", "视频渠道 01", 4.25),
    ("ch03", "视频渠道 03", 4.25),
    ("ch07", "视频渠道 07", 4.25),
    ("ch08", "视频渠道 08", 4.25),
    ("ch09", "视频渠道 09", 4.25),
]

# quota_type 0=token, 1=per call
MODELS = [
    ("gpt-5.3-codex", "OpenAI", 0, 0.875, 0, 8, "default,Codex（推荐）", "openai"),
    ("gpt-5.3-codex-spark", "OpenAI", 0, 37.5, 0, 8, "default,Codex（推荐）", "openai"),
    ("gpt-5.4", "OpenAI", 0, 37.5, 0, 6, "default,Codex（推荐）", "openai"),
    ("gpt-5.4-mini", "OpenAI", 0, 0.375, 0, 6, "default,Codex（推荐）", "openai"),
    ("gpt-5.5", "OpenAI", 0, 37.5, 0, 6, "default,Codex（推荐）", "openai"),
    ("gpt-5.6-luna", "OpenAI", 0, 37.5, 0, 6, "default,Codex（推荐）", "openai"),
    ("gpt-5.6-sol", "OpenAI", 0, 37.5, 0, 6, "default,Codex（推荐）", "openai"),
    ("gpt-5.6-terra", "OpenAI", 0, 37.5, 0, 6, "default,Codex（推荐）", "openai"),
    ("gpt-6-astra", "OpenAI", 0, 5, 0, 5, "default,Codex（推荐）", "openai"),
    ("gpt-image-2", "OpenAI", 1, 0, 0.22, 0, "OpenAI-image2生图专用", "openai"),
    ("gpt-image-2-1k", "OpenAI", 1, 0, 0.12, 0, "gpt-image-2-1k", "openai"),
    ("gpt-image-2-2k", "OpenAI", 1, 0, 0.16, 0, "gpt-image-2-2k", "openai"),
    ("gpt-image-2-4k", "OpenAI", 1, 0, 0.20, 0, "gpt-image-2-4k", "openai"),
    ("tts-1", "OpenAI", 1, 0, 0.015, 0, "default,Codex（推荐）", "openai"),
    ("whisper-1", "OpenAI", 1, 0, 0.006, 0, "default,Codex（推荐）", "openai"),
    ("text-embedding-3-small", "OpenAI", 0, 0.01, 0, 1, "default,Codex（推荐）", "openai"),
    ("rerank-multilingual-v3.0", "Cohere", 1, 0, 0.002, 0, "default,Codex（推荐）", "openai"),
    ("codex-auto-review", "OpenAI", 0, 2.5, 0, 1, "default,Codex（推荐）", "openai"),
    ("claude-opus-5", "Anthropic", 0, 2.5, 0, 5, "Claude Lite,Claude Max（仅限VIP用户使用）", "openai,anthropic"),
    ("claude-opus-4-6", "Anthropic", 0, 2.5, 0, 5, "Claude Lite,Claude Max（仅限VIP用户使用）", "openai,anthropic"),
    ("claude-opus-4-7", "Anthropic", 0, 2.5, 0, 5, "Claude Lite,Claude Max（仅限VIP用户使用）", "openai,anthropic"),
    ("claude-opus-4-8", "Anthropic", 0, 2.5, 0, 5, "Claude Lite,Claude Max（仅限VIP用户使用）", "openai,anthropic"),
    ("claude-sonnet-4-6", "Anthropic", 0, 1.5, 0, 5, "Claude Lite,Claude Max（仅限VIP用户使用）", "openai,anthropic"),
    ("claude-sonnet-5", "Anthropic", 0, 37.5, 0, 1, "Claude Lite", "openai,anthropic"),
    ("claude-fable-5", "Anthropic", 0, 5, 0, 5, "Claude Lite,Claude Max（仅限VIP用户使用）", "openai,anthropic"),
    ("deepseek-v4-flash", "DeepSeek", 0, 0.07, 0, 2, "Deepseek-官方", "openai"),
    ("deepseek-v4-pro", "DeepSeek", 0, 37.5, 0, 1, "Deepseek-官方", "openai"),
    ("grok-4.5", "xAI", 0, 37.5, 0, 1, "Super Grok", "openai"),
    ("grok-4.6", "xAI", 0, 37.5, 0, 1, "Super Grok", "openai"),
    ("grok-imagine-image", "xAI", 1, 0, 0.18, 0, "Grok image", "openai"),
    ("glm-5.1", "智谱", 0, 37.5, 0, 1, "GLM-官方", "openai"),
    ("glm-5.2", "智谱", 0, 0.588, 0, 3.5, "GLM-官方", "openai"),
    ("qwen3.7-plus", "阿里巴巴", 0, 37.5, 0, 1, "Qwen-阿里", "openai"),
    ("qwen3.7-max", "阿里巴巴", 0, 0.835, 0, 3.0, "Qwen-阿里", "openai"),
    ("nano-banana-pro", "未知供应商", 1, 0, 0.2, 0, "Nano Banana Pro", "openai"),
    ("ch0101-sd-2.0-720p", "未知供应商", 1, 0, 2.61, 0, "视频模型,ch01", "openai"),
    ("ch0101-sd-2.0-1080p", "未知供应商", 1, 0, 5.5, 0, "视频模型,ch01", "openai"),
    ("ch0102-sd-2.0-720p", "未知供应商", 1, 0, 3.06, 0, "视频模型,ch01", "openai"),
    ("ch0102-sd-2.0-1080p", "未知供应商", 1, 0, 3.45, 0, "视频模型,ch01", "openai"),
    ("ch0103-sd-2.0-720p", "未知供应商", 0, 37.5, 0, 1, "视频模型,ch01", "openai"),
    ("ch0301-sd-2.0-720p", "未知供应商", 1, 0, 2.14, 0, "视频模型,ch03", "openai"),
    ("ch0301-sd-2.0-1080p", "未知供应商", 1, 0, 5.27, 0, "视频模型,ch03", "openai"),
    ("ch0301-sd-2.0-fast-720p", "未知供应商", 1, 0, 1.81, 0, "视频模型,ch03", "openai"),
    ("ch0702-sd-2.0-720p", "未知供应商", 1, 0, 1.97, 0, "视频模型,ch07", "openai"),
    ("ch0703-sd-2.5-720p", "未知供应商", 1, 0, 10.54, 0, "视频模型", "openai"),
    ("ch8-sd-2.0-u2-720p", "未知供应商", 1, 0, 1.48, 0, "视频模型,ch08", "openai"),
    ("ch8-sd-2.0-u3-720p", "未知供应商", 1, 0, 1.97, 0, "视频模型,ch08", "openai"),
    ("ch9-sd-2.0-ck-720p", "未知供应商", 1, 0, 1.97, 0, "视频模型,ch09", "openai"),
    ("ch9-sd-2.0-ck2-720p", "未知供应商", 1, 0, 1.97, 0, "视频模型,ch09", "openai"),
    ("ch0904-sd-2.0-720p", "未知供应商", 1, 0, 1.81, 0, "视频模型", "openai"),
    ("ch0905-sd-2.0-720p", "未知供应商", 1, 0, 1.64, 0, "视频模型", "openai"),
    ("ch0906-sd-2.0-720p", "未知供应商", 1, 0, 1.97, 0, "视频模型", "openai"),
    ("ch0907-sd-2.5-720p", "未知供应商", 1, 0, 2.47, 0, "视频模型", "openai"),
    ("ch0907-sd-2.5-1080p", "未知供应商", 1, 0, 7.51, 0, "视频模型", "openai"),
    ("sd-2-standard-720p", "未知供应商", 1, 0, 2.86, 0, "视频模型(高质)", "openai"),
    ("sd-2.5-720p", "未知供应商", 1, 0, 4.02, 0, "视频模型(高质)", "openai"),
    ("tvideos-mini-720p", "未知供应商", 1, 0, 1.02, 0, "视频模型(高质)", "openai"),
    ("tvideos-standard-720p", "未知供应商", 1, 0, 2.5, 0, "视频模型(高质)", "openai"),
]


def seed_if_empty(db: Session) -> None:
    if db.query(User).first():
        return
    now = utcnow()
    admin = User(
        username="admin",
        password_hash=hash_password("admin123"),
        display_name="Admin",
        email="admin@local",
        role=10,
        group="default",
        quota=int(settings.quota_per_unit * 1000),
        used_quota=0,
        request_count=0,
        aff_code=secrets.token_hex(3),
    )
    user = User(
        username="FengYu",
        password_hash=hash_password("Feng1010"),
        display_name="FengYu",
        email="fengyu@local",
        role=1,
        group="default",
        quota=346752803,
        used_quota=3247197,
        request_count=219,
        aff_code="yfra",
    )
    db.add_all([admin, user])
    db.flush()

    for name, desc, ratio in GROUPS:
        db.add(ChannelGroup(name=name, desc=desc, ratio=ratio))
    for item in MODELS:
        db.add(
            ModelPrice(
                model_name=item[0],
                vendor=item[1],
                quota_type=item[2],
                model_ratio=item[3],
                model_price=item[4],
                completion_ratio=item[5],
                enable_groups=item[6],
                endpoints=item[7],
            )
        )

    tokens = [
        Token(user_id=user.id, name="FenYuKey", key="sk-" + secrets.token_urlsafe(24), group="Codex（推荐）", remain_quota=-3247197),
        Token(user_id=user.id, name="FenYuKey-kyB6IK", key="sk-" + secrets.token_urlsafe(24), group="Deepseek-官方"),
        Token(user_id=user.id, name="FenYuKey-qNS7iR", key="sk-" + secrets.token_urlsafe(24), group=""),
        Token(user_id=user.id, name="Image2-1k", key="sk-" + secrets.token_urlsafe(24), group="gpt-image-2-1k"),
        Token(user_id=user.id, name="Image2-专用", key="sk-" + secrets.token_urlsafe(24), group="OpenAI-image2生图专用"),
        Token(user_id=admin.id, name="admin-key", key="sk-" + secrets.token_urlsafe(24), group="default"),
    ]
    db.add_all(tokens)
    db.flush()

    db.add(
        Redemption(key="WELCOME100", quota=int(settings.quota_per_unit * 100), status=1)
    )
    db.add(
        Log(
            user_id=user.id,
            type=7,
            content="Logged in successfully via password",
            username=user.username,
            ip="127.0.0.1",
            request_id="seed-login",
            other=json.dumps({"login_method": "password"}),
        )
    )
    for i, tokens_used in enumerate([66530, 25941, 12080, 8300, 4100]):
        db.add(
            Log(
                user_id=user.id,
                created_at=now - (i + 1) * 3600,
                type=2,
                username=user.username,
                token_name="FenYuKey",
                model_name="gpt-5.6-sol",
                quota=8000 + i * 300,
                prompt_tokens=tokens_used,
                completion_tokens=80 + i * 20,
                use_time=20 + i * 8,
                is_stream=True,
                token_id=tokens[0].id,
                group="Codex（推荐）",
                request_id=f"seed-req-{i}",
                other=json.dumps({"group_ratio": 0.4, "request_path": "/v1/chat/completions"}),
            )
        )
    db.commit()


def ensure_catalog(db: Session) -> None:
    have_g = {g.name for g in db.query(ChannelGroup).all()}
    for name, desc, ratio in GROUPS:
        if name not in have_g:
            db.add(ChannelGroup(name=name, desc=desc, ratio=ratio))
    have_m = {m.model_name for m in db.query(ModelPrice).all()}
    for item in MODELS:
        if item[0] not in have_m:
            db.add(
                ModelPrice(
                    model_name=item[0],
                    vendor=item[1],
                    quota_type=item[2],
                    model_ratio=item[3],
                    model_price=item[4],
                    completion_ratio=item[5],
                    enable_groups=item[6],
                    endpoints=item[7],
                )
            )
    db.commit()


def ensure_demo_assets(db: Session) -> None:
    ensure_catalog(db)
    user = db.query(User).filter(User.username == "FengYu").first()
    if user:
        exists = (
            db.query(Token)
            .filter(Token.user_id == user.id, Token.group.in_(["gpt-image-2-1k", "OpenAI-image2生图专用"]))
            .first()
        )
        if not exists:
            db.add(Token(user_id=user.id, name="Image2-1k", key="sk-" + secrets.token_urlsafe(24), group="gpt-image-2-1k"))
            db.add(Token(user_id=user.id, name="Image2-专用", key="sk-" + secrets.token_urlsafe(24), group="OpenAI-image2生图专用"))
    if not db.query(Redemption).filter(Redemption.key == "WELCOME100").first():
        db.add(Redemption(key="WELCOME100", name="welcome", quota=int(settings.quota_per_unit * 100), status=1))
    db.commit()
