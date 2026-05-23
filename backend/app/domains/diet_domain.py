from __future__ import annotations

import json
from pathlib import Path

from backend.app.domains.schemas import CandidateDish, CanteenItem, DietPlanningInput, DietPlanningOutput, MacroTargets, NutritionAdvice


CANTEEN_DATA_PATH = Path("backend/data/canteens.json")

LOCATION_TO_CANTEENS = {
    "西南区": ["粤海校区荔园食堂", "汇元楼美食广场", "沧海校区学生餐厅"],
    "粤海街道": ["粤海校区荔园食堂", "汇元楼美食广场", "沧海校区学生餐厅"],
    "丽湖宿舍": ["沧海校区学生餐厅", "汇元楼美食广场", "粤海校区荔园食堂"],
    "沧海校区": ["沧海校区学生餐厅", "汇元楼美食广场", "粤海校区荔园食堂"],
}

MAX_MEAL_BUDGET_BY_LEVEL = {
    "极限穷鬼<300元": 18,
    "普通学生300-500元": 26,
    "宽裕>500元": 40,
}

GOAL_CONFIG = {
    "减脂": {"calorie_multiplier": 0.85, "protein_per_kg": 1.9, "fat_ratio": 0.25, "note": "控制总热量赤字，优先保住蛋白质摄入，减少掉肌肉风险。"},
    "增肌": {"calorie_multiplier": 1.12, "protein_per_kg": 2.0, "fat_ratio": 0.25, "note": "轻盈热量盈余配合高蛋白，更适合学生党稳定增肌。"},
    "肌肥大": {"calorie_multiplier": 1.1, "protein_per_kg": 2.0, "fat_ratio": 0.25, "note": "围绕恢复和肌肉合成分配热量，优先保证蛋白和训练后碳水。"},
    "练力量": {"calorie_multiplier": 1.02, "protein_per_kg": 1.8, "fat_ratio": 0.28, "note": "维持或略微盈余热量，兼顾力量输出与神经恢复。"},
    "练爆发力/弹跳": {"calorie_multiplier": 1.05, "protein_per_kg": 1.8, "fat_ratio": 0.24, "note": "保持适度碳水储备，提高爆发动作质量和课后恢复速度。"},
    "有氧耐力/马拉松": {"calorie_multiplier": 1.08, "protein_per_kg": 1.7, "fat_ratio": 0.22, "note": "提升碳水供能占比，优先满足耐力训练的糖原补给。"},
}


def load_canteen_items(data_path: Path = CANTEEN_DATA_PATH) -> list[CanteenItem]:
    raw_items = json.loads(data_path.read_text(encoding="utf-8"))
    return [CanteenItem(**item) for item in raw_items]


def calculate_macro_targets(*, gender: str, height_cm: float, weight_kg: float, goal: str) -> MacroTargets:
    bmr = _calculate_bmr(gender=gender, height_cm=height_cm, weight_kg=weight_kg)
    maintenance_calories = bmr * 1.55
    config = GOAL_CONFIG.get(goal, GOAL_CONFIG["练力量"])
    target_calories = round(maintenance_calories * config["calorie_multiplier"], 1)
    target_protein_g = round(weight_kg * config["protein_per_kg"], 1)
    target_fat_g = round((target_calories * config["fat_ratio"]) / 9, 1)
    protein_calories = target_protein_g * 4
    fat_calories = target_fat_g * 9
    target_carbs_g = round(max((target_calories - protein_calories - fat_calories) / 4, 0), 1)
    return MacroTargets(
        estimated_bmr=round(bmr, 1),
        estimated_tdee=round(maintenance_calories, 1),
        target_calories=target_calories,
        target_protein_g=target_protein_g,
        target_carbs_g=target_carbs_g,
        target_fat_g=target_fat_g,
        strategy_note=config["note"],
    )


def generate_diet_plan(input_data: DietPlanningInput) -> DietPlanningOutput:
    nearby_canteens = _resolve_nearby_canteens(input_data.user_location)
    filtered_items = [
        item for item in input_data.canteen_items if item.name in nearby_canteens and item.price <= _resolve_budget_limit(input_data.budget_level)
    ]
    filtered_items.sort(key=lambda item: (_protein_gap_score(item, input_data.user_macros), item.price))
    shortlist = filtered_items[:3]
    total_protein = sum(item.protein_estimate_g for item in shortlist)
    total_price = sum(item.price for item in shortlist)
    return DietPlanningOutput(
        recommended_nearby_canteens=nearby_canteens[:3],
        candidate_dishes=[
            CandidateDish(
                canteen_name=item.name,
                stall=item.stall,
                price=item.price,
                protein_estimate_g=item.protein_estimate_g,
                tags=item.tags,
                description=item.description,
            )
            for item in shortlist
        ],
        nutrition_advice=NutritionAdvice(
            target_protein_g=input_data.user_macros.target_protein_g,
            estimated_selected_protein_g=total_protein,
            estimated_selected_cost=total_price,
            advice=_build_advice(
                protein_target=input_data.user_macros.target_protein_g,
                selected_protein=total_protein,
                budget_level=input_data.budget_level,
            ),
        ),
    )


def _calculate_bmr(*, gender: str, height_cm: float, weight_kg: float) -> float:
    normalized_gender = gender.strip()
    if normalized_gender == "男":
        return 10 * weight_kg + 6.25 * height_cm - 5 * 22 + 5
    if normalized_gender == "女":
        return 10 * weight_kg + 6.25 * height_cm - 5 * 22 - 161
    return 10 * weight_kg + 6.25 * height_cm - 5 * 22 - 78


def _resolve_nearby_canteens(user_location: str) -> list[str]:
    for keyword, canteens in LOCATION_TO_CANTEENS.items():
        if keyword in user_location:
            return canteens
    return ["粤海校区荔园食堂", "汇元楼美食广场", "沧海校区学生餐厅"]


def _resolve_budget_limit(budget_level: str) -> int:
    return MAX_MEAL_BUDGET_BY_LEVEL.get(budget_level, 26)


def _protein_gap_score(item: CanteenItem, macros: MacroTargets) -> float:
    protein_target = macros.target_protein_g / 3
    return abs(float(item.protein_estimate_g) - protein_target)


def _build_advice(*, protein_target: float, selected_protein: float, budget_level: str) -> str:
    if selected_protein >= protein_target * 0.8:
        return "当前候选菜品的蛋白覆盖度较高，适合作为训练日主力进餐。"
    if "极限穷鬼" in budget_level:
        return "预算较紧，建议优先选择高蛋白档口，再用鸡蛋或豆腐补足缺口。"
    return "当前候选组合能覆盖部分蛋白目标，剩余部分可通过加餐奶制品或蛋类补齐。"
