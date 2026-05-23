from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from backend.app.models.chat import StepName


class UserProfileSchema(BaseModel):
    gender: str = Field(..., description="用户性别，允许第三性别")
    height_cm: float = Field(..., gt=0, le=300, description="身高，单位厘米")
    weight_kg: float = Field(..., gt=0, le=500, description="体重，单位千克")
    tdee: Optional[float] = Field(default=None, gt=0, description="估算的每日总消耗热量，可选")


class UserGoalSchema(BaseModel):
    primary: str = Field(..., description="主要训练目标")
    accept_muscle_loss: Optional[bool] = Field(default=None, description="减脂场景下是否接受部分掉肌肉")


class UserSpatiotemporalSchema(BaseModel):
    frequency: str
    duration: str
    preference: str
    dorm_location: str
    schedule_image_url: Optional[str] = None


class UserDietarySchema(BaseModel):
    preferred_canteens: List[str]
    weekly_budget: str


class UserHabitsSchema(BaseModel):
    favorite_sport: str
    integrate_into_training: bool


class UserBoundaryConditions(BaseModel):
    session_id: str
    profile: UserProfileSchema
    goal: UserGoalSchema
    spatiotemporal: UserSpatiotemporalSchema
    dietary: UserDietarySchema
    habits: UserHabitsSchema


class BoundaryConditionsResponse(BaseModel):
    session_id: str
    current_step: StepName
    boundary_conditions: UserBoundaryConditions
    markdown_document: str


class PlanGenerateRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=64)


class PlanGenerateResponse(BaseModel):
    session_id: str
    plan_id: str
    plan_text: str
    prompt_context: Dict[str, Any]
    structured_plan: Dict[str, Any]


class PlanFeedbackRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=64)
    plan_id: str = Field(..., min_length=1, max_length=64)
    user_feedback: str = Field(..., min_length=1, max_length=2000)


class PlanRefineResponse(BaseModel):
    session_id: str
    plan_id: str
    refined_plan_text: str
    feedback_applied: str
    structured_plan: Dict[str, Any]
    change_summary: str


class PlanScheduleItemSchema(BaseModel):
    item_id: str
    day: str
    time_period: str
    location: str
    location_type: str
    training_type: str
    title: str
    items: List[str] = Field(default_factory=list)
    fallback: Optional[str] = None
    notes: Optional[str] = None


class PlanEditTargetSchema(BaseModel):
    item_id: Optional[str] = None
    day: Optional[str] = None
    time_period: Optional[str] = None
    location: Optional[str] = None


class PlanScheduleItemInputSchema(BaseModel):
    day: str
    time_period: str
    location: str
    location_type: str
    training_type: str
    title: str
    items: List[str] = Field(default_factory=list)
    fallback: Optional[str] = None
    notes: Optional[str] = None


class PlanEditOperationSchema(BaseModel):
    action: str = Field(..., description="允许值：delete_item、add_item、move_item、replace_location、replace_notes")
    target: Optional[PlanEditTargetSchema] = None
    new_item: Optional[PlanScheduleItemInputSchema] = None
    new_day: Optional[str] = None
    new_time_period: Optional[str] = None
    new_location: Optional[str] = None
    new_notes: Optional[str] = None
    reason: Optional[str] = None


class StructuredPlanSchema(BaseModel):
    plan_summary: str
    weekly_schedule: List[PlanScheduleItemSchema] = Field(default_factory=list)
    diet_plan: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)


class StructuredPlanToolResultSchema(BaseModel):
    structured_plan: StructuredPlanSchema
    plan_text: str = Field(..., min_length=1)


class StructuredPlanRefinementToolResultSchema(BaseModel):
    operations: List[PlanEditOperationSchema] = Field(default_factory=list)
    change_summary: str = Field(..., min_length=1)
    refined_plan_text: str = Field(..., min_length=1)


class PlanAcceptRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=64)
    plan_id: str = Field(..., min_length=1, max_length=64)


class PlanAcceptResponse(BaseModel):
    session_id: str
    plan_id: str
    final_plan_text: str
    status: str


class WeatherSnapshotSchema(BaseModel):
    precipitation_mm: float = Field(..., ge=0, description="最近观测窗口的降水量，单位毫米")
    temperature_c: float = Field(..., description="当前气温，单位摄氏度")
    is_raining: bool = Field(..., description="当前是否仍在降雨")


class VenueStatusSchema(BaseModel):
    venue_name: str = Field(..., description="场地名称")
    surface_type: str = Field(..., description="场地材质类型")
    wetness_level_pct: int = Field(..., ge=0, le=100, description="湿润度百分比")
    suitability_score: int = Field(..., ge=0, le=100, description="运动适宜度综合得分")
    can_exercise: bool = Field(..., description="是否建议进行运动")
    notice: str = Field(..., description="现场风险提示与建议")


class VenueWeatherStatusResponse(BaseModel):
    location: str = Field(..., description="天气分析地点")
    weather_snapshot: WeatherSnapshotSchema
    venue_statuses: List[VenueStatusSchema]


class UserScheduleItemSchema(BaseModel):
    weekday: str = Field(..., min_length=1, max_length=16)
    time_start: str = Field(..., min_length=1, max_length=16)
    time_end: str = Field(..., min_length=1, max_length=16)
    location: str = Field(..., min_length=1, max_length=128)


class UserProfilePersistRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=64)
    gender: str = Field(..., min_length=1, max_length=32)
    height_cm: float = Field(..., gt=0, le=300)
    weight_kg: float = Field(..., gt=0, le=500)
    goal: str = Field(..., min_length=1, max_length=64)
    budget_level: str = Field(..., min_length=1, max_length=64)
    raw_answers: Dict[str, Any] = Field(..., description="前端提交的原始五问答案")
    schedules: List[UserScheduleItemSchema] = Field(default_factory=list)


class UserMacrosResponseSchema(BaseModel):
    estimated_bmr: float
    estimated_tdee: float
    target_calories: float
    target_protein_g: float
    target_carbs_g: float
    target_fat_g: float
    strategy_note: str


class DietCandidateDishSchema(BaseModel):
    canteen_name: str
    stall: str
    price: int
    protein_estimate_g: int
    tags: List[str]
    description: str


class DietAdviceSchema(BaseModel):
    target_protein_g: float
    estimated_selected_protein_g: int
    estimated_selected_cost: int
    advice: str


class DietContextResponseSchema(BaseModel):
    recommended_nearby_canteens: List[str]
    candidate_dishes: List[DietCandidateDishSchema]
    nutrition_advice: DietAdviceSchema


class UserProfilePersistResponse(BaseModel):
    user_id: int
    session_id: str
    saved_schedule_count: int
    macros: UserMacrosResponseSchema
    diet_context: DietContextResponseSchema
