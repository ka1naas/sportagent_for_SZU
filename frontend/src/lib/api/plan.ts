import { apiRequest } from "@/lib/api/client";
import type { PlanGenerateResponse, PlanRefinePayload, PlanRefineResponse } from "@/types/plan";

export function generatePlan(session_id: string) {
  return apiRequest<PlanGenerateResponse>("/plan/generate", {
    method: "POST",
    body: { session_id },
  });
}

export function refinePlan(payload: PlanRefinePayload) {
  return apiRequest<PlanRefineResponse>("/plan/refine", {
    method: "POST",
    body: payload,
  });
}
