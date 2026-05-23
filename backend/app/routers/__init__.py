from fastapi import APIRouter

from .chat import router as chat_router
from .health import router as health_router
from .meta import router as meta_router
from .plan_routes import router as plan_router
from .user_routes import router as user_router
from .weather_routes import router as weather_router


api_router = APIRouter()
api_router.include_router(chat_router, prefix="/chat", tags=["chat"])
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(meta_router, prefix="/meta", tags=["meta"])
api_router.include_router(plan_router, prefix="/plan", tags=["plan"])
api_router.include_router(user_router, prefix="/user", tags=["user"])
api_router.include_router(weather_router, prefix="/weather", tags=["weather"])


__all__ = ["api_router"]
