from pydantic import ValidationError

from backend.app.models.schemas import UserBoundaryConditions


def build_boundary_conditions(session_id: str, session_data: dict) -> UserBoundaryConditions:
    """
    将状态机 4 步收集到的 session 数据组装为统一的边界条件文档结构。

    该结构既是后续算法层、调度层的标准输入，也可以直接转换成适合
    人类阅读和 LLM 消化的 Markdown 文档。
    """
    required_fields = ("profile", "goal", "spatiotemporal", "dietary", "habits")
    missing_fields = [field_name for field_name in required_fields if field_name not in session_data]
    if missing_fields:
        raise ValueError(f"边界条件数据缺失必要字段: {', '.join(missing_fields)}")

    try:
        return UserBoundaryConditions(
            session_id=session_id,
            profile=session_data["profile"],
            goal=session_data["goal"],
            spatiotemporal=session_data["spatiotemporal"],
            dietary=session_data["dietary"],
            habits=session_data["habits"],
        )
    except ValidationError as exc:
        raise ValueError(f"边界条件数据格式不合法: {exc}") from exc


def generate_markdown_boundary(session_data: UserBoundaryConditions) -> str:
    """
    将结构化的边界条件 JSON 转换为 Markdown 文本。

    设计目标：
    1. 对人类贡献者足够直观，便于调试和审阅；
    2. 对后续 LLM 输入足够清晰，尽量减少语义歧义；
    3. 保持字段顺序稳定，利于日志记录与版本对比。
    """
    profile = session_data.profile
    goal = session_data.goal
    spatiotemporal = session_data.spatiotemporal
    dietary = session_data.dietary
    habits = session_data.habits

    preferred_canteens = dietary.preferred_canteens
    preferred_canteens_text = "、".join(preferred_canteens) if preferred_canteens else "未填写"

    markdown_lines = [
        "# User Boundary Conditions",
        "",
        f"- Session ID: {session_data.session_id}",
        "",
        "## 1. Physical Profile",
        f"- Gender: {profile.gender}",
        f"- Height (cm): {profile.height_cm}",
        f"- Weight (kg): {profile.weight_kg}",
        "",
        "## 2. Goal",
        f"- Primary Goal: {goal.primary}",
        f"- Accept Muscle Loss: {goal.accept_muscle_loss if goal.accept_muscle_loss is not None else '未填写'}",
        "",
        "## 3. Spatiotemporal Constraints",
        f"- Frequency Per Week: {spatiotemporal.frequency}",
        f"- Duration: {spatiotemporal.duration}",
        f"- Preference: {spatiotemporal.preference}",
        f"- Dorm Location: {spatiotemporal.dorm_location}",
        f"- Schedule Image URL: {spatiotemporal.schedule_image_url or '未上传'}",
        "",
        "## 4. Dietary Constraints",
        f"- Preferred Canteens: {preferred_canteens_text}",
        f"- Weekly Budget: {dietary.weekly_budget}",
        "",
        "## 5. Habit Preferences",
        f"- Favorite Sport: {habits.favorite_sport}",
        f"- Integrate Into Training: {habits.integrate_into_training}",
    ]

    return "\n".join(markdown_lines)
