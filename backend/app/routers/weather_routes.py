from fastapi import APIRouter

from backend.app.domains.weather_domain import evaluate_weather_venues, fetch_weather_snapshot
from backend.app.models.schemas import VenueWeatherStatusResponse


router = APIRouter()


@router.get(
    "/venue-status",
    response_model=VenueWeatherStatusResponse,
    summary="获取粤海街道重点运动场地天气适宜度",
)
async def get_venue_weather_status() -> VenueWeatherStatusResponse:
    weather_snapshot = await fetch_weather_snapshot()
    venue_analysis = evaluate_weather_venues(weather_snapshot)

    return VenueWeatherStatusResponse(
        location=venue_analysis.weather_snapshot.location,
        weather_snapshot={
            "precipitation_mm": venue_analysis.weather_snapshot.precipitation_mm,
            "temperature_c": venue_analysis.weather_snapshot.temperature_c,
            "is_raining": venue_analysis.weather_snapshot.is_raining,
        },
        venue_statuses=[item.model_dump() for item in venue_analysis.venue_statuses],
    )
