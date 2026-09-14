import json
import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import Log, Redemption, User, utcnow
from ..services.access import LOG_TOPUP
from ..services.billing import quota_to_usd

router = APIRouter()


class RedeemBody(BaseModel):
    key: str


class AffTransferBody(BaseModel):
    quota: int | None = None


@router.post("/api/user/topup")
def redeem(body: RedeemBody, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    key = body.key.strip()
    if not key:
        raise HTTPException(status_code=400, detail="兑换码不能为空")
    code = db.query(Redemption).filter(Redemption.key == key).first()
    if not code or code.status != 1:
        raise HTTPException(status_code=400, detail="兑换码无效或已使用")
    if code.expired_time and code.expired_time > 0 and code.expired_time < utcnow():
        raise HTTPException(status_code=400, detail="兑换码已过期")
    claimed = (
        db.query(Redemption)
        .filter(Redemption.id == code.id, Redemption.status == 1)
        .update({Redemption.status: 3, Redemption.redeemed_by: user.id}, synchronize_session=False)
    )
    if claimed != 1:
        db.rollback()
        raise HTTPException(status_code=400, detail="兑换码无效或已使用")
    db.refresh(code)
    user.quota += code.quota
    db.add(
        Log(
            user_id=user.id,
            type=LOG_TOPUP,
            content=f"兑换码充值 {code.key}",
            username=user.username,
            quota=code.quota,
            request_id=secrets.token_hex(8),
            other=json.dumps({"redemption_id": code.id}),
        )
    )
    db.commit()
    return {
        "success": True,
        "message": f"兑换成功，到账 ${quota_to_usd(code.quota)}",
        "data": {"quota": user.quota, "added": code.quota, "balance_usd": quota_to_usd(user.quota)},
    }


@router.get("/api/user/aff")
def aff_info(user: User = Depends(get_current_user)):
    return {
        "success": True,
        "message": "",
        "data": {
            "aff_code": user.aff_code,
            "aff_count": user.aff_count,
            "aff_quota": user.aff_quota,
            "aff_history_quota": user.aff_history_quota,
        },
    }


@router.post("/api/user/aff_transfer")
def aff_transfer(body: AffTransferBody, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    amount = body.quota if body.quota is not None else user.aff_quota
    if amount <= 0:
        raise HTTPException(status_code=400, detail="没有可划转的邀请收益")
    if amount > user.aff_quota:
        raise HTTPException(status_code=400, detail="划转额度超过待使用收益")
    user.aff_quota -= amount
    user.quota += amount
    db.add(
        Log(
            user_id=user.id,
            type=LOG_TOPUP,
            content="邀请收益划转到余额",
            username=user.username,
            quota=amount,
        )
    )
    db.commit()
    return {
        "success": True,
        "message": f"已划转 ${quota_to_usd(amount)} 到余额",
        "data": {"quota": user.quota, "aff_quota": user.aff_quota, "balance_usd": quota_to_usd(user.quota)},
    }
