import { getAuthToken } from "./supabase";
import type {
  ApiError,
  ClientEventPayload,
  MentorContactRequest,
  MentorContactResponse,
  MentorMatchResponse,
  RecommendationRequest,
  RecommendationResponse,
  UserDataExport,
} from "../types";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function getSessionId(): string {
  const STORAGE_KEY = "caminhia_session_id";
  let sessionId = sessionStorage.getItem(STORAGE_KEY);
  if (!sessionId) {
    sessionId = crypto.randomUUID();
    sessionStorage.setItem(STORAGE_KEY, sessionId);
  }
  return sessionId;
}

export class CustomApiError extends Error {
  correlationId?: string;
  detalhes?: Array<{ campo: string; motivo: string }>;
  status: number;
  retryAfter?: number;

  constructor(status: number, message: string, correlationId?: string, detalhes?: Array<{ campo: string; motivo: string }>, retryAfter?: number) {
    super(message);
    this.name = "CustomApiError";
    this.status = status;
    this.correlationId = correlationId;
    this.detalhes = detalhes;
    this.retryAfter = retryAfter;
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const headers = new Headers(options.headers || {});

  headers.set("Content-Type", "application/json");
  headers.set("X-Session-ID", getSessionId());

  const token = await getAuthToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(url, { ...options, headers });

  if (response.status === 204) {
    return {} as T;
  }

  const contentType = response.headers.get("content-type");
  const isJson = contentType && contentType.includes("application/json");

  if (!response.ok) {
    let errorMessage = "Ocorreu um erro ao processar sua solicitação.";
    let correlationId: string | undefined;
    let detalhes: Array<{ campo: string; motivo: string }> | undefined;
    let retryAfter: number | undefined;

    if (response.status === 429) {
      const headerVal = response.headers.get("Retry-After");
      if (headerVal) retryAfter = parseInt(headerVal, 10);
    }

    if (isJson) {
      try {
        const errorData: ApiError = await response.json();
        errorMessage = errorData.error || errorMessage;
        correlationId = errorData.correlation_id;
        detalhes = errorData.detalhes;
      } catch {
        // fallback
      }
    } else {
      const text = await response.text();
      if (text) errorMessage = text;
    }

    throw new CustomApiError(response.status, errorMessage, correlationId, detalhes, retryAfter);
  }

  if (isJson) {
    return response.json() as Promise<T>;
  }

  return response.blob() as unknown as Promise<T>;
}

export const api = {
  async getRecommendations(data: RecommendationRequest): Promise<RecommendationResponse> {
    return request<RecommendationResponse>("/recommendations", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async trackEvent(event: ClientEventPayload): Promise<void> {
    try {
      await request<void>("/events", {
        method: "POST",
        body: JSON.stringify(event),
      });
    } catch (err) {
      // Falhas em telemetria nunca devem quebrar a UX do usuário
      console.warn("Falha ao registrar evento comportamental:", err);
    }
  },

  async findMentors(roleId: number, experiences?: string[]): Promise<MentorMatchResponse> {
    const payload: { role_id: number; experiences?: string[] } = { role_id: roleId };
    if (experiences && experiences.length >= 3) {
      payload.experiences = experiences;
    }
    return request<MentorMatchResponse>("/mentor-matches", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async requestMentoring(mentorId: string, data: MentorContactRequest): Promise<MentorContactResponse> {
    return request<MentorContactResponse>(`/mentor-matches/${mentorId}/requests`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async exportUserData(): Promise<UserDataExport> {
    return request<UserDataExport>("/users/me/data", {
      method: "GET",
    });
  },

  async deleteAccount(): Promise<void> {
    return request<void>("/users/me", {
      method: "DELETE",
    });
  },
};
