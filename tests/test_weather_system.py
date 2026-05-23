from pathlib import Path
import sys

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.main import app
from backend.app.routers import weather_routes


def _assert_sorted_suitability(payload: dict) -> None:
    venue_statuses = payload["venue_statuses"]
    score_map = {item["venue_name"]: item["suitability_score"] for item in venue_statuses}

    assert score_map["街头健身区"] >= score_map["深圳大学体育场"] >= score_map["天台篮球场"]


def test_weather_route_with_clear_weather() -> None:
    async def fake_weather() -> dict:
        return {
            "location": "深圳南山区粤海街道",
            "precipitation_mm": 0.0,
            "temperature_c": 31.0,
            "humidity_pct": 58,
            "is_raining": False,
            "source": "test",
            "observation_window_hours": 1,
        }

    original_getter = weather_routes.weather_client.get_yuehai_precipitation
    weather_routes.weather_client.get_yuehai_precipitation = fake_weather
    try:
        client = TestClient(app)
        response = client.get("/api/v1/weather/venue-status")
    finally:
        weather_routes.weather_client.get_yuehai_precipitation = original_getter

    assert response.status_code == 200, response.text
    payload = response.json()

    assert payload["location"] == "深圳南山区粤海街道"
    assert payload["weather_snapshot"]["precipitation_mm"] == 0.0
    assert payload["weather_snapshot"]["is_raining"] is False
    assert len(payload["venue_statuses"]) == 3
    _assert_sorted_suitability(payload)

    score_map = {item["venue_name"]: item["suitability_score"] for item in payload["venue_statuses"]}
    wetness_map = {item["venue_name"]: item["wetness_level_pct"] for item in payload["venue_statuses"]}

    assert score_map["街头健身区"] >= 90
    assert score_map["深圳大学体育场"] >= 75
    assert score_map["天台篮球场"] >= 65
    assert wetness_map["街头健身区"] <= wetness_map["深圳大学体育场"] <= wetness_map["天台篮球场"]


def test_weather_route_with_moderate_rain() -> None:
    async def fake_weather() -> dict:
        return {
            "location": "深圳南山区粤海街道",
            "precipitation_mm": 8.0,
            "temperature_c": 28.0,
            "humidity_pct": 82,
            "is_raining": True,
            "source": "test",
            "observation_window_hours": 1,
        }

    original_getter = weather_routes.weather_client.get_yuehai_precipitation
    weather_routes.weather_client.get_yuehai_precipitation = fake_weather
    try:
        client = TestClient(app)
        response = client.get("/api/v1/weather/venue-status")
    finally:
        weather_routes.weather_client.get_yuehai_precipitation = original_getter

    assert response.status_code == 200, response.text
    payload = response.json()
    _assert_sorted_suitability(payload)

    venue_map = {item["venue_name"]: item for item in payload["venue_statuses"]}

    assert venue_map["天台篮球场"]["can_exercise"] is False
    assert venue_map["天台篮球场"]["suitability_score"] <= 25
    assert venue_map["深圳大学体育场"]["suitability_score"] >= 20
    assert venue_map["街头健身区"]["suitability_score"] >= venue_map["深圳大学体育场"]["suitability_score"]


def test_weather_route_after_heavy_rain_stopped() -> None:
    async def fake_weather() -> dict:
        return {
            "location": "深圳南山区粤海街道",
            "precipitation_mm": 25.0,
            "temperature_c": 30.0,
            "humidity_pct": 88,
            "is_raining": False,
            "source": "test",
            "observation_window_hours": 3,
        }

    original_getter = weather_routes.weather_client.get_yuehai_precipitation
    weather_routes.weather_client.get_yuehai_precipitation = fake_weather
    try:
        client = TestClient(app)
        response = client.get("/api/v1/weather/venue-status")
    finally:
        weather_routes.weather_client.get_yuehai_precipitation = original_getter

    assert response.status_code == 200, response.text
    payload = response.json()
    _assert_sorted_suitability(payload)

    venue_map = {item["venue_name"]: item for item in payload["venue_statuses"]}

    assert venue_map["天台篮球场"]["wetness_level_pct"] >= 85
    assert venue_map["天台篮球场"]["can_exercise"] is False
    assert venue_map["深圳大学体育场"]["wetness_level_pct"] < venue_map["天台篮球场"]["wetness_level_pct"]
    assert venue_map["街头健身区"]["wetness_level_pct"] < venue_map["深圳大学体育场"]["wetness_level_pct"]
    assert venue_map["街头健身区"]["suitability_score"] > venue_map["深圳大学体育场"]["suitability_score"]
