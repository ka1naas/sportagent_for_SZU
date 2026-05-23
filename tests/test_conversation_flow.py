from pathlib import Path
import sys

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.main import app


SESSION_ID = "test_hackathon_001"
OUTPUT_DIR = Path("tests/outputs")
OUTPUT_FILE = OUTPUT_DIR / "sample_boundary_test_001.md"


def run_conversation_flow_test() -> None:
    """
    模拟一个完整的 5 步问卷会话，并在最终生成边界条件 Markdown 文档。

    运行方式：
    `python -m tests.test_conversation_flow`
    或
    `python tests/test_conversation_flow.py`
    """
    client = TestClient(app)

    step1_response = client.post(
        "/api/v1/chat/step1_profile",
        json={
            "session_id": SESSION_ID,
            "gender": "第三性别",
            "height_cm": 172,
            "weight_kg": 68,
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

    boundary_response = client.get(f"/api/v1/chat/boundary_conditions/{SESSION_ID}")
    assert boundary_response.status_code == 200, boundary_response.text

    response_data = boundary_response.json()
    markdown_document = response_data["markdown_document"]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(markdown_document, encoding="utf-8")

    print(f"Boundary conditions Markdown 已生成：{OUTPUT_FILE}")
    print("运行命令：python -m tests.test_conversation_flow")


if __name__ == "__main__":
    run_conversation_flow_test()
