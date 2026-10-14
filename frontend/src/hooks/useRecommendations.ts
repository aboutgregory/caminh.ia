import { useMutation } from "@tanstack/react-query";
import { api, CustomApiError } from "../lib/api";
import type { RecommendationRequest, RecommendationResponse } from "../types";

export function useRecommendations() {
  return useMutation<RecommendationResponse, CustomApiError, RecommendationRequest>({
    mutationFn: (data: RecommendationRequest) => api.getRecommendations(data),
  });
}
