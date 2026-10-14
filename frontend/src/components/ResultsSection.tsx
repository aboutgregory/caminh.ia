import { Star, Users, Eye, Building2 } from "lucide-react";
import type { CareerPath } from "../types";
import { trendBadgeClass } from "../lib/trend";

interface ResultsSectionProps {
  paths: CareerPath[];
  onOpenDetails: (path: CareerPath) => void;
  onOpenMentors: (path: CareerPath) => void;
}

export const ResultsSection: React.FC<ResultsSectionProps> = ({
  paths,
  onOpenDetails,
  onOpenMentors,
}) => {
  return (
    <section className="py-12 px-4 md:px-8 max-w-6xl mx-auto">
      <div className="flex flex-col md:flex-row items-start md:items-end justify-between mb-8 gap-4">
        <div>
          <span className="text-xs font-data text-brand-light tracking-wider uppercase block mb-1">
            Catálogo de Recomendações ({paths.length} caminhos identificados)
          </span>
          <h2 className="text-2xl sm:text-3xl font-display font-bold text-ink">
            Oportunidades Mapeadas para Você
          </h2>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {paths.map((path) => (
          <div
            key={path.id}
            className="glass p-6 rounded-2xl border-line flex flex-col justify-between hover:border-brand-light/40 hover:bg-dark-700/85 transition-all group"
          >
            <div>
              {/* Cabeçalho do Card */}
              <div className="flex items-center justify-between gap-2 mb-3">
                <span className="text-xs font-data px-2 py-0.5 rounded bg-brand-light/10 text-brand-light border border-brand-light/25 font-bold">
                  Rank #{path.id}
                </span>

                <div className="flex items-center gap-1 text-brand-light">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <Star
                      key={i}
                      className={`w-3.5 h-3.5 ${
                        i < path.relevance ? "fill-brand-light text-brand-light" : "text-ink-3 opacity-40"
                      }`}
                    />
                  ))}
                </div>
              </div>

              {/* Título */}
              <h3 className="text-lg font-display font-semibold text-ink group-hover:text-brand-light transition-colors mb-2">
                {path.title}
              </h3>

              {/* Badges de Metadados */}
              <div className="flex flex-wrap items-center gap-2 mb-4">
                <span
                  className={`text-xs px-2.5 py-0.5 rounded-full font-medium ${trendBadgeClass(path.market_trend)}`}
                >
                  {path.market_trend}
                </span>

                {path.is_hybrid && (
                  <span className="text-xs px-2 py-0.5 rounded bg-brand-mid/20 border border-brand-mid/30 text-brand-light">
                    Híbrido
                  </span>
                )}
              </div>

              {/* Descrição resumida (renderizada como texto puro conforme diretriz de segurança) */}
              <p className="text-xs sm:text-sm text-ink-2 line-clamp-3 leading-relaxed mb-4">
                {path.description}
              </p>

              {/* 5 Habilidades-Chave */}
              <div className="mb-4 space-y-1.5">
                <span className="text-[11px] font-data text-ink-3 uppercase block">
                  5 Habilidades-Chave:
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {path.key_skills.map((skill, sIdx) => (
                    <span
                      key={sIdx}
                      className="text-[11px] font-sans px-2 py-0.5 rounded bg-dark-900/90 text-ink border border-line"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              </div>

              {/* Indústrias */}
              {path.industries.length > 0 && (
                <div className="flex items-center gap-1.5 text-xs text-ink-3 mb-4">
                  <Building2 className="w-3.5 h-3.5 text-brand-light/70 shrink-0" />
                  <span className="truncate">{path.industries.join(" • ")}</span>
                </div>
              )}
            </div>

            {/* Ações */}
            <div className="pt-4 border-t border-line flex items-center justify-between gap-2">
              <button
                type="button"
                onClick={() => onOpenDetails(path)}
                className="flex-1 py-2 px-3 text-xs font-semibold text-ink hover:text-brand-light bg-dark-700/80 hover:bg-dark-700 rounded-lg border border-line transition-colors flex items-center justify-center gap-1.5"
              >
                <Eye className="w-3.5 h-3.5" />
                <span>Ver Descritivo</span>
              </button>

              <button
                type="button"
                onClick={() => onOpenMentors(path)}
                className="flex-1 py-2 px-3 text-xs font-semibold text-dark-900 btn-primary rounded-lg transition-all flex items-center justify-center gap-1.5 shadow-sm"
              >
                <Users className="w-3.5 h-3.5" />
                <span>Buscar Mentor</span>
              </button>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
};
