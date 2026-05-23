const SESSION_STORAGE_KEY = "sportagent.session_id";
const SCHEDULE_STORAGE_KEY = "sportagent.demo_schedule";

export function readStoredSessionId() {
  if (typeof window === "undefined") {
    return null;
  }

  return window.localStorage.getItem(SESSION_STORAGE_KEY);
}

export function persistSessionId(sessionId: string) {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(SESSION_STORAGE_KEY, sessionId);
}

export function readDemoScheduleFlag() {
  if (typeof window === "undefined") {
    return true;
  }

  return window.localStorage.getItem(SCHEDULE_STORAGE_KEY) !== "false";
}

export function persistDemoScheduleFlag(enabled: boolean) {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(SCHEDULE_STORAGE_KEY, String(enabled));
}
