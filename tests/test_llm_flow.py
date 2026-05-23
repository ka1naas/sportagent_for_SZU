from pathlib import Path
import sys

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.main import app


SESSION_ID = "test_llm_flow_001"


def _prepare_session(client: TestClient) -> None:
    client.post(
        "/api/v1/chat/step1_profile",
        json={"session_id": SESSION_ID, "gender": "第三性别", "height_cm": 171, "weight_kg": 66},
    )
    client.post(
        "/api/v1/chat/step2_goal",
        json={"session_id": SESSION_ID, "goal": "减脂", "accept_muscle_loss": "接受"},
    )
    client.post(
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
    client.post(
        "/api/v1/chat/step4_diet",
        json={"session_id": SESSION_ID, "preferred_canteens": ["听荔餐厅"], "weekly_budget": "极限穷鬼<300元"},
    )
    client.post(
        "/api/v1/chat/step5_habits",
        json={"session_id": SESSION_ID, "favorite_sport": "篮球", "integrate_into_training": True},
    )


def run_llm_flow_test() -> None:
    """
    测试真实 LLM 接入后的计划闭环路由。

    当前测试会直接发起真实模型调用。
    运行前请确保 [`backend/.env.example`](backend/.env.example) 或 [`backend/.env`](backend/.env)
    中已配置可用的 `LLM_BASE_URL`、`LLM_API_KEY` 与模型名。
    """
    client = TestClient(app)
    _prepare_session(client)

    generate_response = client.post("/api/v1/plan/generate", json={"session_id": SESSION_ID})
    assert generate_response.status_code == 200, generate_response.text
    generate_data = generate_response.json()
    plan_id = generate_data["plan_id"]
    assert generate_data["plan_text"].strip() != ""

    refine_response_1 = client.post(
        "/api/v1/plan/refine",
        json={
            "session_id": SESSION_ID,
            "plan_id": plan_id,
            "user_feedback": "我不喜欢跑步，预算再少一点",
        },
    )
    assert refine_response_1.status_code == 200, refine_response_1.text
    refine_data_1 = refine_response_1.json()
    assert refine_data_1["refined_plan_text"].strip() != ""

    refine_response_2 = client.post(
        "/api/v1/plan/refine",
        json={
            "session_id": SESSION_ID,
            "plan_id": plan_id,
            "user_feedback": "能不能加入室内的运动",
        },
    )
    assert refine_response_2.status_code == 200, refine_response_2.text
    refine_data_2 = refine_response_2.json()
    assert refine_data_2["refined_plan_text"].strip() != ""

    accept_response = client.post(
        "/api/v1/plan/accept",
        json={"session_id": SESSION_ID, "plan_id": plan_id},
    )
    assert accept_response.status_code == 200, accept_response.text
    accept_data = accept_response.json()
    assert accept_data["status"] == "accepted"
    assert accept_data["final_plan_text"].strip() != ""

    print("LLM 闭环测试通过：generate -> refine -> refine -> accept")


if __name__ == "__main__":
    run_llm_flow_test()
