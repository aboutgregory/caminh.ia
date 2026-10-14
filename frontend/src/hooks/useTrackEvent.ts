import { useCallback } from "react";
import { api } from "../lib/api";
import type { ClientEventPayload } from "../types";

export function useTrackEvent() {
  const track = useCallback((event: ClientEventPayload) => {
    api.trackEvent(event);
  }, []);

  return { track };
}
