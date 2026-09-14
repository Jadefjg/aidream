from fastapi import APIRouter

from ..config import settings
from ..models import utcnow

router = APIRouter()

ANNOUNCEMENT = """欢迎大家使用ThinkAi Token聚合平台，统一接口、多渠道调度、模型持续更新
GPT官方价格1/17，Claude官方价格1/3
Image2生图模型1、2、4k分别为，6分、8分、1毛
进群领新人测试额度/使用Claude满血渠道/开票：418671514"""


@router.get("/api/status")
def status():
    return {
        "success": True,
        "message": "",
        "data": {
            "system_name": settings.app_name,
            "logo": "",
            "start_time": utcnow() - 86400 * 3,
            "quota_per_unit": settings.quota_per_unit,
            "display_in_currency": True,
            "quota_display_type": "USD",
            "docs_link": settings.docs_link,
            "server_address": settings.server_address,
            "enable_drawing": True,
            "enable_task": True,
            "enable_data_export": True,
            "password_login_enabled": True,
            "password_register_enabled": True,
            "register_enabled": True,
            "HeaderNavModules": '{"home":true,"console":true,"pricing":{"enabled":true,"requireAuth":false},"docs":true,"about":false}',
            "announcements": ANNOUNCEMENT,
            "announcements_enabled": True,
            "chats": [
                {"Cherry Studio": "cherrystudio://providers/api-keys?v=1&data={cherryConfig}"},
                {"Lobe Chat 官方示例": "https://chat-preview.lobehub.com/"},
            ],
            "version": "aidream-1.0",
        },
    }
