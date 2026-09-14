import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import Token, User, utcnow

bearer = HTTPBearer(auto_error=False)


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120000).hex()
    return f"{salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, digest = stored.split("$", 1)
    except ValueError:
        return False
    check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120000).hex()
    return hmac.compare_digest(check, digest)


def create_access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "token_use": "access",
        "sub": str(user.id),
        "username": user.username,
        "role": user.role,
        "iss": "new-api",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.access_token_expire_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="无权进行此操作，access token 无效")


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    raw = None
    if creds:
        raw = creds.credentials
    elif authorization:
        raw = authorization.replace("Bearer ", "").strip()
    if not raw:
        raise HTTPException(status_code=401, detail="未登录或登录已过期")
    payload = decode_token(raw)
    user = db.get(User, int(payload["sub"]))
    if not user or user.status != 1:
        raise HTTPException(status_code=401, detail="用户不存在或已被禁用")
    return user


def resolve_api_token(authorization: str | None, db: Session, api_key: str | None = None) -> tuple[Token, User]:
    authorization = authorization or api_key
    if not authorization:
        raise HTTPException(status_code=401, detail="You didn't provide an API key.")
    key = authorization.strip()
    if key.lower().startswith("bearer "):
        key = key[7:].strip()
    token = db.query(Token).filter(Token.key == key).first()
    if not token or token.status != 1:
        raise HTTPException(status_code=401, detail="Incorrect API key provided")
    if token.expired_time not in (-1, 0) and token.expired_time < utcnow():
        raise HTTPException(status_code=403, detail="This token has expired")
    user = db.get(User, token.user_id)
    if not user or user.status != 1:
        raise HTTPException(status_code=403, detail="User is disabled")
    return token, user


def get_api_token(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> tuple[Token, User]:
    return resolve_api_token(authorization, db)
