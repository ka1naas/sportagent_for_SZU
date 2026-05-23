from __future__ import annotations

from typing import Any, List

from db.models import PlanHistory
from sqlalchemy.orm import Session

from backend.app.adapters.llm_adapter import LLMAdapter
from backend.app.core.prompt_aggregator import FitnessPromptAggregator
from backend.app.domains.diet_domain import calculate_macro_targets, generate_diet_plan, load_canteen_items
from backend.app.domains.exercise_domain import load_exercise_templates, select_exercise_template
from backend.app.domains.schemas import DietPlanningInput
from backend.app.domains.weather_domain import evaluate_weather_venues, fetch_weather_snapshot
from backend.app.models.schemas import (
    PlanEditOperationSchema,
    PlanScheduleItemSchema,
    StructuredPlanRefinementToolResultSchema,
    StructuredPlanSchema,
    StructuredPlanToolResultSchema,
)
from backend.app.subsystems.boundary_collector import BoundaryCollectorService


def build_plan_id(session_id: str) -> str:
    return f"plan_{session_id}"


def _get_active_plan_record(db: Session, session_id: str) -> PlanHistory | None:
    return (
        db.query(PlanHistory)
        .filter(PlanHistory.session_id == session_id, PlanHistory.is_active.is_(True))
        .order_by(PlanHistory.id.desc())
        .first()
    )


def _build_structured_plan(*, boundary_conditions, weather_assessment, diet_recommendation, exercise_library) -> dict:
    schedule_items = [
        {
            "item_id": f"{index + 1}",
            "day": day,
            "time_period": boundary_conditions.spatiotemporal.preference,
            "location": venue.venue_name,
            "location_type": venue.surface_type,
            "training_type": boundary_conditions.goal.primary,
            "title": f"{day}{boundary_conditions.goal.primary}训练",
            "items": _extract_exercise_items(exercise_library),
            "fallback": _resolve_fallback(weather_assessment),
            "notes": venue.notice,
        }
        for index, (day, venue) in enumerate(
            zip(_resolve_training_days(boundary_conditions.spatiotemporal.frequency), weather_assessment.venue_statuses)
        )
    ]

    structured = StructuredPlanSchema(
        plan_summary=f"围绕{boundary_conditions.goal.primary}目标生成的周训练与饮食计划。",
        weekly_schedule=schedule_items,
        diet_plan=diet_recommendation.model_dump(),
        warnings=[venue.notice for venue in weather_assessment.venue_statuses[:2]],
    )
    return structured.model_dump()


def _resolve_training_days(frequency: str) -> list[str]:
    mapping = {
        "1-2次": ["周二", "周六"],
        "3-4次": ["周一", "周三", "周五", "周日"],
        "5次以上": ["周一", "周二", "周三", "周五", "周六"],
    }
    return mapping.get(frequency, ["周三", "周六"])


def _extract_exercise_items(exercise_library) -> list[str]:
    template_data = exercise_library.template_data
    if isinstance(template_data, dict):
        for key in ("actions", "movements", "recommendations", "plan"):
            value = template_data.get(key)
            if isinstance(value, list):
                return [str(item) for item in value[:5]]
    return [exercise_library.template_name]


def _resolve_fallback(weather_assessment) -> str:
    indoor_candidates = [venue.venue_name for venue in weather_assessment.venue_statuses if "室内" in venue.surface_type]
    return indoor_candidates[0] if indoor_candidates else "改为宿舍/室内轻量训练"


def _apply_feedback_patch(structured_plan: dict, user_feedback: str) -> tuple[dict, str]:
    updated_plan = dict(structured_plan)
    weekly_schedule = list(updated_plan.get("weekly_schedule", []))
    original_len = len(weekly_schedule)

    if "周三" in user_feedback and ("健身房" in user_feedback or "体育馆" in user_feedback or "gym" in user_feedback.lower()):
        weekly_schedule = [
            item
            for item in weekly_schedule
            if not (item.get("day") == "周三" and ("馆" in item.get("location", "") or "gym" in item.get("location", "").lower()))
        ]
        change_summary = "已移除周三相关健身房/体育馆训练安排。"
    else:
        change_summary = f"已根据反馈调整计划：{user_feedback}"

    if len(weekly_schedule) == original_len and weekly_schedule:
        weekly_schedule[0]["notes"] = f"用户反馈已记录：{user_feedback}"

    updated_plan["weekly_schedule"] = weekly_schedule
    updated_plan["plan_summary"] = updated_plan.get("plan_summary", "") + "（已根据最新反馈更新）"
    return updated_plan, change_summary


def _build_generation_tool_spec() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "build_structured_plan",
                "description": "根据提供的结构化上下文生成完整训练与饮食计划。",
                "parameters": StructuredPlanToolResultSchema.model_json_schema(),
            },
        }
    ]


def _build_refinement_tool_spec() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "edit_structured_plan",
                "description": "基于当前结构化计划和用户反馈返回最小必要修改操作。",
                "parameters": StructuredPlanRefinementToolResultSchema.model_json_schema(),
            },
        }
    ]


def _normalize_generated_structured_plan(tool_arguments: dict[str, Any]) -> StructuredPlanToolResultSchema:
    return StructuredPlanToolResultSchema.model_validate(tool_arguments)


def _normalize_refinement_tool_result(tool_arguments: dict[str, Any]) -> StructuredPlanRefinementToolResultSchema:
    return StructuredPlanRefinementToolResultSchema.model_validate(tool_arguments)


def _match_schedule_item(schedule_items: list[dict[str, Any]], target: dict[str, Any] | None) -> int | None:
    if not target:
        return None

    target_item_id = target.get("item_id")
    if target_item_id:
        for item_index, schedule_item in enumerate(schedule_items):
            if schedule_item.get("item_id") == target_item_id:
                return item_index

    for item_index, schedule_item in enumerate(schedule_items):
        matches = True
        for field_name in ("day", "time_period", "location"):
            expected_value = target.get(field_name)
            if expected_value and schedule_item.get(field_name) != expected_value:
                matches = False
                break
        if matches:
            return item_index
    return None


def _next_schedule_item_id(schedule_items: list[dict[str, Any]]) -> str:
    numeric_ids = []
    for schedule_item in schedule_items:
        item_id = str(schedule_item.get("item_id", ""))
        if item_id.isdigit():
            numeric_ids.append(int(item_id))
    return str(max(numeric_ids, default=0) + 1)


def _apply_structured_plan_operations(
    structured_plan: dict[str, Any],
    operations: list[PlanEditOperationSchema],
) -> dict[str, Any]:
    patched_plan = dict(structured_plan)
    patched_schedule = [dict(item) for item in patched_plan.get("weekly_schedule", [])]

    for operation in operations:
        matched_index = _match_schedule_item(
            patched_schedule,
            operation.target.model_dump(exclude_none=True) if operation.target else None,
        )

        if operation.action == "delete_item":
            if matched_index is not None:
                patched_schedule.pop(matched_index)
            continue

        if operation.action == "add_item":
            if operation.new_item is None:
                continue
            new_schedule_item = operation.new_item.model_dump()
            new_schedule_item["item_id"] = _next_schedule_item_id(patched_schedule)
            validated_new_item = PlanScheduleItemSchema.model_validate(new_schedule_item)
            patched_schedule.append(validated_new_item.model_dump())
            continue

        if matched_index is None:
            continue

        schedule_item = dict(patched_schedule[matched_index])
        if operation.action == "move_item":
            if operation.new_day:
                schedule_item["day"] = operation.new_day
            if operation.new_time_period:
                schedule_item["time_period"] = operation.new_time_period
            if operation.new_location:
                schedule_item["location"] = operation.new_location
        elif operation.action == "replace_location":
            if operation.new_location:
                schedule_item["location"] = operation.new_location
        elif operation.action == "replace_notes":
            if operation.new_notes:
                schedule_item["notes"] = operation.new_notes

        validated_schedule_item = PlanScheduleItemSchema.model_validate(schedule_item)
        patched_schedule[matched_index] = validated_schedule_item.model_dump()

    patched_plan["weekly_schedule"] = patched_schedule
    validated_plan = StructuredPlanSchema.model_validate(patched_plan)
    return validated_plan.model_dump()


def _generate_structured_plan_with_tool_call(
    *,
    aggregator: FitnessPromptAggregator,
    llm_adapter: LLMAdapter,
    boundary_conditions: Any,
    weather_assessment: Any,
    diet_recommendation: Any,
    exercise_library: Any,
) -> StructuredPlanToolResultSchema:
    tool_messages = aggregator.build_generation_tool_prompt(
        boundary_conditions=boundary_conditions,
        weather_assessment=weather_assessment,
        diet_recommendation=diet_recommendation,
        exercise_library=exercise_library,
    )
    tool_result = llm_adapter.generate_tool_call(
        messages=tool_messages,
        tools=_build_generation_tool_spec(),
        tool_choice={"type": "function", "function": {"name": "build_structured_plan"}},
    )
    return _normalize_generated_structured_plan(tool_result["arguments"])


def _refine_structured_plan_with_tool_call(
    *,
    aggregator: FitnessPromptAggregator,
    llm_adapter: LLMAdapter,
    boundary_conditions: Any,
    weather_assessment: Any,
    diet_recommendation: Any,
    exercise_library: Any,
    current_structured_plan: dict[str, Any],
    user_feedback: str,
) -> StructuredPlanRefinementToolResultSchema:
    tool_messages = aggregator.build_refinement_tool_prompt(
        boundary_conditions=boundary_conditions,
        weather_assessment=weather_assessment,
        diet_recommendation=diet_recommendation,
        exercise_library=exercise_library,
        current_structured_plan=current_structured_plan,
        user_feedback=user_feedback,
    )
    tool_result = llm_adapter.generate_tool_call(
        messages=tool_messages,
        tools=_build_refinement_tool_spec(),
        tool_choice={"type": "function", "function": {"name": "edit_structured_plan"}},
    )
    return _normalize_refinement_tool_result(tool_result["arguments"])


async def generate_initial_plan(session_id: str, db: Session) -> str:
    collector = BoundaryCollectorService(db)
    aggregator = FitnessPromptAggregator()
    llm_adapter = LLMAdapter()

    boundary_conditions = collector.get_complete_boundary(session_id)
    weather_snapshot = await fetch_weather_snapshot()
    weather_assessment = evaluate_weather_venues(weather_snapshot)
    macro_targets = calculate_macro_targets(
        gender=boundary_conditions.profile.gender,
        height_cm=boundary_conditions.profile.height_cm,
        weight_kg=boundary_conditions.profile.weight_kg,
        goal=boundary_conditions.goal.primary,
    )
    diet_recommendation = generate_diet_plan(
        DietPlanningInput(
            user_location=boundary_conditions.spatiotemporal.dorm_location,
            budget_level=boundary_conditions.dietary.weekly_budget,
            user_macros=macro_targets,
            canteen_items=load_canteen_items(),
        )
    )
    exercise_library = select_exercise_template(goal=boundary_conditions.goal.primary, templates=load_exercise_templates())
    tool_plan_result = _generate_structured_plan_with_tool_call(
        aggregator=aggregator,
        llm_adapter=llm_adapter,
        boundary_conditions=boundary_conditions,
        weather_assessment=weather_assessment,
        diet_recommendation=diet_recommendation,
        exercise_library=exercise_library,
    )
    messages = aggregator.build_generation_prompt(
        boundary_conditions=boundary_conditions,
        weather_assessment=weather_assessment,
        diet_recommendation=diet_recommendation,
        exercise_library=exercise_library,
    )
    final_text = tool_plan_result.plan_text
    structured_plan = tool_plan_result.structured_plan.model_dump()
    plan_id = build_plan_id(session_id)

    existing_record = _get_active_plan_record(db, session_id)
    if existing_record is not None:
        existing_record.plan_id = plan_id
        existing_record.current_plan_text = final_text
        existing_record.structured_plan = structured_plan
        existing_record.message_history = messages + [{"role": "assistant", "content": final_text}]
        existing_record.status = "draft"
        existing_record.is_active = True
        existing_record.change_summary = "初始生成"
    else:
        db.add(
            PlanHistory(
                session_id=session_id,
                plan_id=plan_id,
                current_plan_text=final_text,
                structured_plan=structured_plan,
                message_history=messages + [{"role": "assistant", "content": final_text}],
                status="draft",
                is_active=True,
                change_summary="初始生成",
            )
        )
    db.commit()
    return final_text


async def refine_plan(session_id: str, user_feedback: str, db: Session) -> str:
    collector = BoundaryCollectorService(db)
    aggregator = FitnessPromptAggregator()
    llm_adapter = LLMAdapter()

    boundary_conditions = collector.get_complete_boundary(session_id)
    plan_record = _get_active_plan_record(db, session_id)
    if plan_record is None or not plan_record.message_history:
        raise ValueError(f"session_id `{session_id}` 不存在可用于修正的历史计划。")

    history_messages = list(plan_record.message_history)
    previous_plan = _extract_last_assistant_message(history_messages)
    weather_snapshot = await fetch_weather_snapshot()
    weather_assessment = evaluate_weather_venues(weather_snapshot)
    macro_targets = calculate_macro_targets(
        gender=boundary_conditions.profile.gender,
        height_cm=boundary_conditions.profile.height_cm,
        weight_kg=boundary_conditions.profile.weight_kg,
        goal=boundary_conditions.goal.primary,
    )
    diet_recommendation = generate_diet_plan(
        DietPlanningInput(
            user_location=boundary_conditions.spatiotemporal.dorm_location,
            budget_level=boundary_conditions.dietary.weekly_budget,
            user_macros=macro_targets,
            canteen_items=load_canteen_items(),
        )
    )
    exercise_library = select_exercise_template(goal=boundary_conditions.goal.primary, templates=load_exercise_templates())
    tool_refinement_result = _refine_structured_plan_with_tool_call(
        aggregator=aggregator,
        llm_adapter=llm_adapter,
        boundary_conditions=boundary_conditions,
        weather_assessment=weather_assessment,
        diet_recommendation=diet_recommendation,
        exercise_library=exercise_library,
        current_structured_plan=plan_record.structured_plan or {},
        user_feedback=user_feedback,
    )
    messages = aggregator.build_refinement_prompt(
        boundary_conditions=boundary_conditions,
        weather_assessment=weather_assessment,
        diet_recommendation=diet_recommendation,
        exercise_library=exercise_library,
        previous_plan=previous_plan,
        user_feedback=user_feedback,
    )
    refined_text = tool_refinement_result.refined_plan_text
    updated_structured_plan = _apply_structured_plan_operations(
        plan_record.structured_plan or {},
        tool_refinement_result.operations,
    )
    change_summary = tool_refinement_result.change_summary
    plan_record.current_plan_text = refined_text
    plan_record.structured_plan = updated_structured_plan
    plan_record.message_history = history_messages + [{"role": "user", "content": user_feedback}, {"role": "assistant", "content": refined_text}]
    plan_record.status = "refined"
    plan_record.change_summary = change_summary
    db.commit()
    return refined_text


def accept_plan(session_id: str, db: Session) -> dict[str, str]:
    plan_record = _get_active_plan_record(db, session_id)
    if plan_record is None or not plan_record.message_history:
        raise ValueError(f"session_id `{session_id}` 不存在可确认的历史计划。")
    history_messages = list(plan_record.message_history)
    final_plan_text = _extract_last_assistant_message(history_messages)
    plan_record.current_plan_text = final_plan_text
    plan_record.status = "accepted"
    plan_record.is_active = False
    db.commit()
    return {"final_plan_text": final_plan_text, "status": "accepted"}


def _extract_last_assistant_message(messages: List[dict[str, str]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "assistant":
            return message.get("content", "")
    raise ValueError("历史消息中不存在 assistant 输出。")
