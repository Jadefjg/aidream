from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ChannelGroup, ModelPrice
from ..config import settings

router = APIRouter()


@router.get("/api/pricing")
def pricing(db: Session = Depends(get_db)):
    groups = {g.name: g.ratio for g in db.query(ChannelGroup).all()}
    items = []
    for m in db.query(ModelPrice).order_by(ModelPrice.vendor, ModelPrice.model_name).all():
        enable_groups = [g for g in m.enable_groups.split(",") if g]
        ratio = min((groups.get(g, 1.0) for g in enable_groups), default=1.0)
        if m.quota_type == 0:
            input_price = round(2.0 * m.model_ratio * ratio, 4)
            completion_price = round(2.0 * m.model_ratio * m.completion_ratio * ratio, 4)
            official_in = round(2.0 * m.model_ratio, 4)
            official_out = round(2.0 * m.model_ratio * m.completion_ratio, 4)
            save = round((1 - ratio) * 100, 1) if ratio < 1 else 0
        else:
            input_price = round(m.model_price * ratio, 4)
            completion_price = 0
            official_in = m.model_price
            official_out = 0
            save = round((1 - ratio) * 100, 1) if ratio < 1 else 0
        items.append(
            {
                "model_name": m.model_name,
                "vendor_name": m.vendor,
                "quota_type": m.quota_type,
                "model_ratio": m.model_ratio,
                "model_price": m.model_price,
                "completion_ratio": m.completion_ratio,
                "enable_groups": enable_groups,
                "supported_endpoint_types": m.endpoints.split(","),
                "input_price": input_price,
                "completion_price": completion_price,
                "official_input": official_in,
                "official_completion": official_out,
                "save_percent": save,
                "group_ratio": ratio,
                "quota_per_unit": settings.quota_per_unit,
            }
        )
    return {"success": True, "message": "", "data": items}


@router.get("/api/group/")
def groups(db: Session = Depends(get_db)):
    data = {g.name: {"desc": g.desc, "ratio": g.ratio} for g in db.query(ChannelGroup).all()}
    return {"success": True, "message": "", "data": data}
