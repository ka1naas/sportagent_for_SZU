from pathlib import Path
import sys

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.main import app
from db import init_db
from backend.app.domains.diet_domain import DietPlanningInput, calculate_macro_targets, generate_diet_plan, load_canteen_items


def test_calculate_daily_macros_for_fat_loss() -> None:
    result = calculate_macro_targets(gender="男", height_cm=175, weight_kg=70, goal="减脂").model_dump()

    assert result["estimated_tdee"] > result["estimated_bmr"]
    assert result["target_calories"] < result["estimated_tdee"]
    assert result["target_protein_g"] >= 130
    assert result["target_carbs_g"] > 0


def test_generate_canteen_context_matches_budget_and_location() -> None:
    user_macros = {
        "target_protein_g": 140.0,
        "target_carbs_g": 180.0,
        "target_fat_g": 45.0,
        "target_calories": 1950.0,
    }

    result = generate_diet_plan(
        DietPlanningInput(
            user_location="西南区教学楼",
            user_macros=calculate_macro_targets(gender="男", height_cm=175, weight_kg=70, goal="减脂"),
            budget_level="极限穷鬼<300元",
            canteen_items=load_canteen_items(),
        )
    ).model_dump()

    assert result["recommended_nearby_canteens"][0] == "粤海校区荔园食堂"
    assert len(result["candidate_dishes"]) >= 1
    assert all(item["price"] <= 18 for item in result["candidate_dishes"])


def test_save_profile_endpoint_persists_and_returns_diet_context() -> None:
    init_db()
    client = TestClient(app)
    response = client.post(
        "/api/v1/user/save_profile",
        json={
            "session_id": "persist_test_001",
            "gender": "男",
            "height_cm": 175,
            "weight_kg": 70,
            "goal": "减脂",
            "budget_level": "普通学生300-500元",
            "raw_answers": {
                "profile": {"gender": "男", "height_cm": 175, "weight_kg": 70},
                "goal": {"primary": "减脂", "accept_muscle_loss": True},
                "dorm_location": "西南区",
            },
            "schedules": [
                {"weekday": "Mon", "time_start": "08:00", "time_end": "09:40", "location": "西南区教学楼"},
                {"weekday": "Tue", "time_start": "14:00", "time_end": "15:40", "location": "粤海街道"},
            ],
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()

    assert payload["session_id"] == "persist_test_001"
    assert payload["saved_schedule_count"] == 2
    assert payload["macros"]["target_protein_g"] > 0
    assert len(payload["diet_context"]["recommended_nearby_canteens"]) >= 1
    assert "advice" in payload["diet_context"]["nutrition_advice"]


if __name__ == "__main__":
    test_calculate_daily_macros_for_fat_loss()
    test_generate_canteen_context_matches_budget_and_location()
    test_save_profile_endpoint_persists_and_returns_diet_context()
