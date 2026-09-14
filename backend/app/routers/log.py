from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import Log, User
from ..config import settings
from ..services.billing import quota_to_usd

router = APIRouter()

TYPE_NAME = {1: "充值", 2: "消费", 3: "管理", 4: "系统", 5: "错误", 7: "登录"}


@router.get("/api/log/self")
def self_logs(
    p: int = Query(1),
    page_size: int = Query(10),
    token_name: str = "",
    model_name: str = "",
    group: str = "",
    type: int | None = None,
    start_timestamp: int = 0,
    end_timestamp: int = 0,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(Log).filter(Log.user_id == user.id)
    if token_name:
        q = q.filter(Log.token_name.contains(token_name))
    if model_name:
        q = q.filter(Log.model_name.contains(model_name))
    if group:
        q = q.filter(Log.group.contains(group))
    if type is not None:
        q = q.filter(Log.type == type)
    if start_timestamp:
        q = q.filter(Log.created_at >= start_timestamp)
    if end_timestamp:
        q = q.filter(Log.created_at <= end_timestamp)
    total = q.count()
    items = q.order_by(Log.id.desc()).offset(max(p - 1, 0) * page_size).limit(page_size).all()
    data = []
    for log in items:
        data.append(
            {
                "id": log.id,
                "user_id": log.user_id,
                "created_at": log.created_at,
                "type": log.type,
                "type_name": TYPE_NAME.get(log.type, "其他"),
                "content": log.content,
                "username": log.username,
                "token_name": log.token_name,
                "model_name": log.model_name,
                "quota": log.quota,
                "quota_usd": round(log.quota / settings.quota_per_unit, 6),
                "prompt_tokens": log.prompt_tokens,
                "completion_tokens": log.completion_tokens,
                "use_time": log.use_time,
                "is_stream": log.is_stream,
                "token_id": log.token_id,
                "group": log.group,
                "ip": log.ip,
                "request_id": log.request_id,
                "other": log.other,
            }
        )
    return {"success": True, "message": "", "data": {"page": p, "page_size": page_size, "total": total, "items": data}}


@router.get("/api/log/")
def logs_alias(
    p: int = Query(1),
    page_size: int = Query(10),
    token_name: str = "",
    model_name: str = "",
    group: str = "",
    type: int | None = None,
    start_timestamp: int = 0,
    end_timestamp: int = 0,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return self_logs(p, page_size, token_name, model_name, group, type, start_timestamp, end_timestamp, db, user)
