import type { StructuredPlan } from "@/types/plan";
import type { WeatherSnapshot, VenueStatus } from "@/types/weather";

export type AssistantRouteKind = "generate_plan" | "refine_plan" | "weather_check" | "general_answer";

export type AssistantChatRequest = {
  session_id: string;
  message: string;
  plan_id?: string | null;
  is_initial_planning_turn?: boolean;
};

export type AssistantChatResponse = {
  session_id: string;
  route_kind: AssistantRouteKind;
  assistant_message: string;
  plan_id?: string | null;
  structured_plan?: StructuredPlan | null;
  change_summary?: string | null;
  weather_snapshot?: WeatherSnapshot | null;
  venue_statuses: VenueStatus[];
};
