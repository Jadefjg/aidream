import secrets

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import Token, User
from ..services.billing import mask_key

router = APIRouter()


class TokenBody(BaseModel):
    name: str
    remain_quota: int = 0
    unlimited_quota: bool = True
    expired_time: int = -1
    models: str = ""
    subnet: str = ""
    group: str = ""


def token_item(t: Token, reveal: bool = False) -> dict:
    return {
        "id": t.id,
        "name": t.name,
        "key": t.key if reveal else mask_key(t.key),
        "raw_key": t.key if reveal else None,
        "status": t.status,
        "remain_quota": t.remain_quota,
        "unlimited_quota": t.unlimited_quota,
        "group": t.group,
        "models": t.models,
        "subnet": t.subnet,
        "expired_time": t.expired_time,
        "created_time": t.created_time,
        "accessed_time": t.accessed_time,
        "used_quota": t.used_quota or 0,
    }


@router.get("/api/token/")
def list_tokens(
    p: int = Query(0),
    size: int = Query(10),
    keyword: str = "",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    p = max(0, p)
    size = max(1, min(size, 100))
    q = db.query(Token).filter(Token.user_id == user.id)
    if keyword:
        q = q.filter(or_(Token.name.contains(keyword), Token.key.contains(keyword)))
    total = q.count()
    items = q.order_by(Token.id.desc()).offset(max(p, 0) * size).limit(size).all()
    return {"success": True, "message": "", "data": [token_item(t) for t in items], "total": total}


@router.post("/api/token/")
def create_token(body: TokenBody, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="令牌名称不能为空")
    if body.remain_quota < 0:
        raise HTTPException(status_code=400, detail="令牌额度不能为负数")
    if body.expired_time < -1:
        raise HTTPException(status_code=400, detail="令牌过期时间无效")
    t = Token(
        user_id=user.id,
        name=name,
        key="sk-" + secrets.token_urlsafe(24),
        remain_quota=body.remain_quota,
        unlimited_quota=body.unlimited_quota,
        expired_time=body.expired_time,
        models=body.models,
        subnet=body.subnet,
        group=body.group,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return {"success": True, "message": "", "data": token_item(t, reveal=True)}


@router.put("/api/token/")
def update_token(body: dict, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    t = db.query(Token).filter(Token.id == body.get("id"), Token.user_id == user.id).first()
    if not t:
        raise HTTPException(status_code=404, detail="令牌不存在")
    if "name" in body and not str(body["name"]).strip():
        raise HTTPException(status_code=400, detail="令牌名称不能为空")
    if "remain_quota" in body and int(body["remain_quota"]) < 0:
        raise HTTPException(status_code=400, detail="令牌额度不能为负数")
    for field in ("name", "remain_quota", "unlimited_quota", "expired_time", "models", "subnet", "group", "status"):
        if field in body:
            setattr(t, field, body[field])
    db.commit()
    return {"success": True, "message": "已更新", "data": token_item(t)}


@router.get("/api/token/{token_id}/key")
def reveal_key(token_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    t = db.query(Token).filter(Token.id == token_id, Token.user_id == user.id).first()
    if not t:
        raise HTTPException(status_code=404, detail="令牌不存在")
    return {"success": True, "data": {"key": t.key}}


@router.delete("/api/token/{token_id}")
def delete_token(token_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    t = db.query(Token).filter(Token.id == token_id, Token.user_id == user.id).first()
    if not t:
        raise HTTPException(status_code=404, detail="令牌不存在")
    db.delete(t)
    db.commit()
    return {"success": True, "message": "已删除"}
