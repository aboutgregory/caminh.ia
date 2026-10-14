import { Star, Compass, MapPin, Zap } from "lucide-react";
import type { CareerPath } from "../types";
import { trendBadgeClass } from "../lib/trend";

interface CareerMapVisualizationProps {
  paths: CareerPath[];
  onSelectPath: (path: CareerPath) => void;
  selectedPathId?: number;
}

export const CareerMapVisualization: React.FC<CareerMapVisualizationProps> = ({
  paths,
  onSelectPath,
  selectedPathId,
}) => {
  return (
    <section className="relative py-12 px-4 md:px-8 max-w-6xl mx-auto overflow-hidden">
      {/* Cabeçalho do Mapa */}
      <div className="text-center mb-10 space-y-2">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-data glass border-brand-light/30 text-brand-light">
          <Compass className="w-3.5 h-3.5 text-brand-light" />
          <span>Arquipélago de Possibilidades • Estilo Ilhas Flutuantes</span>
        </div>
        <h2 className="text-2xl sm:text-4xl font-display font-bold text-ink">
          Seu Mapa de Navegação Profissional
        </h2>
        <p className="text-xs sm:text-sm text-ink-2 max-w-xl mx-auto">
          Cada ilha representa um território de carreira que combina suas habilidades. Clique em qualquer ilha para ver a rota detalhada e os mentores disponíveis.
        </p>
      </div>

      {/* Grid de Ilhas Flutuantes */}
      <div className="relative min-h-[500px] w-full p-6 sm:p-10 rounded-3xl glass border-brand-light/20 bg-dark-900/60">
        {/* Linhas de constelação e conexão de fundo */}
        <div className="absolute inset-0 pointer-events-none opacity-20 bg-[radial-gradient(#B48DDA_1px,transparent_1px)] [background-size:24px_24px]" />

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 relative z-10">
          {paths.map((path, idx) => {
            const isSelected = selectedPathId === path.id;
            const floatDelay = `${(idx % 4) * 0.7}s`;

            return (
              <div
                key={path.id}
                style={{ animationDelay: floatDelay }}
                className="animate-floatIsland transition-all"
              >
                <div
                  onClick={() => onSelectPath(path)}
                  className={`group cursor-pointer p-5 rounded-2xl transition-all duration-300 relative border ${
                    isSelected
                      ? "glass-strong scale-[1.02] border-brand-light ring-2 ring-brand-light/40"
                      : "glass border-line hover:border-brand-light/50 hover:bg-dark-700/90 hover:scale-[1.01]"
                  }`}
                >
                  {/* Topo do Card de Ilha */}
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <span className="w-7 h-7 rounded-full bg-brand-light/15 border border-brand-light/30 text-brand-light flex items-center justify-center font-data text-xs font-bold">
                        #{path.id}
                      </span>
                      {path.is_hybrid && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-data tracking-wide uppercase bg-brand-mid/20 border border-brand-mid/40 text-brand-light flex items-center gap-1">
                          <Zap className="w-3 h-3" /> Híbrido
                        </span>
                      )}
                    </div>

                    {/* Estrelas */}
                    <div className="flex items-center gap-0.5 text-brand-light" title={`Relevância: ${path.relevance} de 5 estrelas`}>
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

                  {/* Título da Carreira */}
                  <h3 className="text-base sm:text-lg font-display font-semibold text-ink group-hover:text-brand-light transition-colors mb-2 line-clamp-2">
                    {path.title}
                  </h3>

                  {/* Tendência de mercado */}
                  <div className="flex items-center gap-2 mb-3">
                    <span
                      className={`text-[11px] font-medium px-2 py-0.5 rounded-full ${trendBadgeClass(path.market_trend)}`}
                    >
                      {path.market_trend}
                    </span>
                    <span className="text-[11px] font-data text-ink-3">
                      Confiança: {Math.round(path.confidence_score * 100)}%
                    </span>
                  </div>

                  {/* Habilidades-Chave (Pílulas) */}
                  <div className="flex flex-wrap gap-1.5 pt-2 border-t border-line">
                    {path.key_skills.slice(0, 3).map((skill, sIdx) => (
                      <span
                        key={sIdx}
                        className="text-[11px] font-sans px-2 py-0.5 rounded-md bg-dark-900/80 text-ink-2 border border-line truncate max-w-[140px]"
                      >
                        {skill}
                      </span>
                    ))}
                    {path.key_skills.length > 3 && (
                      <span className="text-[10px] font-data px-1.5 py-0.5 text-ink-3 self-center">
                        +{path.key_skills.length - 3}
                      </span>
                    )}
                  </div>

                  {/* CTA no hover */}
                  <div className="mt-4 pt-2 flex items-center justify-between text-xs text-brand-light font-medium opacity-80 group-hover:opacity-100 transition-opacity">
                    <span className="flex items-center gap-1">
                      <MapPin className="w-3.5 h-3.5" /> Explorar rota
                    </span>
                    <span className="text-[11px] text-ink-3 group-hover:text-brand-light transition-colors">
                      Ver detalhes →
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};
