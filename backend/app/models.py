from datetime import datetime, timezone

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> int:
    return int(datetime.now(timezone.utc).timestamp())


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    display_name: Mapped[str] = mapped_column(String(64), default="")
    email: Mapped[str] = mapped_column(String(128), default="")
    role: Mapped[int] = mapped_column(Integer, default=1)  # 1 user, 10 admin
    status: Mapped[int] = mapped_column(Integer, default=1)
    group: Mapped[str] = mapped_column(String(64), default="default")
    quota: Mapped[int] = mapped_column(Integer, default=0)
    used_quota: Mapped[int] = mapped_column(Integer, default=0)
    request_count: Mapped[int] = mapped_column(Integer, default=0)
    aff_code: Mapped[str] = mapped_column(String(16), default="")
    aff_count: Mapped[int] = mapped_column(Integer, default=0)
    aff_quota: Mapped[int] = mapped_column(Integer, default=0)
    aff_history_quota: Mapped[int] = mapped_column(Integer, default=0)
    inviter_id: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[int] = mapped_column(Integer, default=utcnow)

    tokens = relationship("Token", back_populates="user")


class Token(Base):
    __tablename__ = "tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(64))
    key: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    status: Mapped[int] = mapped_column(Integer, default=1)
    remain_quota: Mapped[int] = mapped_column(Integer, default=0)
    unlimited_quota: Mapped[bool] = mapped_column(Boolean, default=True)
    group: Mapped[str] = mapped_column(String(64), default="")
    models: Mapped[str] = mapped_column(Text, default="")
    subnet: Mapped[str] = mapped_column(String(256), default="")
    expired_time: Mapped[int] = mapped_column(Integer, default=-1)
    created_time: Mapped[int] = mapped_column(Integer, default=utcnow)
    accessed_time: Mapped[int] = mapped_column(Integer, default=0)
    used_quota: Mapped[int] = mapped_column(Integer, default=0)

    user = relationship("User", back_populates="tokens")


class Log(Base):
    __tablename__ = "logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, default=0)
    created_at: Mapped[int] = mapped_column(Integer, default=utcnow, index=True)
    type: Mapped[int] = mapped_column(Integer, default=2)  # 2 consume, 7 system
    content: Mapped[str] = mapped_column(Text, default="")
    username: Mapped[str] = mapped_column(String(64), default="")
    token_name: Mapped[str] = mapped_column(String(64), default="")
    model_name: Mapped[str] = mapped_column(String(128), default="")
    quota: Mapped[int] = mapped_column(Integer, default=0)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    use_time: Mapped[int] = mapped_column(Integer, default=0)
    is_stream: Mapped[bool] = mapped_column(Boolean, default=False)
    token_id: Mapped[int] = mapped_column(Integer, default=0)
    group: Mapped[str] = mapped_column(String(64), default="")
    ip: Mapped[str] = mapped_column(String(64), default="")
    request_id: Mapped[str] = mapped_column(String(80), default="")
    other: Mapped[str] = mapped_column(Text, default="{}")


class ModelPrice(Base):
    __tablename__ = "model_prices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    vendor: Mapped[str] = mapped_column(String(64), default="")
    quota_type: Mapped[int] = mapped_column(Integer, default=0)  # 0 token, 1 per-call
    model_ratio: Mapped[float] = mapped_column(Float, default=1.0)
    model_price: Mapped[float] = mapped_column(Float, default=0.0)
    completion_ratio: Mapped[float] = mapped_column(Float, default=1.0)
    cache_ratio: Mapped[float] = mapped_column(Float, default=0.1)
    enable_groups: Mapped[str] = mapped_column(Text, default="default")
    endpoints: Mapped[str] = mapped_column(String(128), default="openai")


class ChannelGroup(Base):
    __tablename__ = "channel_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    desc: Mapped[str] = mapped_column(String(256), default="")
    ratio: Mapped[float] = mapped_column(Float, default=1.0)


class UpstreamChannel(Base):
    """Configurable upstream route, similar to a New API channel."""
    __tablename__ = "upstream_channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    base_url: Mapped[str] = mapped_column(String(512))
    api_key: Mapped[str] = mapped_column(String(512), default="")
    provider: Mapped[str] = mapped_column(String(32), default="openai")
    groups: Mapped[str] = mapped_column(Text, default="default")
    models: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[int] = mapped_column(Integer, default=1)
    weight: Mapped[int] = mapped_column(Integer, default=1)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    last_failure: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[int] = mapped_column(Integer, default=utcnow)


class Redemption(Base):
    __tablename__ = "redemptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(64), default="")
    quota: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[int] = mapped_column(Integer, default=1)  # 1 unused, 3 used
    redeemed_by: Mapped[int] = mapped_column(Integer, default=0)
    expired_time: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[int] = mapped_column(Integer, default=utcnow)


class ImageTask(Base):
    __tablename__ = "image_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    prompt: Mapped[str] = mapped_column(Text, default="")
    size: Mapped[str] = mapped_column(String(32), default="1024x1024")
    quality: Mapped[str] = mapped_column(String(16), default="1k")
    n: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(16), default="success")
    image_b64: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[int] = mapped_column(Integer, default=utcnow)
