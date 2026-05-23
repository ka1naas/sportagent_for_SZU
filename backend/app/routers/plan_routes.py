from fastapi import APIRouter, HTTPException, status
import asyncio
from fastapi import Depends
from sqlalchemy.orm import Session

from backend.app.models.schemas import (
    PlanAcceptRequest,
    PlanAcceptResponse,
    PlanFeedbackRequest,
    PlanGenerateRequest,
    PlanGenerateResponse,
    PlanRefineResponse,
    UserBoundaryConditions,
)
from db.models import PlanHistory
from backend.app.orchestrators.fitness_workflow import accept_plan as orchestrator_accept_plan
from backend.app.orchestrators.fitness_workflow import build_plan_id, generate_initial_plan, refine_plan as orchestrator_refine_plan
from backend.app.subsystems.boundary_collector import BoundaryCollectorService
from db.database import get_db


router = APIRouter()
collector_service = BoundaryCollectorService()


def _build_boundary_schema(session_id: str) -> UserBoundaryConditions:
    session = collector_service.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到对应的用户会话。",
        )

    payload = session["payload"]
    required_fields = ["profile", "goal", "spatiotemporal", "dietary", "habits"]
    missing_fields = [field_name for field_name in required_fields if field_name not in payload]
    if missing_fields:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"边界条件未收集完整，缺少字段: {missing_fields}",
        )

    return UserBoundaryConditions(session_id=session_id, **payload)


@router.post("/generate", response_model=PlanGenerateResponse, summary="生成初步训练与饮食计划")
def generate_plan(payload: PlanGenerateRequest, db: Session = Depends(get_db)) -> PlanGenerateResponse:
    boundary_data = _build_boundary_schema(payload.session_id)
    plan_text = asyncio.run(generate_initial_plan(payload.session_id, db))

    plan_id = build_plan_id(payload.session_id)
    stored_plan = db.query(PlanHistory).filter(PlanHistory.plan_id == plan_id).one()

    return PlanGenerateResponse(
        session_id=payload.session_id,
        plan_id=plan_id,
        plan_text=plan_text,
        prompt_context=boundary_data.model_dump(),
        structured_plan=stored_plan.structured_plan,
    )


@router.post("/refine", response_model=PlanRefineResponse, summary="根据用户反馈修正计划")
def refine_plan(payload: PlanFeedbackRequest, db: Session = Depends(get_db)) -> PlanRefineResponse:
    if payload.plan_id != build_plan_id(payload.session_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="plan_id 与 session_id 不匹配。",
        )

    try:
        refined_plan_text = asyncio.run(orchestrator_refine_plan(payload.session_id, payload.user_feedback, db))
    except (KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    stored_plan = db.query(PlanHistory).filter(PlanHistory.plan_id == payload.plan_id).one()

    return PlanRefineResponse(
        session_id=payload.session_id,
        plan_id=payload.plan_id,
        refined_plan_text=refined_plan_text,
        feedback_applied=payload.user_feedback,
        structured_plan=stored_plan.structured_plan,
        change_summary=stored_plan.change_summary,
    )


@router.post("/accept", response_model=PlanAcceptResponse, summary="确认并锁定最终计划")
def accept_plan(payload: PlanAcceptRequest, db: Session = Depends(get_db)) -> PlanAcceptResponse:
    if payload.plan_id != build_plan_id(payload.session_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="plan_id 与 session_id 不匹配。",
        )

    try:
        accepted_result = orchestrator_accept_plan(payload.session_id, db)
    except (KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return PlanAcceptResponse(
        session_id=payload.session_id,
        plan_id=payload.plan_id,
        final_plan_text=accepted_result["final_plan_text"],
        status=accepted_result["status"],
    )
