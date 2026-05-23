from pathlib import Path
import sys

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.main import app


SESSION_ID = "test_ai_plan_001"
OUTPUT_DIR = Path("tests/outputs")
PLAN_OUTPUT_FILE = OUTPUT_DIR / "sample_ai_plan_test_001.md"
REFINED_PLAN_OUTPUT_FILE = OUTPUT_DIR / "sample_ai_plan_refined_test_001.md"


def _prepare_boundary_conditions(client: TestClient) -> None:
    step1_response = client.post(
        "/api/v1/chat/step1_profile",
        json={
            "session_id": SESSION_ID,
            "gender": "第三性别",
            "height_cm": 170,
            "weight_kg": 65,
        },
    )
    assert step1_response.status_code == 200, step1_response.text

    step2_response = client.post(
        "/api/v1/chat/step2_goal",
        json={
            "session_id": SESSION_ID,
            "goal": "减脂",
            "accept_muscle_loss": "接受",
        },
    )
    assert step2_response.status_code == 200, step2_response.text

    step3_response = client.post(
        "/api/v1/chat/step3_space_time",
        json={
            "session_id": SESSION_ID,
            "frequency": "3-4次",
            "duration": "45-60分钟",
            "preference": "下课后",
            "dorm_location": "西南区",
            "schedule_image_url": None,
        },
    )
    assert step3_response.status_code == 200, step3_response.text

    step4_response = client.post(
        "/api/v1/chat/step4_diet",
        json={
            "session_id": SESSION_ID,
            "preferred_canteens": ["听荔餐厅"],
            "weekly_budget": "极限穷鬼<300元",
        },
    )
    assert step4_response.status_code == 200, step4_response.text

    step5_response = client.post(
        "/api/v1/chat/step5_habits",
        json={
            "session_id": SESSION_ID,
            "favorite_sport": "篮球",
            "integrate_into_training": True,
        },
    )
    assert step5_response.status_code == 200, step5_response.text


def run_ai_plan_flow_test() -> None:
    """
    测试 AI 计划生成与反馈修正闭环。

    运行方式：
    `python -m tests.test_ai_plan_flow`
    或
    `python tests/test_ai_plan_flow.py`
    """
    client = TestClient(app)
    _prepare_boundary_conditions(client)

    generate_response = client.post(
        "/api/v1/plan/generate",
        json={"session_id": SESSION_ID},
    )
    assert generate_response.status_code == 200, generate_response.text

    generate_data = generate_response.json()
    plan_id = generate_data["plan_id"]
    plan_text = generate_data["plan_text"]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PLAN_OUTPUT_FILE.write_text(plan_text, encoding="utf-8")

    refine_response = client.post(
        "/api/v1/plan/refine",
        json={
            "session_id": SESSION_ID,
            "plan_id": plan_id,
            "user_feedback": "听荔餐厅太远了，换成离西南区更近的食堂；我不喜欢长时间跑步。",
        },
    )
    assert refine_response.status_code == 200, refine_response.text

    refine_data = refine_response.json()
    refined_plan_text = refine_data["refined_plan_text"]
    REFINED_PLAN_OUTPUT_FILE.write_text(refined_plan_text, encoding="utf-8")

    print(f"AI 初步计划已生成：{PLAN_OUTPUT_FILE}")
    print(f"AI 修正版计划已生成：{REFINED_PLAN_OUTPUT_FILE}")
    print("运行命令：python -m tests.test_ai_plan_flow")


if __name__ == "__main__":
    run_ai_plan_flow_test()
