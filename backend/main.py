from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.routers import api_router
from backend.config import settings
from db import init_db


app = FastAPI(
    title=settings.app_name,
    debug=settings.app_debug,
    version="0.1.0",
    description="开源校园智能健身调度引擎后端基础服务。",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/", tags=["root"], summary="Root endpoint")
def read_root() -> dict[str, str]:
    return {
        "message": f"{settings.app_name} is running",
        "docs": "/docs",
    }
