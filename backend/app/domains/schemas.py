from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, Field


class WeatherSnapshot(BaseModel):
    location: str
    precipitation_mm: float = Field(..., ge=0)
    temperature_c: float
    humidity_pct: int = Field(..., ge=0, le=100)
    is_raining: bool
    source: str
    observation_window_hours: int = Field(..., ge=1)
    fallback_reason: Optional[str] = None


class VenueStatus(BaseModel):
    venue_name: str
    surface_type: str
    wetness_level_pct: int = Field(..., ge=0, le=100)
    suitability_score: int = Field(..., ge=0, le=100)
    can_exercise: bool
    notice: str


class WeatherVenueAnalysisOutput(BaseModel):
    weather_snapshot: WeatherSnapshot
    venue_statuses: List[VenueStatus]


class MacroTargets(BaseModel):
    estimated_bmr: float
    estimated_tdee: float
    target_calories: float
    target_protein_g: float
    target_carbs_g: float
    target_fat_g: float
    strategy_note: str


class CanteenItem(BaseModel):
    name: str
    stall: str
    price: int
    tags: List[str] = Field(default_factory=list)
    protein_estimate_g: int
    description: str = ""


class DietPlanningInput(BaseModel):
    user_location: str
    budget_level: str
    user_macros: MacroTargets
    canteen_items: List[CanteenItem]


class CandidateDish(BaseModel):
    canteen_name: str
    stall: str
    price: int
    protein_estimate_g: int
    tags: List[str]
    description: str


class NutritionAdvice(BaseModel):
    target_protein_g: float
    estimated_selected_protein_g: int
    estimated_selected_cost: int
    advice: str


class DietPlanningOutput(BaseModel):
    recommended_nearby_canteens: List[str]
    candidate_dishes: List[CandidateDish]
    nutrition_advice: NutritionAdvice


class ExerciseTemplateOutput(BaseModel):
    goal: str
    template_name: str
    template_data: dict[str, Any]
