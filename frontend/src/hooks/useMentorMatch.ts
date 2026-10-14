import { useMutation, useQuery } from "@tanstack/react-query";
import { api, CustomApiError } from "../lib/api";
import type { MentorContactRequest, MentorContactResponse, MentorMatchResponse } from "../types";

export function useMentorMatch(roleId: number | null, experiences?: string[], enabled: boolean = true) {
  return useQuery<MentorMatchResponse, CustomApiError>({
    queryKey: ["mentors", roleId, experiences],
    queryFn: () => {
      if (!roleId) throw new Error("roleId obrigatório");
      return api.findMentors(roleId, experiences);
    },
    enabled: enabled && roleId !== null,
    staleTime: 5 * 60 * 1000,
  });
}

export function useRequestMentoring() {
  return useMutation<MentorContactResponse, CustomApiError, { mentorId: string; data: MentorContactRequest }>({
    mutationFn: ({ mentorId, data }) => api.requestMentoring(mentorId, data),
  });
}
