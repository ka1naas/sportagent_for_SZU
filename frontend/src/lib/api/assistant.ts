import { apiRequest } from "@/lib/api/client";
import type { AssistantChatRequest, AssistantChatResponse } from "@/types/assistant";

export function sendAssistantMessage(payload: AssistantChatRequest) {
  return apiRequest<AssistantChatResponse>("/chat/assistant", {
    method: "POST",
    body: payload,
  });
}
