import { useEffect, useState } from "react";
import { X, Star, Users, ThumbsUp, ThumbsDown, Bookmark, Building2, Check, Compass } from "lucide-react";
import type { CareerPath } from "../types";
import { useTrackEvent } from "../hooks/useTrackEvent";
import { trendBadgeClass } from "../lib/trend";

interface CareerDetailsModalProps {
  path: CareerPath | null;
  onClose: () => void;
  onOpenMentors: (path: CareerPath) => void;
  requestId?: string;
}

export const CareerDetailsModal: React.FC<CareerDetailsModalProps> = ({
  path,
  onClose,
  onOpenMentors,
  requestId,
}) => {
  const { track } = useTrackEvent();
  const [rated, setRated] = useState<"positive" | "negative" | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!path) return;
    const startTime = Date.now();

    // Registra visualização
    track({
      event_type: "career_expanded",
      request_id: requestId,
      role_id: path.id,
    });

    return () => {
      const readingTimeMs = Date.now() - startTime;
      track({
        event_type: "career_expanded",
        request_id: requestId,
        role_id: path.id,
        reading_time_ms: readingTimeMs,
      });
    };
  }, [path, requestId, track]);

  if (!path) return null;

  const handleRate = (type: "positive" | "negative") => {
    setRated(type);
    track({
      event_type: type === "positive" ? "rated_positive" : "rated_negative",
      request_id: requestId,
      role_id: path.id,
      rating: type === "positive" ? 5 : 1,
    });
  };

  const handleSave = () => {
    setSaved(!saved);
    track({
      event_type: "career_saved",
      request_id: requestId,
      role_id: path.id,
    });
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="career-details-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-dark-900/80 backdrop-blur-md animate-fadeUp"
      onClick={onClose}
    >
      <div
        className="glass-strong w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-3xl p-6 sm:p-8 relative border border-brand-light/40 shadow-2xl text-ink"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Botão de Fechar */}
        <button
          onClick={onClose}
          className="absolute top-6 right-6 p-2 rounded-full text-ink-3 hover:text-ink hover:bg-dark-700 transition-colors"
          title="Fechar"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Cabeçalho */}
        <div className="flex items-center gap-2 mb-3">
          <span className="text-xs font-data px-2.5 py-1 rounded bg-brand-light/15 text-brand-light border border-brand-light/30 font-bold">
            Posição #{path.id}
          </span>
          <span
            className={`text-xs px-2.5 py-1 rounded-full font-medium ${trendBadgeClass(path.market_trend)}`}
          >
            {path.market_trend}
          </span>
          {path.is_hybrid && (
            <span className="text-xs px-2.5 py-1 rounded bg-brand-mid/20 border border-brand-mid/30 text-brand-light">
              Carreira Híbrida
            </span>
          )}
        </div>

        <h2 id="career-details-title" className="text-2xl sm:text-3xl font-display font-bold text-ink mb-3">
          {path.title}
        </h2>

        {/* Avaliação de Relevância */}
        <div className="flex items-center gap-4 mb-6 pb-4 border-b border-line">
          <div className="flex items-center gap-1 text-brand-light">
            {Array.from({ length: 5 }).map((_, i) => (
              <Star
                key={i}
                className={`w-4 h-4 ${
                  i < path.relevance ? "fill-brand-light text-brand-light" : "text-ink-3 opacity-40"
                }`}
              />
            ))}
            <span className="text-xs font-data ml-2 text-ink-2">
              ({path.relevance} / 5 estrelas)
            </span>
          </div>
          <span className="text-xs font-data text-brand-light">
            Aderência: {Math.round(path.confidence_score * 100)}%
          </span>
        </div>

        {/* Descritivo Contextualizado */}
        <div className="space-y-3 mb-6">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold text-brand-light uppercase tracking-wider flex items-center gap-1.5">
              <Compass className="w-4 h-4 text-brand-light" /> Por que este caminho faz sentido para você:
            </span>
            <span className="text-[11px] font-data text-ink-3">
              {path.description_source === "claude" ? "✦ IA Claude Sonnet" : "✦ Curadoria caminh.ia"}
            </span>
          </div>

          {/* Renderizado de forma segura como texto (sem dangerouslySetInnerHTML) */}
          <div className="p-4 rounded-xl bg-dark-900/70 border border-line text-sm leading-relaxed text-ink whitespace-pre-line">
            {path.description}
          </div>
        </div>

        {/* 5 Habilidades-Chave */}
        <div className="mb-6 space-y-2">
          <span className="text-xs font-data text-ink-3 uppercase block">
            5 Habilidades Relevantes para esta Trajetória:
          </span>
          <div className="flex flex-wrap gap-2">
            {path.key_skills.map((skill, idx) => (
              <span
                key={idx}
                className="text-xs font-sans px-3 py-1.5 rounded-lg bg-dark-700/90 text-ink border border-brand-light/25"
              >
                {skill}
              </span>
            ))}
          </div>
        </div>

        {/* Indústrias */}
        {path.industries.length > 0 && (
          <div className="mb-8 p-3 rounded-xl bg-dark-700/40 border border-line flex items-center gap-2 text-xs text-ink-2">
            <Building2 className="w-4 h-4 text-brand-light shrink-0" />
            <span>Setores com maior demanda: <strong className="text-ink">{path.industries.join(", ")}</strong></span>
          </div>
        )}

        {/* Feedback do Usuário e Botões de Ação */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 border-t border-line">
          <div className="flex items-center gap-2 w-full sm:w-auto justify-center sm:justify-start">
            <span className="text-xs text-ink-3 mr-1">Esta recomendação faz sentido?</span>
            <button
              onClick={() => handleRate("positive")}
              className={`p-2 rounded-lg border transition-colors ${
                rated === "positive"
                  ? "bg-success/80 border-success text-success"
                  : "bg-dark-700/80 border-line text-ink-3 hover:text-ink"
              }`}
              title="Gostei da sugestão"
            >
              <ThumbsUp className="w-4 h-4" />
            </button>
            <button
              onClick={() => handleRate("negative")}
              className={`p-2 rounded-lg border transition-colors ${
                rated === "negative"
                  ? "bg-danger/80 border-danger text-danger"
                  : "bg-dark-700/80 border-line text-ink-3 hover:text-ink"
              }`}
              title="Não faz sentido para mim"
            >
              <ThumbsDown className="w-4 h-4" />
            </button>
            <button
              onClick={handleSave}
              className={`p-2 rounded-lg border transition-colors ${
                saved
                  ? "bg-brand-light/20 border-brand-light text-brand-light"
                  : "bg-dark-700/80 border-line text-ink-3 hover:text-ink"
              }`}
              title="Salvar carreira"
            >
              {saved ? <Check className="w-4 h-4" /> : <Bookmark className="w-4 h-4" />}
            </button>
          </div>

          <button
            onClick={() => {
              onClose();
              onOpenMentors(path);
            }}
            className="w-full sm:w-auto px-6 py-2.5 btn-primary flex items-center justify-center gap-2 text-xs tracking-wide"
          >
            <Users className="w-4 h-4" />
            <span>Encontrar Mentores Nesta Área</span>
          </button>
        </div>
      </div>
    </div>
  );
};
