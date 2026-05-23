"use client";

import { create } from "zustand";

import type {
  DietStepPayload,
  GoalStepPayload,
  HabitStepPayload,
  ProfileStepPayload,
  SpaceTimeStepPayload,
  StepName,
} from "@/types/chat";
import type { StructuredPlan } from "@/types/plan";
import type { AssistantRouteKind } from "@/types/session";
import type { VenueWeatherStatusResponse } from "@/types/weather";

type PlannerAnswers = {
  profile?: Omit<ProfileStepPayload, "session_id">;
  goal?: Omit<GoalStepPayload, "session_id">;
  spaceTime?: Omit<SpaceTimeStepPayload, "session_id">;
  diet?: Omit<DietStepPayload, "session_id">;
  habits?: Omit<HabitStepPayload, "session_id">;
};

type PlannerStore = {
  sessionId: string;
  currentStep: StepName;
  hasDemoSchedule: boolean;
  planId: string | null;
  planText: string | null;
  structuredPlan: StructuredPlan | null;
  changeSummary: string | null;
  latestAssistantMessage: string | null;
  latestRouteKind: AssistantRouteKind | null;
  latestWeatherStatus: VenueWeatherStatusResponse | null;
  answers: PlannerAnswers;
  setSessionId: (sessionId: string) => void;
  setCurrentStep: (step: StepName) => void;
  setHasDemoSchedule: (value: boolean) => void;
  resetPlanOutputs: () => void;
  setPlanResult: (payload: { planId: string; planText: string; structuredPlan: StructuredPlan }) => void;
  setRefineResult: (payload: { structuredPlan: StructuredPlan; changeSummary: string; assistantMessage: string }) => void;
  setLatestWeatherStatus: (status: VenueWeatherStatusResponse, message: string) => void;
  setLatestRouteKind: (kind: AssistantRouteKind) => void;
  setLatestAssistantMessage: (message: string, kind: AssistantRouteKind) => void;
  updateAnswers: (answers: Partial<PlannerAnswers>) => void;
};

export const usePlannerStore = create<PlannerStore>((set) => ({
  sessionId: "",
  currentStep: "step1_profile",
  hasDemoSchedule: true,
  planId: null,
  planText: null,
  structuredPlan: null,
  changeSummary: null,
  latestAssistantMessage: null,
  latestRouteKind: null,
  latestWeatherStatus: null,
  answers: {},
  setSessionId: (sessionId) => set({ sessionId }),
  setCurrentStep: (currentStep) => set({ currentStep }),
  setHasDemoSchedule: (hasDemoSchedule) => set({ hasDemoSchedule }),
  resetPlanOutputs: () =>
    set({
      planId: null,
      planText: null,
      structuredPlan: null,
      changeSummary: null,
      latestAssistantMessage: null,
      latestRouteKind: null,
      latestWeatherStatus: null,
    }),
  setPlanResult: ({ planId, planText, structuredPlan }) =>
    set({
      planId,
      planText,
      structuredPlan,
      latestAssistantMessage: planText,
      latestRouteKind: "generate_plan",
    }),
  setRefineResult: ({ structuredPlan, changeSummary, assistantMessage }) =>
    set({
      structuredPlan,
      changeSummary,
      latestAssistantMessage: assistantMessage,
      latestRouteKind: "refine_plan",
    }),
  setLatestWeatherStatus: (latestWeatherStatus, message) =>
    set({
      latestWeatherStatus,
      latestAssistantMessage: message,
      latestRouteKind: "weather_check",
    }),
  setLatestRouteKind: (latestRouteKind) => set({ latestRouteKind }),
  setLatestAssistantMessage: (latestAssistantMessage, latestRouteKind) =>
    set({
      latestAssistantMessage,
      latestRouteKind,
    }),
  updateAnswers: (answers) => set((state) => ({ answers: { ...state.answers, ...answers } })),
}));

export function createGuestSessionId() {
  return `guest_${crypto.randomUUID()}`;
}
