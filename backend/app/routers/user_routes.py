from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.domains.diet_domain import DietPlanningInput, calculate_macro_targets, generate_diet_plan, load_canteen_items
from backend.app.models.schemas import UserProfilePersistRequest, UserProfilePersistResponse
from db.database import get_db
from db.models import User, UserMacros, UserSchedule


router = APIRouter()


@router.post("/save_profile", response_model=UserProfilePersistResponse, summary="持久化用户画像并生成饮食候选")
def save_user_profile(payload: UserProfilePersistRequest, db: Session = Depends(get_db)) -> UserProfilePersistResponse:
    user = db.query(User).filter(User.session_id == payload.session_id).one_or_none()
    if user is None:
        user = User(
            session_id=payload.session_id,
            gender=payload.gender,
            height_cm=payload.height_cm,
            weight_kg=payload.weight_kg,
            goal=payload.goal,
            raw_answers=payload.raw_answers,
        )
        db.add(user)
        db.flush()
    else:
        user.gender = payload.gender
        user.height_cm = payload.height_cm
        user.weight_kg = payload.weight_kg
        user.goal = payload.goal
        user.raw_answers = payload.raw_answers
        user.schedules.clear()

    for schedule in payload.schedules:
        user.schedules.append(
            UserSchedule(
                weekday=schedule.weekday,
                time_start=schedule.time_start,
                time_end=schedule.time_end,
                location=schedule.location,
            )
        )

    macros_result = calculate_macro_targets(
        gender=payload.gender,
        height_cm=payload.height_cm,
        weight_kg=payload.weight_kg,
        goal=payload.goal,
    ).model_dump()

    if user.macros is None:
        user.macros = UserMacros(
            target_protein_g=macros_result["target_protein_g"],
            target_carbs_g=macros_result["target_carbs_g"],
            target_fat_g=macros_result["target_fat_g"],
            target_calories=macros_result["target_calories"],
            strategy_note=macros_result["strategy_note"],
        )
    else:
        user.macros.target_protein_g = macros_result["target_protein_g"]
        user.macros.target_carbs_g = macros_result["target_carbs_g"]
        user.macros.target_fat_g = macros_result["target_fat_g"]
        user.macros.target_calories = macros_result["target_calories"]
        user.macros.strategy_note = macros_result["strategy_note"]

    latest_location = payload.schedules[0].location if payload.schedules else payload.raw_answers.get("dorm_location", "西南区")
    macro_targets = calculate_macro_targets(
        gender=payload.gender,
        height_cm=payload.height_cm,
        weight_kg=payload.weight_kg,
        goal=payload.goal,
    )

    diet_context = generate_diet_plan(
        DietPlanningInput(
            user_location=latest_location,
            user_macros=macro_targets,
            budget_level=payload.budget_level,
            canteen_items=load_canteen_items(),
        )
    ).model_dump()

    db.commit()
    db.refresh(user)

    return UserProfilePersistResponse(
        user_id=user.id,
        session_id=user.session_id,
        saved_schedule_count=len(user.schedules),
        macros=macros_result,
        diet_context=diet_context,
    )
