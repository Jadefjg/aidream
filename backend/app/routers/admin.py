import secrets
import os
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import Redemption, User, UpstreamChannel, Log, utcnow
from ..config import settings
from ..services.billing import quota_to_usd, usd_to_quota

router = APIRouter()


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role < 10:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


class RedemptionCreate(BaseModel):
    name: str = "batch"
    count: int = 1
    quota: int | None = None
    amount_usd: float | None = None
    expired_time: int = 0


class UserPatch(BaseModel):
    id: int
    quota: int | None = None
    status: int | None = None
    group: str | None = None


class ChannelBody(BaseModel):
    name: str
    base_url: str
    api_key: str = ""
    provider: str = "openai"
    groups: str = "default"
    models: str = ""
    priority: int = 0
    status: int = 1
    weight: int = 1


def channel_payload(c: UpstreamChannel) -> dict:
    return {"id": c.id, "name": c.name, "base_url": c.base_url, "api_key": (c.api_key[:6] + "..." if c.api_key else ""), "provider": c.provider, "groups": c.groups, "models": c.models, "priority": c.priority, "status": c.status, "weight": c.weight, "failure_count": c.failure_count, "last_failure": c.last_failure}


@router.get("/api/channel/")
def list_channels(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return {"success": True, "data": [channel_payload(c) for c in db.query(UpstreamChannel).order_by(UpstreamChannel.priority.desc(), UpstreamChannel.id).all()]}


@router.post("/api/channel/")
def create_channel(body: ChannelBody, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    if db.query(UpstreamChannel).filter(UpstreamChannel.name == body.name).first():
        raise HTTPException(status_code=400, detail="渠道名称已存在")
    channel = UpstreamChannel(**body.model_dump())
    db.add(channel); db.add(Log(user_id=admin.id, type=3, content=f"创建上游渠道：{body.name}", username=admin.username, request_id=secrets.token_hex(8))); db.commit(); db.refresh(channel)
    return {"success": True, "data": channel_payload(channel)}


@router.put("/api/channel/{cid}")
def update_channel(cid: int, body: ChannelBody, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    channel = db.get(UpstreamChannel, cid)
    if not channel: raise HTTPException(status_code=404, detail="渠道不存在")
    for key, value in body.model_dump().items(): setattr(channel, key, value)
    db.add(Log(user_id=admin.id, type=3, content=f"更新上游渠道：{channel.name}", username=admin.username, request_id=secrets.token_hex(8))); db.commit(); db.refresh(channel)
    return {"success": True, "data": channel_payload(channel)}


@router.delete("/api/channel/{cid}")
def delete_channel(cid: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    channel = db.get(UpstreamChannel, cid)
    if not channel: raise HTTPException(status_code=404, detail="渠道不存在")
    db.delete(channel); db.add(Log(user_id=admin.id, type=3, content=f"删除上游渠道：{channel.name}", username=admin.username, request_id=secrets.token_hex(8))); db.commit()
    return {"success": True, "message": "已删除"}


@router.post("/api/admin/backup")
def backup_database(admin: User = Depends(require_admin)):
    source = Path(settings.database_url.replace("sqlite:///", ""))
    if not source.exists():
        raise HTTPException(status_code=404, detail="当前数据库不是可备份的 SQLite 文件")
    target_dir = Path(settings.database_backup_dir); target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"aidream-{utcnow()}.db"
    shutil.copy2(source, target)
    return {"success": True, "data": {"path": str(target), "size": target.stat().st_size}}


@router.get("/api/redemption/")
def list_redemptions(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    rows = db.query(Redemption).order_by(Redemption.id.desc()).limit(200).all()
    return {
        "success": True,
        "data": [
            {
                "id": r.id,
                "name": r.name,
                "key": r.key,
                "quota": r.quota,
                "quota_usd": quota_to_usd(r.quota),
                "status": r.status,
                "redeemed_by": r.redeemed_by,
                "expired_time": r.expired_time,
                "created_at": r.created_at,
            }
            for r in rows
        ],
    }


@router.post("/api/redemption/")
def create_redemptions(body: RedemptionCreate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    count = max(1, min(body.count, 100))
    quota = body.quota if body.quota is not None else usd_to_quota(body.amount_usd or 1)
    keys = []
    for _ in range(count):
        key = secrets.token_urlsafe(10).replace("-", "").upper()[:16]
        db.add(Redemption(key=key, name=body.name, quota=quota, expired_time=body.expired_time))
        keys.append(key)
    db.commit()
    return {"success": True, "message": f"已生成 {count} 个兑换码", "data": keys}


@router.get("/api/user/")
def list_users(
    p: int = Query(0),
    size: int = Query(20),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    p = max(0, p)
    size = max(1, min(size, 100))
    q = db.query(User).order_by(User.id.desc())
    total = q.count()
    rows = q.offset(max(p, 0) * size).limit(size).all()
    return {
        "success": True,
        "total": total,
        "data": [
            {
                "id": u.id,
                "username": u.username,
                "display_name": u.display_name,
                "email": u.email,
                "role": u.role,
                "status": u.status,
                "group": u.group,
                "quota": u.quota,
                "used_quota": u.used_quota,
                "request_count": u.request_count,
                "balance_usd": quota_to_usd(u.quota),
            }
            for u in rows
        ],
    }


@router.put("/api/user/")
def patch_user(body: UserPatch, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    user = db.get(User, body.id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if body.quota is not None:
        user.quota = body.quota
    if body.status is not None:
        user.status = body.status
    if body.group is not None:
        user.group = body.group
    db.commit()
    return {"success": True, "message": "已更新"}


@router.delete("/api/redemption/{rid}")
def delete_redemption(rid: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    row = db.get(Redemption, rid)
    if not row:
        raise HTTPException(status_code=404, detail="兑换码不存在")
    db.delete(row)
    db.commit()
    return {"success": True, "message": "已删除"}


@router.put("/api/redemption/")
def patch_redemption(body: dict, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    row = db.get(Redemption, body.get("id"))
    if not row:
        raise HTTPException(status_code=404, detail="兑换码不存在")
    if "status" in body:
        row.status = body["status"]
    if "name" in body:
        row.name = body["name"]
    db.commit()
    return {"success": True, "message": "已更新"}
