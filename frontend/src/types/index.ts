export type MarketTrend = "Em Alta" | "Estável" | "Emergente";

export type RecommendationSource = "item_based" | "knowledge_graph" | "hybrid";

export type DescriptionSource = "claude" | "fallback";

export interface CareerPath {
  id: number;
  role_slug: string;
  title: string;
  description: string;
  description_source: DescriptionSource;
  key_skills: string[];
  relevance: number; // 1-5
  confidence_score: number; // 0-1
  market_trend: MarketTrend;
  industries: string[];
  is_hybrid: boolean;
  source: RecommendationSource;
}

export interface RecommendationRequest {
  experiences: string[];
  risk_tolerance?: number;
  consent_data: boolean;
}

export interface RecommendationResponse {
  request_id: string;
  model_version: string;
  generated_in_ms: number;
  saved: boolean;
  paths: CareerPath[];
}

export interface Mentor {
  mentor_id: string;
  display_name: string;
  headline: string | null;
  similarity_score: number;
  match_reasons: string[];
}

export interface MentorMatchResponse {
  role_id: number;
  mentors: Mentor[];
}

export interface MentorContactRequest {
  role_id: number;
  message: string;
}

export interface MentorContactResponse {
  match_id: string;
  status: "requested";
}

export type ClientEventType =
  | "recommendation_viewed"
  | "career_expanded"
  | "career_saved"
  | "rated_positive"
  | "rated_negative"
  | "dismissed";

export interface ClientEventPayload {
  event_type: ClientEventType;
  request_id?: string;
  role_id?: number;
  rating?: number;
  reading_time_ms?: number;
}

export interface ApiError {
  error: string;
  correlation_id?: string;
  detalhes?: Array<{ campo: string; motivo: string }>;
}

export interface UserDataExport {
  conta: {
    email?: string;
    display_name?: string;
    is_mentor?: boolean;
    mentor_status?: string;
    mentor_headline?: string;
    consent_data_at?: string;
    created_at?: string;
  } | null;
  experiencias: Array<{
    position: number;
    raw_text: string;
    kind: string;
    created_at: string;
    habilidades: string[];
  }>;
  recomendacoes: Array<{
    request_id: string;
    rank: number;
    title: string;
    confidence_score: number;
    description: string;
    created_at: string;
  }>;
  mentorias: Array<{
    papel: "mentorado" | "mentor";
    status: string;
    message: string;
    created_at: string;
    cargo?: string;
  }>;
  eventos: Array<{
    event_type: string;
    occurred_at: string;
    payload: Record<string, unknown>;
  }>;
  exportado_em: string;
}
