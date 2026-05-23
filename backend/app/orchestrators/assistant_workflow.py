from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session

from backend.app.adapters.llm_adapter import LLMAdapter
from backend.app.core.prompt_aggregator import FitnessPromptAggregator
from backend.app.domains.weather_domain import evaluate_weather_venues, fetch_weather_snapshot
from backend.app.models.chat import AssistantRouteKind, AssistantToolName
from backend.app.orchestrators.fitness_workflow import (
    _get_active_plan_record,
    build_plan_id,
    generate_initial_plan,
    refine_plan,
)
from backend.app.subsystems.boundary_collector import BoundaryCollectorService


def _build_assistant_tools() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": AssistantToolName.generate_training_plan.value,
                "description": "在用户已完成五步背景采集后，生成第一版训练与饮食计划。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "trigger_reason": {"type": "string"},
                    },
                    "required": ["trigger_reason"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": AssistantToolName.refine_training_plan.value,
                "description": "根据用户反馈修改当前训练计划。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_feedback": {"type": "string"},
                    },
                    "required": ["user_feedback"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": AssistantToolName.check_training_weather.value,
                "description": "判断现在是否适合去训练，并结合天气与场馆情况返回建议。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_question": {"type": "string"},
                    },
                    "required": ["user_question"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": AssistantToolName.answer_general_question.value,
                "description": "回答用户关于训练、饮食、恢复等普通问题。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_question": {"type": "string"},
                    },
                    "required": ["user_question"],
                },
            },
        },
    ]


def _build_weather_message(weather_assessment: Any) -> str:
    if not weather_assessment.venue_statuses:
        return "当前暂无足够的天气与场馆信息，建议先做室内轻量训练。"

    best_venue = sorted(weather_assessment.venue_statuses, key=lambda item: item.suitability_score, reverse=True)[0]
    weather_snapshot = weather_assessment.weather_snapshot
    return (
        f"现在{'在下雨' if weather_snapshot.is_raining else '天气相对稳定'}，"
        f"更推荐去 {best_venue.venue_name}。{best_venue.notice}"
    )


async def run_assistant_turn(
    *,
    session_id: str,
    message: str,
    is_initial_planning_turn: bool,
    plan_id: Optional[str],
    db: Session,
) -> dict[str, Any]:
    collector = BoundaryCollectorService(db)
    boundary_conditions = collector.get_complete_boundary(session_id)
    aggregator = FitnessPromptAggregator()
    llm_adapter = LLMAdapter()
    active_plan = _get_active_plan_record(db, session_id)

    if is_initial_planning_turn and active_plan is None:
        generated_text = await generate_initial_plan(session_id, db)
        refreshed_plan = _get_active_plan_record(db, session_id)
        return {
            "session_id": session_id,
            "route_kind": AssistantRouteKind.generate_plan,
            "assistant_message": generated_text,
            "plan_id": build_plan_id(session_id),
            "structured_plan": refreshed_plan.structured_plan if refreshed_plan else None,
            "change_summary": "初始生成",
            "weather_snapshot": None,
            "venue_statuses": [],
        }

    weather_snapshot = await fetch_weather_snapshot()
    weather_assessment = evaluate_weather_venues(weather_snapshot)
    router_messages = aggregator.build_assistant_router_prompt(
        boundary_conditions=boundary_conditions,
        current_plan=active_plan.structured_plan if active_plan else None,
        user_message=message,
        is_initial_planning_turn=is_initial_planning_turn,
        has_active_plan=active_plan is not None,
    )
    tool_result = llm_adapter.generate_tool_call(
        messages=router_messages,
        tools=_build_assistant_tools(),
        tool_choice="auto",
    )

    tool_name = tool_result["tool_name"]
    arguments = tool_result["arguments"]

    if tool_name == AssistantToolName.generate_training_plan.value:
        generated_text = await generate_initial_plan(session_id, db)
        refreshed_plan = _get_active_plan_record(db, session_id)
        return {
            "session_id": session_id,
            "route_kind": AssistantRouteKind.generate_plan,
            "assistant_message": generated_text,
            "plan_id": build_plan_id(session_id),
            "structured_plan": refreshed_plan.structured_plan if refreshed_plan else None,
            "change_summary": "初始生成",
            "weather_snapshot": None,
            "venue_statuses": [],
        }

    if tool_name == AssistantToolName.refine_training_plan.value:
        target_plan_id = plan_id or build_plan_id(session_id)
        refined_text = await refine_plan(session_id, arguments["user_feedback"], db)
        refreshed_plan = _get_active_plan_record(db, session_id)
        return {
            "session_id": session_id,
            "route_kind": AssistantRouteKind.refine_plan,
            "assistant_message": refined_text,
            "plan_id": target_plan_id,
            "structured_plan": refreshed_plan.structured_plan if refreshed_plan else None,
            "change_summary": refreshed_plan.change_summary if refreshed_plan else None,
            "weather_snapshot": None,
            "venue_statuses": [],
        }

    if tool_name == AssistantToolName.check_training_weather.value:
        return {
            "session_id": session_id,
            "route_kind": AssistantRouteKind.weather_check,
            "assistant_message": _build_weather_message(weather_assessment),
            "plan_id": plan_id or (build_plan_id(session_id) if active_plan else None),
            "structured_plan": active_plan.structured_plan if active_plan else None,
            "change_summary": None,
            "weather_snapshot": weather_assessment.weather_snapshot.model_dump(),
            "venue_statuses": [venue.model_dump() for venue in weather_assessment.venue_statuses],
        }

    general_messages = aggregator.build_general_answer_prompt(
        boundary_conditions=boundary_conditions,
        current_plan=active_plan.structured_plan if active_plan else None,
        user_message=arguments["user_question"],
    )
    assistant_message = llm_adapter.generate_text(general_messages)
    return {
        "session_id": session_id,
        "route_kind": AssistantRouteKind.general_answer,
        "assistant_message": assistant_message,
        "plan_id": plan_id or (build_plan_id(session_id) if active_plan else None),
        "structured_plan": active_plan.structured_plan if active_plan else None,
        "change_summary": None,
        "weather_snapshot": None,
        "venue_statuses": [],
    }
