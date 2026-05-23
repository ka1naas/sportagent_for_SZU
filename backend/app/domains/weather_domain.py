from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from backend.app.domains.schemas import VenueStatus, WeatherSnapshot, WeatherVenueAnalysisOutput
from backend.config import settings


@dataclass(frozen=True)
class VenueProfile:
    name: str
    surface_type: str
    drainage_factor: float
    rain_sensitivity: float
    dry_speed_factor: float
    base_risk_penalty: float


VENUE_PROFILES: tuple[VenueProfile, ...] = (
    VenueProfile("天台篮球场", "胶篮球场", 1.35, 1.55, 0.35, 20),
    VenueProfile("深圳大学体育场", "塑胶跑道", 0.95, 1.0, 0.7, 8),
    VenueProfile("街头健身区", "塑胶板", 0.55, 0.65, 1.35, 3),
)

YUEHAI_LOCATION = {
    "name": "深圳南山区粤海街道",
    "lon": 113.94,
    "lat": 22.53,
}
DEFAULT_TIMEOUT_SECONDS = 6.0
VENUES_DATA_PATH = Path("backend/data/venues.json")


def build_mock_weather_snapshot(*, reason: str, location: str = "深圳南山区粤海街道") -> WeatherSnapshot:
    return WeatherSnapshot(
        location=location,
        precipitation_mm=15.0,
        temperature_c=26.0,
        humidity_pct=92,
        is_raining=True,
        source="mock",
        observation_window_hours=3,
        fallback_reason=reason,
    )


async def fetch_weather_snapshot() -> WeatherSnapshot:
    api_key = settings.weather_api_key.strip()
    base_url = settings.weather_api_base_url.strip().rstrip("/")

    if not api_key or not base_url:
        return build_mock_weather_snapshot(reason="missing_api_configuration", location=YUEHAI_LOCATION["name"])

    params = {
        "location": f"{YUEHAI_LOCATION['lon']},{YUEHAI_LOCATION['lat']}",
        "key": api_key,
    }

    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS) as client:
            response = await client.get(f"{base_url}/weather/now", params=params)
            response.raise_for_status()
            payload = response.json()
        return normalize_weather_payload(payload, location=YUEHAI_LOCATION["name"])
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        return build_mock_weather_snapshot(reason="weather_api_request_failed", location=YUEHAI_LOCATION["name"])


def normalize_weather_payload(payload: dict[str, Any], *, location: str = "深圳南山区粤海街道") -> WeatherSnapshot:
    now_data = _extract_now_payload(payload)
    precipitation_mm = _safe_float(now_data.get("precip") or now_data.get("precipitation"))
    temperature_c = _safe_float(now_data.get("temp") or now_data.get("temperature"))
    humidity_pct = int(round(_safe_float(now_data.get("humidity"))))
    return WeatherSnapshot(
        location=location,
        precipitation_mm=round(max(precipitation_mm, 0.0), 1),
        temperature_c=round(temperature_c, 1),
        humidity_pct=max(0, min(100, humidity_pct)),
        is_raining=precipitation_mm > 0,
        source="live",
        observation_window_hours=1,
    )


def evaluate_weather_venues(weather_snapshot: WeatherSnapshot) -> WeatherVenueAnalysisOutput:
    venue_statuses: list[VenueStatus] = []
    dynamic_profiles = _load_venue_profiles()
    for profile in dynamic_profiles:
        wetness_level_pct = _calculate_wetness(
            profile=profile,
            precipitation_mm=weather_snapshot.precipitation_mm,
            temperature_c=weather_snapshot.temperature_c,
            humidity_pct=weather_snapshot.humidity_pct,
            is_raining=weather_snapshot.is_raining,
        )
        suitability_score = _calculate_suitability(
            profile,
            wetness_level_pct,
            weather_snapshot.precipitation_mm,
            weather_snapshot.is_raining,
        )
        venue_statuses.append(
            VenueStatus(
                venue_name=profile.name,
                surface_type=profile.surface_type,
                wetness_level_pct=wetness_level_pct,
                suitability_score=suitability_score,
                can_exercise=suitability_score >= 60,
                notice=_build_notice(
                    profile,
                    wetness_level_pct,
                    suitability_score,
                    weather_snapshot.precipitation_mm,
                    weather_snapshot.is_raining,
                ),
            )
        )
    return WeatherVenueAnalysisOutput(weather_snapshot=weather_snapshot, venue_statuses=venue_statuses)


def _load_venue_profiles() -> list[VenueProfile]:
    if not VENUES_DATA_PATH.exists():
        return list(VENUE_PROFILES)

    raw_items = json.loads(VENUES_DATA_PATH.read_text(encoding="utf-8"))
    profiles: list[VenueProfile] = []
    for item in raw_items:
        notes = item.get("notes", "")
        name = item.get("name", "未知场馆")
        indoor = bool(item.get("indoor", False))
        sport_types = item.get("sport_types", [])
        if indoor:
            surface_type = "室内综合场馆"
            drainage_factor = 0.2
            rain_sensitivity = 0.2
            dry_speed_factor = 1.8
            base_risk_penalty = 2
        elif any("跑步" in sport for sport in sport_types):
            surface_type = "室外跑道"
            drainage_factor = 0.9
            rain_sensitivity = 0.9
            dry_speed_factor = 0.8
            base_risk_penalty = 8
        else:
            surface_type = "室外综合场地"
            drainage_factor = 1.0
            rain_sensitivity = 1.1
            dry_speed_factor = 0.7
            base_risk_penalty = 10

        if "篮球" in name or any("篮球" in sport for sport in sport_types):
            surface_type = "篮球场地"
            drainage_factor = 1.2
            rain_sensitivity = 1.4
            dry_speed_factor = 0.45
            base_risk_penalty = 18

        if notes and "雨天" in notes and indoor:
            base_risk_penalty = 1

        profiles.append(
            VenueProfile(
                name=name,
                surface_type=surface_type,
                drainage_factor=drainage_factor,
                rain_sensitivity=rain_sensitivity,
                dry_speed_factor=dry_speed_factor,
                base_risk_penalty=base_risk_penalty,
            )
        )

    return profiles or list(VENUE_PROFILES)


def _extract_now_payload(weather_data: dict[str, Any]) -> dict[str, Any]:
    if "now" in weather_data and isinstance(weather_data["now"], dict):
        return weather_data["now"]
    if "result" in weather_data and isinstance(weather_data["result"], dict):
        return weather_data["result"]
    return weather_data


def _safe_float(value: Any) -> float:
    if value in (None, ""):
        raise ValueError("invalid numeric weather value")
    return float(value)


def _calculate_wetness(*, profile: VenueProfile, precipitation_mm: float, temperature_c: float, humidity_pct: float, is_raining: bool) -> int:
    rain_impact = precipitation_mm * 7.5 * profile.drainage_factor * profile.rain_sensitivity
    humidity_impact = (humidity_pct / 100.0) * 18
    if is_raining:
        drying_offset = 0.0
    else:
        temperature_bonus = max(temperature_c - 24.0, 0.0) * 2.4
        humidity_drag = max(humidity_pct - 70.0, 0.0) * 0.32
        drying_offset = max((temperature_bonus - humidity_drag) * profile.dry_speed_factor, 0.0)
    if profile.name == "天台篮球场" and precipitation_mm > 2:
        rain_impact += 18
        if not is_raining:
            drying_offset *= 0.55
    if profile.name == "街头健身区" and not is_raining:
        drying_offset += 12
    wetness = rain_impact + humidity_impact - drying_offset
    return int(max(0, min(100, round(wetness))))


def _calculate_suitability(profile: VenueProfile, wetness_level_pct: int, precipitation_mm: float, is_raining: bool) -> int:
    score = 100 - wetness_level_pct - profile.base_risk_penalty
    if profile.name == "天台篮球场" and precipitation_mm > 2:
        score -= 15
    if profile.name == "深圳大学体育场" and precipitation_mm <= 8:
        score += 8
    if profile.name == "街头健身区" and not is_raining:
        score += 10
    if is_raining and profile.name == "街头健身区" and precipitation_mm >= 20:
        score -= 12
    return int(max(0, min(100, round(score))))


def _build_notice(profile: VenueProfile, wetness_level_pct: int, suitability_score: int, precipitation_mm: float, is_raining: bool) -> str:
    if profile.name == "天台篮球场":
        if precipitation_mm > 2:
            return "胶面极滑且有局部积水，强烈不建议进行变向和弹跳训练！建议切换至室内有氧。"
        if wetness_level_pct >= 45:
            return "地面返潮明显，急停和横移仍有打滑风险，建议只做低强度投篮或热身。"
        return "场地基本干爽，可正常训练，但启动前仍建议先试踩确认摩擦力。"
    if profile.name == "深圳大学体育场":
        if is_raining and precipitation_mm >= 12:
            return "跑道存在短时积水，直道慢跑尚可，弯道冲刺和钉鞋训练建议延后。"
        if wetness_level_pct >= 35:
            return "跑道略微潮湿，直道慢跑无影响，弯道加速请注意防滑。"
        return "塑胶跑道状态稳定，可正常完成耐力跑和节奏跑训练。"
    if is_raining and precipitation_mm >= 20:
        return "虽然排水快，但暴雨后器械握把和踏板仍偏湿，训练前先擦干接触面更稳妥。"
    if wetness_level_pct >= 25:
        return "地面有少量残余水迹，器械区可练，爆发式跳跃动作建议暂缓 20 分钟。"
    return "塑胶板结构排水良好，表面基本无积水，可正常进行力量器械训练。"
