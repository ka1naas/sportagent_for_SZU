from __future__ import annotations

import json
from typing import Any

from backend.app.models.schemas import UserBoundaryConditions
from backend.app.domains.schemas import DietPlanningOutput, ExerciseTemplateOutput, WeatherVenueAnalysisOutput


class FitnessPromptAggregator:
    """将子系统与领域模块结果统一组装为可直接发送给 LLMAdapter 的 messages。"""

    def __init__(self, system_persona: str | None = None) -> None:
        self._system_persona = system_persona or self._default_system_persona()

    def build_generation_prompt(
        self,
        *,
        boundary_conditions: UserBoundaryConditions,
        weather_assessment: WeatherVenueAnalysisOutput,
        diet_recommendation: DietPlanningOutput,
        exercise_library: ExerciseTemplateOutput,
    ) -> list[dict[str, str]]:
        system_prompt = self._system_persona
        user_prompt = self._build_generation_user_prompt(
            boundary_conditions=boundary_conditions,
            weather_assessment=weather_assessment,
            diet_recommendation=diet_recommendation,
            exercise_library=exercise_library,
        )
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def build_refinement_prompt(
        self,
        *,
        boundary_conditions: UserBoundaryConditions,
        weather_assessment: WeatherVenueAnalysisOutput,
        diet_recommendation: DietPlanningOutput,
        exercise_library: ExerciseTemplateOutput,
        previous_plan: str,
        user_feedback: str,
    ) -> list[dict[str, str]]:
        system_prompt = self._system_persona
        base_prompt = self._build_generation_user_prompt(
            boundary_conditions=boundary_conditions,
            weather_assessment=weather_assessment,
            diet_recommendation=diet_recommendation,
            exercise_library=exercise_library,
        )
        refinement_prompt = (
            f"{base_prompt}\n\n"
            "以下是上一版计划，请在其基础上修改，不要推翻全部重写：\n"
            f"{previous_plan}\n\n"
            "以下是用户新的反馈，请逐条吸收并生成修正版：\n"
            f"{user_feedback}"
        )
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": refinement_prompt},
        ]

    def build_generation_tool_prompt(
        self,
        *,
        boundary_conditions: UserBoundaryConditions,
        weather_assessment: WeatherVenueAnalysisOutput,
        diet_recommendation: DietPlanningOutput,
        exercise_library: ExerciseTemplateOutput,
    ) -> list[dict[str, str]]:
        system_prompt = self._system_persona
        user_prompt = (
            f"{self._build_generation_user_prompt(boundary_conditions=boundary_conditions, weather_assessment=weather_assessment, diet_recommendation=diet_recommendation, exercise_library=exercise_library)}\n\n"
            "你必须调用 `build_structured_plan` 工具。"
            "不要输出普通自然语言正文。"
            "请在工具参数中返回完整的 structured_plan 以及一段 plan_text。"
        )
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def build_refinement_tool_prompt(
        self,
        *,
        boundary_conditions: UserBoundaryConditions,
        weather_assessment: WeatherVenueAnalysisOutput,
        diet_recommendation: DietPlanningOutput,
        exercise_library: ExerciseTemplateOutput,
        current_structured_plan: dict[str, Any],
        user_feedback: str,
    ) -> list[dict[str, str]]:
        system_prompt = self._system_persona
        user_prompt = (
            f"{self._build_generation_user_prompt(boundary_conditions=boundary_conditions, weather_assessment=weather_assessment, diet_recommendation=diet_recommendation, exercise_library=exercise_library)}\n\n"
            f"【当前结构化计划】\n{self._to_pretty_json(current_structured_plan)}\n\n"
            f"【用户修改意见】\n{user_feedback}\n\n"
            "你必须调用 `edit_structured_plan` 工具。"
            "不要返回整份新计划 JSON。"
            "请只返回最小必要修改操作 operations、change_summary 和 refined_plan_text。"
        )
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def build_assistant_router_prompt(
        self,
        *,
        boundary_conditions: UserBoundaryConditions,
        current_plan: dict[str, Any] | None,
        user_message: str,
        is_initial_planning_turn: bool,
        has_active_plan: bool,
    ) -> list[dict[str, str]]:
        system_prompt = self._system_persona
        user_prompt = (
            "你是校园健身助手的主对话调度器。"
            "你必须根据用户背景、当前计划状态和用户最新一句话，选择最合适的工具。\n\n"
            f"【用户五步背景】\n{self._to_pretty_json(boundary_conditions.model_dump())}\n\n"
            f"【当前是否已有训练计划】\n{json.dumps({'has_active_plan': has_active_plan}, ensure_ascii=False, indent=2)}\n\n"
            f"【当前训练计划（如有）】\n{self._to_pretty_json(current_plan or {})}\n\n"
            f"【是否是五步完成后的首次主回答】\n{json.dumps({'is_initial_planning_turn': is_initial_planning_turn}, ensure_ascii=False, indent=2)}\n\n"
            f"【用户最新消息】\n{user_message}\n\n"
            "决策规则：\n"
            "1. 如果 is_initial_planning_turn=true 且当前没有 active plan，优先选择 generate_training_plan；\n"
            "2. 如果用户明显在表达对已有计划的不满或修改要求，选择 refine_training_plan；\n"
            "3. 如果用户在问现在能不能训练、适不适合去某个场地，选择 check_training_weather；\n"
            "4. 其他训练、饮食、恢复类问题，选择 answer_general_question。"
        )
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def build_general_answer_prompt(
        self,
        *,
        boundary_conditions: UserBoundaryConditions,
        current_plan: dict[str, Any] | None,
        user_message: str,
    ) -> list[dict[str, str]]:
        system_prompt = self._system_persona
        user_prompt = (
            f"【用户五步背景】\n{self._to_pretty_json(boundary_conditions.model_dump())}\n\n"
            f"【当前训练计划（如有）】\n{self._to_pretty_json(current_plan or {})}\n\n"
            f"【用户问题】\n{user_message}\n\n"
            "请直接回答用户问题。回答要结合用户背景与已有计划，不要脱离上下文空谈。"
        )
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    @staticmethod
    def _default_system_persona() -> str:
        return (
            "你是深大本地化专属健身教练、天气风险观察员和穷鬼营养师。"
            "你必须严格依据提供的结构化上下文生成计划，不得虚构不存在的食堂、天气、场地和训练资源。"
            "输出要专业、接地气、可执行，优先降低决策成本、预算压力和天气风险。"
        )

    def _build_generation_user_prompt(
        self,
        *,
        boundary_conditions: UserBoundaryConditions,
        weather_assessment: WeatherVenueAnalysisOutput,
        diet_recommendation: DietPlanningOutput,
        exercise_library: ExerciseTemplateOutput,
    ) -> str:
        return (
            "请根据以下结构化数据，生成一份深大本地化训练与饮食计划。\n\n"
            f"【用户边界条件】\n{self._to_pretty_json(boundary_conditions.model_dump())}\n\n"
            f"【天气与场地评估】\n{self._to_pretty_json(weather_assessment.model_dump())}\n\n"
            f"【饮食推荐】\n{self._to_pretty_json(diet_recommendation.model_dump())}\n\n"
            f"【训练动作库】\n{self._to_pretty_json(exercise_library.model_dump())}\n\n"
            "输出要求：\n"
            "1. 给出训练安排、饮食建议、天气替代方案和执行注意事项；\n"
            "2. 饮食建议必须优先使用候选食堂与菜品池；\n"
            "3. 场地选择必须参考天气与湿滑风险评估；\n"
            "4. 训练建议必须参考动作库模板，不能脱离提供的训练知识乱写；\n"
            "5. 语言要像真正懂深大校园生活的教练，不要官话。"
        )

    @staticmethod
    def _to_pretty_json(payload: dict[str, Any]) -> str:
        return json.dumps(payload, ensure_ascii=False, indent=2)
