import json
import secrets
import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import create_access_token, get_current_user, hash_password, verify_password
from ..config import settings
from ..database import get_db
from ..models import ChannelGroup, Log, User
from ..services.access import LOG_LOGIN, LOG_SYSTEM, group_models
from ..services.billing import quota_to_usd

router = APIRouter()
_login_attempts: dict[str, deque[float]] = defaultdict(deque)


class LoginBody(BaseModel):
    username: str
    password: str


class RegisterBody(BaseModel):
    username: str
    password: str
    email: str = ""
    aff_code: str = ""


def user_payload(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name or user.username,
        "email": user.email,
        "role": user.role,
        "status": user.status,
        "group": user.group,
        "quota": user.quota,
        "used_quota": user.used_quota,
        "request_count": user.request_count,
        "aff_code": user.aff_code,
        "aff_count": user.aff_count,
        "aff_quota": user.aff_quota,
        "aff_history_quota": user.aff_history_quota,
        "inviter_id": user.inviter_id,
        "balance_usd": quota_to_usd(user.quota),
        "used_usd": quota_to_usd(user.used_quota),
    }


@router.post("/api/user/login")
def login(body: LoginBody, request: Request, db: Session = Depends(get_db)):
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    attempts = _login_attempts[ip]
    while attempts and now - attempts[0] > 300:
        attempts.popleft()
    if len(attempts) >= 10:
        raise HTTPException(status_code=429, detail="登录尝试过于频繁，请稍后再试")
    user = (
        db.query(User)
        .filter((User.username == body.username) | (User.email == body.username))
        .first()
    )
    if not user or not verify_password(body.password, user.password_hash):
        attempts.append(now)
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    attempts.clear()
    if user.status != 1:
        raise HTTPException(status_code=403, detail="该账号已被禁用")
    token = create_access_token(user)
    db.add(
        Log(
            user_id=user.id,
            type=LOG_LOGIN,
            content="Logged in successfully via password",
            username=user.username,
            ip=request.client.host if request.client else "",
            request_id=secrets.token_hex(8),
            other=json.dumps({"login_method": "password"}),
        )
    )
    db.commit()
    data = user_payload(user)
    return {
        "success": True,
        "message": "",
        "data": {
            **data,
            "access_token": token,
            "token_type": "Bearer",
            "user": data,
        },
    }


@router.post("/api/user/register")
def register(body: RegisterBody, db: Session = Depends(get_db)):
    username = body.username.strip()
    if len(username) < 3 or len(username) > 20:
        raise HTTPException(status_code=400, detail="用户名长度需为 3-20 位")
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="密码至少 6 位")
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    if body.email and db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=400, detail="邮箱已被注册")
    inviter_id = 0
    inviter = None
    if body.aff_code:
        inviter = db.query(User).filter(User.aff_code == body.aff_code.strip()).first()
        if inviter:
            inviter_id = inviter.id
            inviter.aff_count += 1
            inviter.aff_quota += settings.aff_quota_per_invite
            inviter.aff_history_quota += settings.aff_quota_per_invite
    user = User(
        username=username,
        password_hash=hash_password(body.password),
        display_name=username,
        email=body.email,
        quota=settings.register_gift_quota,
        aff_code=secrets.token_hex(3),
        inviter_id=inviter_id,
    )
    db.add(user)
    db.flush()
    db.add(
        Log(
            user_id=user.id,
            type=LOG_SYSTEM,
            content=f"新用户注册 {username}",
            username=username,
            quota=settings.register_gift_quota,
        )
    )
    db.commit()
    db.refresh(user)
    token = create_access_token(user)
    data = user_payload(user)
    return {"success": True, "message": "", "data": {**data, "access_token": token, "user": data}}


@router.get("/api/user/self")
def self_info(user: User = Depends(get_current_user)):
    return {"success": True, "message": "", "data": user_payload(user)}


class UpdateSelfBody(BaseModel):
    display_name: str | None = None
    email: str | None = None
    password: str | None = None
    original_password: str | None = None


@router.put("/api/user/self")
def update_self(body: UpdateSelfBody, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if body.password:
        if not body.original_password or not verify_password(body.original_password, user.password_hash):
            raise HTTPException(status_code=400, detail="原密码错误")
        user.password_hash = hash_password(body.password)
    if body.display_name is not None:
        user.display_name = body.display_name
    if body.email is not None:
        user.email = body.email
    db.commit()
    return {"success": True, "message": "保存成功", "data": user_payload(user)}


@router.get("/api/user/self/groups")
def self_groups(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    groups = db.query(ChannelGroup).all()
    data = {g.name: {"desc": g.desc, "ratio": g.ratio} for g in groups}
    return {"success": True, "message": "", "data": data}


@router.get("/api/user/models")
def user_models(group: str = "", db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    names = [m.model_name for m in group_models(db, group or user.group or "default")]
    return {"success": True, "message": "", "data": names}
