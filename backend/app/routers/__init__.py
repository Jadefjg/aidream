from fastapi import APIRouter

from . import admin, data, log, pricing, relay, status, token, topup, user

api_router = APIRouter()
api_router.include_router(status.router)
api_router.include_router(user.router)
api_router.include_router(token.router)
api_router.include_router(log.router)
api_router.include_router(pricing.router)
api_router.include_router(topup.router)
api_router.include_router(data.router)
api_router.include_router(relay.router)
api_router.include_router(admin.router)
