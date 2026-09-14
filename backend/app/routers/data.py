from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import Log, User
from ..services.billing import quota_to_usd

router = APIRouter()


@router.get("/api/data/")
def dashboard_data(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    logs = db.query(Log).filter(Log.user_id == user.id, Log.type == 2).all()
    by_hour = defaultdict(lambda: {"quota": 0, "count": 0, "tokens": 0})
    by_model = defaultdict(lambda: {"quota": 0, "count": 0})
    total_tokens = 0
    for log in logs:
        hour = (log.created_at // 3600) * 3600
        by_hour[hour]["quota"] += log.quota
        by_hour[hour]["count"] += 1
        by_hour[hour]["tokens"] += log.prompt_tokens + log.completion_tokens
        by_model[log.model_name or "unknown"]["quota"] += log.quota
        by_model[log.model_name or "unknown"]["count"] += 1
        total_tokens += log.prompt_tokens + log.completion_tokens
    hours = sorted(by_hour.keys()) or [0]
    timespan = max(hours[-1] - hours[0], 3600)
    rpm = round(len(logs) / (timespan / 60), 3) if logs else 0
    tpm = round(total_tokens / (timespan / 60), 3) if logs else 0
    return {
        "success": True,
        "message": "",
        "data": {
            "quota": user.quota,
            "used_quota": user.used_quota,
            "request_count": user.request_count,
            "stat_count": len(logs),
            "stat_quota": sum(l.quota for l in logs),
            "stat_tokens": total_tokens,
            "balance_usd": quota_to_usd(user.quota),
            "used_usd": quota_to_usd(user.used_quota),
            "rpm": rpm,
            "tpm": tpm,
            "trend": [{"t": t, **by_hour[t]} for t in hours],
            "models": [{"name": k, **v} for k, v in by_model.items()],
        },
    }
