import { useState } from "react";
import { Plus, Trash2, Sparkles, Compass, AlertCircle, ArrowRight } from "lucide-react";

interface HeroSectionProps {
  onSubmit: (experiences: string[], riskTolerance: number) => void;
  isLoading: boolean;
}

const SAMUEL_PRESET = [
  "Emagreci 30 kg em 2019 com reeducação alimentar, treino de força e terapia contínua. Essa jornada me ensinou disciplina corporal, paciência com processos longos e escuta profunda do próprio corpo.",
  "Atuei como Growth Lead em startups B2B e B2C. Estruturei funis de aquisição, automações de marketing, análise de retenção e testes A/B com foco em métricas de ciclo de vida.",
  "Trabalho 100% em home office há mais de 5 anos. Criei rotinas rígidas de foco, gestão de energia, pausas ativas e automações que eliminam tarefas repetitivas.",
];

export const HeroSection: React.FC<HeroSectionProps> = ({ onSubmit, isLoading }) => {
  const [experiences, setExperiences] = useState<string[]>(["", "", ""]);
  const [riskTolerance, setRiskTolerance] = useState<number>(0.5);

  const handleAddExperience = () => {
    if (experiences.length < 5) {
      setExperiences([...experiences, ""]);
    }
  };

  const handleRemoveExperience = (index: number) => {
    if (experiences.length > 3) {
      const next = [...experiences];
      next.splice(index, 1);
      setExperiences(next);
    }
  };

  const handleChange = (index: number, val: string) => {
    const next = [...experiences];
    next[index] = val;
    setExperiences(next);
  };

  const loadPreset = () => {
    setExperiences([...SAMUEL_PRESET]);
  };

  // RN-01: mínimo 3 experiências preenchidas com pelo menos 10 caracteres
  const validExperiences = experiences.filter((e) => e.trim().length >= 10);
  const canSubmit = validExperiences.length >= 3 && !isLoading;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (canSubmit) {
      onSubmit(
        experiences.map((exp) => exp.trim()).filter(Boolean),
        riskTolerance
      );
    }
  };

  return (
    <section className="relative pt-12 pb-20 px-4 md:px-8 max-w-5xl mx-auto">
      {/* Badges superiores */}
      <div className="flex flex-wrap items-center justify-center gap-3 mb-6 animate-fadeUp">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-medium glass border-brand-light/30 text-brand-light">
          <Sparkles className="w-3.5 h-3.5 text-brand-light" />
          <span>IA treinada com dados de carreiras de 2025</span>
        </div>
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-data glass border-line text-ink-2">
          <span>+2.000 combinações já geradas</span>
        </div>
      </div>

      {/* Headline principal */}
      <div className="text-center mb-10 space-y-4 animate-fadeUp">
        <h1 className="text-3xl sm:text-5xl md:text-6xl font-display font-bold tracking-tight text-ink">
          Conecte o que parece <span className="text-highlight">desconexo</span>
        </h1>
        <p className="max-w-2xl mx-auto text-sm sm:text-base md:text-lg text-ink-2 font-sans font-normal leading-relaxed">
          Suas vivências — profissionais, pessoais, de saúde ou comunidade — são o ativo mais diferenciado da sua trajetória. O caminh.ia cruza suas experiências para revelar caminhos profissionais únicos e mentores que já trilharam esses mapas.
        </p>

        <div className="pt-2">
          <button
            type="button"
            onClick={loadPreset}
            className="text-xs font-medium text-brand-light/80 hover:text-brand-light underline underline-offset-4 transition-colors"
          >
            Carregar exemplo validado (Persona Samuel Medina)
          </button>
        </div>
      </div>

      {/* Formulário de Onboarding de Experiências */}
      <form onSubmit={handleSubmit} className="glass p-6 sm:p-8 rounded-2xl border-brand-light/25 space-y-6">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <label className="text-xs font-semibold uppercase tracking-wider text-brand-light flex items-center gap-2">
              <Compass className="w-4 h-4 text-brand-light" />
              Suas Experiências e Aprendizados (Mínimo 3, Máximo 5)
            </label>
            <span className="text-xs font-data text-ink-3">
              {validExperiences.length}/5 preenchidas
            </span>
          </div>

          <p className="text-xs text-ink-2">
            Conte o que você fez e o que isso te ensinou. Experiências pessoais (superação de saúde, esportes, arte, voluntariado) pesam com a mesma força que cargos corporativos.
          </p>

          <div className="space-y-4">
            {experiences.map((exp, idx) => (
              <div key={idx} className="relative group">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-data text-ink-3">
                    Experiência {idx + 1} {idx < 3 ? "(Obrigatória)" : "(Opcional)"}
                  </span>
                  <div className="flex items-center gap-3">
                    <span
                      className={`text-xs font-data ${
                        exp.length > 1500
                          ? "text-danger font-bold"
                          : exp.length < 10 && exp.length > 0
                          ? "text-warning"
                          : "text-ink-3"
                      }`}
                    >
                      {exp.length}/1500 caracteres
                    </span>
                    {experiences.length > 3 && (
                      <button
                        type="button"
                        onClick={() => handleRemoveExperience(idx)}
                        className="text-ink-3 hover:text-danger transition-colors p-1"
                        title="Remover campo"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                </div>

                <textarea
                  value={exp}
                  onChange={(e) => handleChange(idx, e.target.value)}
                  placeholder={`Ex: ${
                    idx === 0
                      ? "Liderei projetos de migração de nuvem e aprendi a coordenar equipes sob pressão..."
                      : idx === 1
                      ? "Passei 3 anos em processo de reabilitação e aprendi sobre disciplina motora e consistência..."
                      : "Trabalhei com vendas diretas e entendi a psicologia de tomada de decisão..."
                  }`}
                  rows={3}
                  maxLength={1500}
                  className="w-full px-4 py-3 bg-dark-900/70 border border-line rounded-xl text-ink placeholder-ink-3 text-sm focus:outline-none focus:border-brand-light focus:ring-1 focus:ring-brand-light transition-all resize-none"
                />
              </div>
            ))}
          </div>

          {experiences.length < 5 && (
            <button
              type="button"
              onClick={handleAddExperience}
              className="inline-flex items-center gap-2 text-xs font-semibold text-brand-light hover:text-brand-light py-2 px-3 rounded-lg border border-brand-light/20 hover:border-brand-light/40 transition-all"
            >
              <Plus className="w-4 h-4" />
              <span>Adicionar outra experiência ({experiences.length}/5)</span>
            </button>
          )}
        </div>

        {/* Nível de Abertura a Carreiras Emergentes */}
        <div className="pt-4 border-t border-line space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="font-medium text-ink">Apetite por Caminhos Emergentes</span>
            <span className="font-data text-brand-light">
              {riskTolerance <= 0.3
                ? "Conservador (Cargos consolidados)"
                : riskTolerance >= 0.7
                ? "Explorador (Cargos de fronteira e alta inovação)"
                : "Equilibrado (Transição gradual)"}
            </span>
          </div>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={riskTolerance}
            onChange={(e) => setRiskTolerance(parseFloat(e.target.value))}
            className="w-full accent-brand-light bg-dark-900 rounded-lg h-2 cursor-pointer"
          />
        </div>

        {/* Validação e Botão Principal */}
        <div className="pt-2 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="text-xs text-ink-3 flex items-center gap-1.5">
            {!canSubmit && (
              <>
                <AlertCircle className="w-4 h-4 text-warning shrink-0" />
                <span>Preencha ao menos 3 experiências (mínimo 10 caracteres cada) para mapear</span>
              </>
            )}
          </div>

          <button
            type="submit"
            disabled={!canSubmit}
            className="w-full sm:w-auto px-8 py-3.5 btn-primary flex items-center justify-center gap-3 text-sm tracking-wide disabled:opacity-50"
          >
            {isLoading ? (
              <>
                <div className="w-4 h-4 border-2 border-dark-900 border-t-transparent rounded-full animate-spin" />
                <span>Combinando experiências e gerando mapas...</span>
              </>
            ) : (
              <>
                <span>Gerar Meus Caminhos de Carreira</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </div>
      </form>
    </section>
  );
};
