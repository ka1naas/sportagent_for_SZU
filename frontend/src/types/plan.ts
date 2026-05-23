export type WeeklyScheduleItem = {
  item_id: string;
  day: string;
  time_period: string;
  location: string;
  location_type: string;
  training_type: string;
  title: string;
  items: string[];
  fallback?: string | null;
  notes?: string | null;
};

export type StructuredPlan = {
  plan_summary: string;
  weekly_schedule: WeeklyScheduleItem[];
  diet_plan: Record<string, unknown>;
  warnings: string[];
};

export type PlanGenerateResponse = {
  session_id: string;
  plan_id: string;
  plan_text: string;
  prompt_context: Record<string, unknown>;
  structured_plan: StructuredPlan;
};

export type PlanRefinePayload = {
  session_id: string;
  plan_id: string;
  user_feedback: string;
};

export type PlanRefineResponse = {
  session_id: string;
  plan_id: string;
  refined_plan_text: string;
  feedback_applied: string;
  structured_plan: StructuredPlan;
  change_summary: string;
};
