from typing import Union

from fastapi import APIRouter

from backend.config import settings


router = APIRouter()


@router.get("", summary="Application metadata")
def get_meta() -> dict[str, Union[str, bool]]:
    return {
        "app_name": settings.app_name,
        "environment": settings.app_env,
        "debug": settings.app_debug,
    }
