import { useEffect, useRef, useState } from "react";
import { ShieldCheck, X } from "lucide-react";

/** null = a pessoa ainda não decidiu; nenhum dado é enviado antes disso (seg. v2 §3.4). */
export type ConsentDecision = boolean | null;

const STORAGE_KEY = "caminhia_consent_data";

export function loadConsent(): ConsentDecision {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved === null ? null : saved === "true";
  } catch {
    return null; // storage bloqueado (aba anônima, política do navegador): pergunta de novo
  }
}

function saveConsent(value: boolean): void {
  try {
    localStorage.setItem(STORAGE_KEY, String(value));
  } catch {
    /* sem storage: a decisão vale só para esta visita */
  }
}

interface ConsentBannerProps {
  decision: ConsentDecision;
  onDecide: (consented: boolean) => void;
  /** incrementa quando alguém tenta gerar caminhos sem ter decidido: chama atenção para o banner */
  attentionSignal: number;
}

export const ConsentBanner: React.FC<ConsentBannerProps> = ({ decision, onDecide, attentionSignal }) => {
  const [expanded, setExpanded] = useState(false);
  const firstButton = useRef<HTMLButtonElement>(null);
  const showFull = decision === null || expanded;

  useEffect(() => {
    if (attentionSignal > 0) firstButton.current?.focus();
  }, [attentionSignal]);

  const decide = (value: boolean) => {
    saveConsent(value);
    onDecide(value);
    setExpanded(false);
  };

  if (!showFull) {
    return (
      <div className="fixed bottom-4 left-4 z-40">
        <button
          onClick={() => setExpanded(true)}
          className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium glass text-brand-light hover:border-brand-light transition-colors"
        >
          <ShieldCheck className="w-4 h-4" aria-hidden />
          <span>Privacidade: {decision ? "salvamento autorizado" : "somente o essencial"}</span>
        </button>
      </div>
    );
  }

  return (
    <aside
      aria-label="Consentimento de privacidade"
      className={`fixed bottom-0 inset-x-0 z-50 p-4 md:p-6 bg-dark-900/95 backdrop-blur-xl border-t border-brand-light/30 shadow-2xl ${
        attentionSignal > 0 && decision === null ? "animate-pulseGlow" : ""
      }`}
    >
      <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-start gap-3 flex-1">
          <div className="p-2 rounded-lg bg-brand-light/10 border border-brand-light/20 text-brand-light shrink-0 mt-0.5">
            <ShieldCheck className="w-5 h-5" aria-hidden />
          </div>
          <div className="text-xs md:text-sm text-ink-2 leading-relaxed">
            <span className="font-semibold text-ink block mb-1">Transparência e Governança de Dados (LGPD)</span>
            Suas experiências profissionais e vivências pessoais são processadas exclusivamente para mapear caminhos de
            carreira, com apoio do modelo de linguagem da Anthropic (Claude), e para conectar você a mentores compatíveis.
            Seus dados nunca são vendidos. Ao autorizar o salvamento, suas experiências e resultados ficam vinculados à sua
            conta para acompanhamento contínuo.
            {decision === null && attentionSignal > 0 && (
              <span className="block mt-2 font-semibold text-brand-light" role="status">
                Escolha uma opção para gerar seus caminhos.
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2.5 w-full md:w-auto shrink-0 justify-end">
          <button
            ref={firstButton}
            onClick={() => decide(false)}
            className="px-3.5 py-2 rounded-md text-xs font-medium text-ink-2 hover:text-ink hover:bg-dark-700/60 transition-colors"
          >
            Apenas essencial
          </button>
          <button onClick={() => decide(true)} className="px-4 py-2 rounded-md text-xs font-semibold btn-primary">
            Autorizar e salvar
          </button>
          {decision !== null && (
            <button
              onClick={() => setExpanded(false)}
              className="p-1.5 rounded-md text-ink-3 hover:text-ink transition-colors"
              aria-label="Minimizar aviso de privacidade"
            >
              <X className="w-4 h-4" aria-hidden />
            </button>
          )}
        </div>
      </div>
    </aside>
  );
};
