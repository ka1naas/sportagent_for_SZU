import { apiRequest } from "@/lib/api/client";
import type {
  ChatStepResponse,
  DietStepPayload,
  GoalStepPayload,
  HabitStepPayload,
  ProfileStepPayload,
  SpaceTimeStepPayload,
} from "@/types/chat";

export function submitProfileStep(payload: ProfileStepPayload) {
  return apiRequest<ChatStepResponse>("/chat/step1_profile", {
    method: "POST",
    body: payload,
  });
}

export function submitGoalStep(payload: GoalStepPayload) {
  return apiRequest<ChatStepResponse>("/chat/step2_goal", {
    method: "POST",
    body: payload,
  });
}

export function submitSpaceTimeStep(payload: SpaceTimeStepPayload) {
  return apiRequest<ChatStepResponse>("/chat/step3_space_time", {
    method: "POST",
    body: payload,
  });
}

export function submitDietStep(payload: DietStepPayload) {
  return apiRequest<ChatStepResponse>("/chat/step4_diet", {
    method: "POST",
    body: payload,
  });
}

export function submitHabitStep(payload: HabitStepPayload) {
  return apiRequest<ChatStepResponse>("/chat/step5_habits", {
    method: "POST",
    body: payload,
  });
}
