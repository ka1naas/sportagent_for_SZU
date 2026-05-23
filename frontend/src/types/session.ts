export type SessionState = {
  sessionId: string;
  hasDemoSchedule: boolean;
};

export type AssistantRouteKind = "generate_plan" | "refine_plan" | "weather_check" | "general_answer";
