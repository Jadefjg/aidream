from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .database import Base, SessionLocal, engine
from .migrate import migrate_schema
from .routers import api_router
from .seed import ensure_demo_assets, seed_if_empty
from .config import settings

app = FastAPI(title="THINK-AI", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[x.strip() for x in settings.cors_origins.split(",") if x.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)


@app.exception_handler(HTTPException)
async def http_exc(request: Request, exc: HTTPException):
    if request.url.path.startswith("/v1") or request.url.path.startswith("/v1beta"):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"message": exc.detail, "type": "invalid_request_error", "code": exc.status_code}},
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "message": exc.detail, "data": None},
    )


@app.exception_handler(Exception)
async def all_exc(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"success": False, "message": str(exc), "data": None})


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    migrate_schema(engine)
    db = SessionLocal()
    try:
        seed_if_empty(db)
        ensure_demo_assets(db)
    finally:
        db.close()


@app.get("/health")
def health():
    return {"ok": True}
