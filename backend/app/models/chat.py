from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class StepName(str, Enum):
    step1_profile = "step1_profile"
    step2_goal = "step2_goal"
    step3_space_time = "step3_space_time"
    step4_diet = "step4_diet"
    step5_habits = "step5_habits"
    completed = "completed"


class GenderOption(str, Enum):
    male = "男"
    female = "女"
    third_gender = "第三性别"


class GoalOption(str, Enum):
    fat_loss = "减脂"
    muscle_gain = "增肌"
    strength = "力量"
    power = "爆发力"
    endurance = "耐力"


class AcceptanceOption(str, Enum):
    accept = "接受"
    reject = "不接受"


class WeeklyFrequencyOption(str, Enum):
    one_to_two = "1-2次"
    three_to_four = "3-4次"
    over_five = "5次以上"


class DurationOption(str, Enum):
    under_thirty = "30分钟内"
    forty_five_to_sixty = "45-60分钟"
    over_sixty = "1小时以上"


class PreferenceOption(str, Enum):
    before_class = "上课前"
    after_class = "下课后"
    no_preference = "无所谓"


class BudgetLevel(str, Enum):
    budget_low = "极限穷鬼<300元"
    budget_mid = "普通学生300-500元"
    budget_high = "宽裕>500元"


class FavoriteSportOption(str, Enum):
    basketball = "篮球"
    cycling = "骑行"
    running = "跑步"
    badminton = "羽毛球"
    fitness = "健身"
    not_active = "不爱运动"
    other = "其他"


class ProfileStepRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=64)
    gender: GenderOption
    height_cm: float = Field(..., gt=0, le=300)
    weight_kg: float = Field(..., gt=0, le=500)


class GoalStepRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=64)
    goal: GoalOption
    accept_muscle_loss: Optional[AcceptanceOption] = None


class SpaceTimeStepRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=64)
    frequency: WeeklyFrequencyOption
    duration: DurationOption
    preference: PreferenceOption
    dorm_location: str = Field(..., min_length=1, max_length=64)
    schedule_image_url: Optional[str] = Field(default=None, max_length=255)


class DietStepRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=64)
    preferred_canteens: list[str] = Field(..., min_length=1, max_length=8)
    weekly_budget: BudgetLevel


class HabitStepRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=64)
    favorite_sport: FavoriteSportOption
    favorite_sport_other: Optional[str] = Field(default=None, max_length=64)
    integrate_into_training: bool


class GoalStepResult(BaseModel):
    science_tip: str
    follow_up_question: Optional[str] = None


class ChatSessionRecord(BaseModel):
    session_id: str
    current_step: StepName
    payload: dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


class ChatStepResponse(BaseModel):
    session_id: str
    current_step: StepName
    next_step: StepName
    message: str
    data: dict[str, Any]


class AssistantRouteKind(str, Enum):
    generate_plan = "generate_plan"
    refine_plan = "refine_plan"
    weather_check = "weather_check"
    general_answer = "general_answer"


class AssistantToolName(str, Enum):
    generate_training_plan = "generate_training_plan"
    refine_training_plan = "refine_training_plan"
    check_training_weather = "check_training_weather"
    answer_general_question = "answer_general_question"


class AssistantChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=64)
    message: str = Field(..., min_length=1, max_length=2000)
    plan_id: Optional[str] = Field(default=None, min_length=1, max_length=128)
    is_initial_planning_turn: bool = False


class AssistantChatResponse(BaseModel):
    session_id: str
    route_kind: AssistantRouteKind
    assistant_message: str
    plan_id: Optional[str] = None
    structured_plan: Optional[dict[str, Any]] = None
    change_summary: Optional[str] = None
    weather_snapshot: Optional[dict[str, Any]] = None
    venue_statuses: list[dict[str, Any]] = Field(default_factory=list)
