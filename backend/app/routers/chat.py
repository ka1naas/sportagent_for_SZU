from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.models.chat import (
    AcceptanceOption,
    AssistantChatRequest,
    AssistantChatResponse,
    ChatStepResponse,
    DietStepRequest,
    ProfileStepRequest,
    GoalOption,
    GoalStepRequest,
    HabitStepRequest,
    SpaceTimeStepRequest,
    StepName,
)
from backend.app.models.schemas import BoundaryConditionsResponse
from backend.app.orchestrators.assistant_workflow import run_assistant_turn
from backend.app.subsystems.boundary_collector import BoundaryCollectorService
from backend.app.utils import build_boundary_conditions, generate_markdown_boundary
from db.database import get_db


router = APIRouter()
collector_service = BoundaryCollectorService()


GOAL_SCIENCE_TIPS = {
    GoalOption.fat_loss: "减脂的核心是长期保持热量赤字，同时尽量保证蛋白质摄入和基础力量训练。",
    GoalOption.muscle_gain: "增肌需要循序渐进的力量训练、充足蛋白质和稳定恢复。",
    GoalOption.strength: "力量提升依赖高质量复合动作、渐进超负荷和充分休息。",
    GoalOption.power: "爆发力训练强调神经募集效率、动作速度和较低疲劳度。",
    GoalOption.endurance: "耐力提升需要控制训练分区，并逐步提高总训练量。",
}


def _require_previous_step(session_id: str, expected_step: StepName) -> dict:
    session = collector_service.get_session(session_id)
    if session is None:
        collector_service.update_step_data(session_id, StepName.step1_profile, {})
        session = collector_service.get_session(session_id)
        if session is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="会话初始化失败。")
    current_step = StepName(session["current_step"])

    ordered_steps = [
        StepName.step1_profile,
        StepName.step2_goal,
        StepName.step3_space_time,
        StepName.step4_diet,
        StepName.step5_habits,
        StepName.completed,
    ]

    if ordered_steps.index(current_step) < ordered_steps.index(expected_step):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"当前会话尚未完成前置步骤，当前步骤为 {current_step.value}。",
        )

    return session


@router.post("/step1_profile", response_model=ChatStepResponse, summary="Step 1: 身体基础信息")
def submit_profile_step(payload: ProfileStepRequest) -> ChatStepResponse:
    session = collector_service.get_session(payload.session_id)
    if session is not None and StepName(session["current_step"]) == StepName.completed:
        collector_service.reset_session(payload.session_id)

    result = collector_service.update_step_data(
        payload.session_id,
        StepName.step1_profile,
        {
            "gender": payload.gender.value,
            "height_cm": payload.height_cm,
            "weight_kg": payload.weight_kg,
        },
    )

    return ChatStepResponse(
        session_id=payload.session_id,
        current_step=StepName.step1_profile,
        next_step=StepName.step2_goal,
        message="已记录身体基础信息。",
        data={"session": result["payload"]},
    )


@router.post("/step2_goal", response_model=ChatStepResponse, summary="Step 2: 锻炼目标")
def submit_goal_step(payload: GoalStepRequest) -> ChatStepResponse:
    if payload.goal == GoalOption.fat_loss and payload.accept_muscle_loss is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="选择减脂时必须回答是否接受掉部分肌肉。",
        )

    _require_previous_step(payload.session_id, StepName.step2_goal)
    result = collector_service.update_step_data(
        payload.session_id,
        StepName.step2_goal,
        {
            "goal": payload.goal.value,
            "accept_muscle_loss": payload.accept_muscle_loss.value if payload.accept_muscle_loss else None,
        },
    )

    follow_up_question = (
        "是否接受掉部分肌肉？减脂是一个长期的热量赤字过程，速度较慢。"
        if payload.goal == GoalOption.fat_loss
        else None
    )

    return ChatStepResponse(
        session_id=payload.session_id,
        current_step=StepName.step2_goal,
        next_step=StepName.step3_space_time,
        message="已记录锻炼目标。",
        data={
            "science_tip": GOAL_SCIENCE_TIPS[payload.goal],
            "follow_up_question": follow_up_question,
            "session": result["payload"],
        },
    )


@router.post("/step3_space_time", response_model=ChatStepResponse, summary="Step 3: 时空约束")
def submit_space_time_step(payload: SpaceTimeStepRequest) -> ChatStepResponse:
    _require_previous_step(payload.session_id, StepName.step3_space_time)
    result = collector_service.update_step_data(
        payload.session_id,
        StepName.step3_space_time,
        {
            "frequency": payload.frequency.value,
            "duration": payload.duration.value,
            "preference": payload.preference.value,
            "dorm_location": payload.dorm_location,
            "schedule_image_url": payload.schedule_image_url,
        },
    )

    return ChatStepResponse(
        session_id=payload.session_id,
        current_step=StepName.step3_space_time,
        next_step=StepName.step4_diet,
        message="已记录时空约束。",
        data={"session": result["payload"]},
    )


@router.post("/step4_diet", response_model=ChatStepResponse, summary="Step 4: 饮食与预算")
def submit_diet_step(payload: DietStepRequest) -> ChatStepResponse:
    _require_previous_step(payload.session_id, StepName.step4_diet)
    result = collector_service.update_step_data(
        payload.session_id,
        StepName.step4_diet,
        {
            "preferred_canteens": payload.preferred_canteens,
            "weekly_budget": payload.weekly_budget.value,
        },
    )

    return ChatStepResponse(
        session_id=payload.session_id,
        current_step=StepName.step4_diet,
        next_step=StepName.step5_habits,
        message="已记录饮食与预算偏好。",
        data={"session": result["payload"]},
    )


@router.post("/step5_habits", response_model=ChatStepResponse, summary="Step 5: 运动习惯")
def submit_habit_step(payload: HabitStepRequest) -> ChatStepResponse:
    favorite_sport = payload.favorite_sport_other if payload.favorite_sport.value == "其他" else payload.favorite_sport.value

    if payload.favorite_sport.value == "其他" and not payload.favorite_sport_other:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="当喜爱运动选择‘其他’时，必须提供 favorite_sport_other。",
        )

    _require_previous_step(payload.session_id, StepName.step5_habits)
    result = collector_service.update_step_data(
        payload.session_id,
        StepName.step5_habits,
        {
            "favorite_sport": payload.favorite_sport.value,
            "favorite_sport_other": favorite_sport if payload.favorite_sport.value == "其他" else None,
            "integrate_into_training": payload.integrate_into_training,
        },
    )

    return ChatStepResponse(
        session_id=payload.session_id,
        current_step=StepName.step5_habits,
        next_step=StepName.completed,
        message="已完成 5 步问卷收集。",
        data={"session": result["payload"]},
    )


@router.get(
    "/boundary_conditions/{session_id}",
    response_model=BoundaryConditionsResponse,
    summary="生成边界条件文档",
)
def get_boundary_conditions(session_id: str) -> BoundaryConditionsResponse:
    session = collector_service.get_session(session_id)

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到对应的会话数据。",
        )

    current_step = StepName(session["current_step"])
    if current_step != StepName.completed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="当前会话尚未完成 5 步问卷，无法生成边界条件文档。",
        )

    boundary_conditions = build_boundary_conditions(session_id, session["payload"])
    markdown_document = generate_markdown_boundary(boundary_conditions)

    return BoundaryConditionsResponse(
        session_id=session_id,
        current_step=current_step,
        boundary_conditions=boundary_conditions,
        markdown_document=markdown_document,
    )

@router.post("/assistant", response_model=AssistantChatResponse, summary="统一 AI 对话主入口")
async def assistant_chat(payload: AssistantChatRequest, db: Session = Depends(get_db)) -> AssistantChatResponse:
    try:
        result = await run_assistant_turn(
            session_id=payload.session_id,
            message=payload.message,
            is_initial_planning_turn=payload.is_initial_planning_turn,
            plan_id=payload.plan_id,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return AssistantChatResponse(**result)
