import { useState } from "react";
import { X, Users, Send, CheckCircle2, AlertCircle, ArrowLeft, MessageSquare } from "lucide-react";
import confetti from "canvas-confetti";
import type { CareerPath, Mentor } from "../types";
import { useMentorMatch, useRequestMentoring } from "../hooks/useMentorMatch";

interface MentorFormProps {
  path: CareerPath | null;
  experiences?: string[];
  isAuthenticated: boolean;
  onRequireAuth: () => void;
  onClose: () => void;
}

export const MentorForm: React.FC<MentorFormProps> = ({
  path,
  experiences,
  isAuthenticated,
  onRequireAuth,
  onClose,
}) => {
  const [selectedMentor, setSelectedMentor] = useState<Mentor | null>(null);
  const [message, setMessage] = useState("");
  const [success, setSuccess] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const { data, isLoading, error } = useMentorMatch(
    path?.id ?? null,
    experiences,
    isAuthenticated
  );

  const { mutate: sendRequest, isPending: isSending } = useRequestMentoring();

  if (!path) return null;

  if (!isAuthenticated) {
    return (
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="mentor-auth-required-title"
        className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-dark-900/80 backdrop-blur-md animate-fadeUp"
        onClick={onClose}
      >
        <div
          className="glass-strong w-full max-w-md rounded-3xl p-6 sm:p-8 relative border border-brand-light/40 shadow-2xl text-center text-ink"
          onClick={(e) => e.stopPropagation()}
        >
          <button
            onClick={onClose}
            className="absolute top-5 right-5 p-2 rounded-full text-ink-3 hover:text-ink hover:bg-dark-700 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>

          <div className="w-12 h-12 rounded-2xl bg-brand-light/15 border border-brand-light/30 text-brand-light flex items-center justify-center mx-auto mb-4">
            <Users className="w-6 h-6" />
          </div>

          <h2 id="mentor-auth-required-title" className="text-xl sm:text-2xl font-display font-bold mb-2">
            Autenticação Necessária
          </h2>
          <p className="text-xs sm:text-sm text-ink-2 leading-relaxed mb-6">
            Para garantir a privacidade dos mentores e evitar mensagens automáticas, o contato de mentoria exige login prévio.
          </p>

          <button
            onClick={() => {
              onClose();
              onRequireAuth();
            }}
            className="w-full py-3 px-6 btn-primary text-sm font-semibold flex items-center justify-center gap-2"
          >
            <span>Fazer Login para Ver Mentores</span>
          </button>
        </div>
      </div>
    );
  }

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedMentor) return;

    setSubmitError(null);
    sendRequest(
      {
        mentorId: selectedMentor.mentor_id,
        data: {
          role_id: path.id,
          message: message.trim(),
        },
      },
      {
        onSuccess: () => {
          setSuccess(true);
          confetti({
            particleCount: 80,
            spread: 60,
            origin: { y: 0.6 },
            colors: ["#B48DDA", "#B48DDA", "#3A246A"],
          });
        },
        onError: (err) => {
          setSubmitError(err.message || "Não foi possível enviar a solicitação.");
        },
      }
    );
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="mentor-form-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-dark-900/80 backdrop-blur-md animate-fadeUp"
      onClick={onClose}
    >
      <div
        className="glass-strong w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-3xl p-6 sm:p-8 relative border border-brand-light/40 shadow-2xl text-ink"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={onClose}
          className="absolute top-6 right-6 p-2 rounded-full text-ink-3 hover:text-ink hover:bg-dark-700 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {success ? (
          <div className="py-8 text-center space-y-4">
            <div className="w-16 h-16 rounded-full bg-success/80 border border-success/50 text-success flex items-center justify-center mx-auto">
              <CheckCircle2 className="w-8 h-8" />
            </div>
            <h2 id="mentor-form-title" className="text-2xl font-display font-bold text-ink">
              Solicitação Enviada com Sucesso!
            </h2>
            <p className="text-sm text-ink-2 max-w-md mx-auto leading-relaxed">
              Sua mensagem foi encaminhada com segurança para <strong className="text-brand-light">{selectedMentor?.display_name}</strong>. Quando o mentor responder, você receberá uma notificação no seu e-mail cadastrado.
            </p>
            <div className="pt-4">
              <button
                onClick={onClose}
                className="px-6 py-2.5 btn-primary text-xs font-semibold"
              >
                Concluir e Voltar ao Mapa
              </button>
            </div>
          </div>
        ) : selectedMentor ? (
          <div>
            <button
              onClick={() => setSelectedMentor(null)}
              className="text-xs font-medium text-brand-light hover:text-brand-light flex items-center gap-1.5 mb-4"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Voltar para lista de mentores</span>
            </button>

            <div className="p-4 rounded-xl bg-dark-900/80 border border-line mb-6 flex items-start gap-4">
              <div className="w-10 h-10 rounded-full bg-brand-light/20 text-brand-light font-bold flex items-center justify-center text-sm font-data shrink-0">
                {selectedMentor.display_name.charAt(0)}
              </div>
              <div>
                <h3 className="text-base font-semibold text-ink">
                  Solicitar Mentoria com {selectedMentor.display_name}
                </h3>
                {selectedMentor.headline && (
                  <p className="text-xs text-ink-2 mb-1">{selectedMentor.headline}</p>
                )}
                <span className="text-[11px] font-data text-brand-light">
                  Aderência: {Math.round(selectedMentor.similarity_score * 100)}% de sinergia
                </span>
              </div>
            </div>

            {submitError && (
              <div className="mb-4 p-3 rounded-xl bg-danger/60 border border-danger/40 text-danger text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{submitError}</span>
              </div>
            )}

            <form onSubmit={handleSendMessage} className="space-y-4">
              <div>
                <label className="text-xs font-semibold uppercase tracking-wider text-ink block mb-1.5 flex items-center gap-1.5">
                  <MessageSquare className="w-3.5 h-3.5 text-brand-light" />
                  Sua Mensagem de Apresentação (20 a 1000 caracteres)
                </label>
                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="Olá! Vi sua trajetória e gostaria de trocar ideias sobre como aplicar minhas habilidades de... nesta área de..."
                  rows={5}
                  maxLength={1000}
                  className="w-full px-4 py-3 bg-dark-900/70 border border-line rounded-xl text-ink placeholder-ink-3 text-sm focus:outline-none focus:border-brand-light focus:ring-1 focus:ring-brand-light transition-all resize-none"
                />
                <div className="flex justify-between items-center text-xs font-data text-ink-3 mt-1">
                  <span>{message.trim().length < 20 ? "Mínimo 20 caracteres" : "Comprimento adequado"}</span>
                  <span>{message.length}/1000</span>
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setSelectedMentor(null)}
                  className="px-4 py-2 text-xs font-medium text-ink-3 hover:text-ink"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={message.trim().length < 20 || isSending}
                  className="px-6 py-2.5 btn-primary text-xs font-semibold flex items-center gap-2 disabled:opacity-50"
                >
                  {isSending ? (
                    <div className="w-4 h-4 border-2 border-dark-900 border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <>
                      <Send className="w-3.5 h-3.5" />
                      <span>Enviar Solicitação</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        ) : (
          <div>
            <div className="mb-6">
              <span className="text-xs font-data text-brand-light tracking-wider uppercase block mb-1">
                Matching de Mentores • {path.title}
              </span>
              <h2 id="mentor-form-title" className="text-2xl font-display font-bold text-ink">
                Profissionais Que Já Trilharam Este Caminho
              </h2>
              <p className="text-xs text-ink-2 mt-1">
                Conectamos você a mentores com vivências complementares e experiência comprovada no cargo-alvo.
              </p>
            </div>

            {isLoading ? (
              <div className="py-12 text-center space-y-3">
                <div className="w-8 h-8 border-2 border-brand-light border-t-transparent rounded-full animate-spin mx-auto" />
                <p className="text-xs text-ink-2 font-data">Buscando mentores compatíveis na rede...</p>
              </div>
            ) : error ? (
              <div className="p-4 rounded-xl bg-danger/50 border border-danger/30 text-danger text-xs">
                {error.message}
              </div>
            ) : !data?.mentors || data.mentors.length === 0 ? (
              <div className="py-8 text-center p-6 rounded-2xl bg-dark-900/60 border border-line space-y-2">
                <p className="text-sm text-ink-2">
                  Ainda não temos mentores disponíveis especificamente para este caminho no momento.
                </p>
                <p className="text-xs text-ink-3">
                  Novos mentores são aprovados semanalmente na comunidade.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {data.mentors.map((m) => (
                  <div
                    key={m.mentor_id}
                    className="p-4 rounded-2xl glass border-line hover:border-brand-light/40 hover:bg-dark-700/90 transition-all flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
                  >
                    <div className="flex items-start gap-3.5">
                      <div className="w-10 h-10 rounded-full bg-brand-light/15 border border-brand-light/30 text-brand-light font-bold flex items-center justify-center text-sm font-data shrink-0 mt-0.5">
                        {m.display_name.charAt(0)}
                      </div>
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <h4 className="text-sm font-semibold text-ink">{m.display_name}</h4>
                          <span className="text-[11px] font-data px-2 py-0.5 rounded-full bg-brand-light/10 text-brand-light border border-brand-light/20">
                            {Math.round(m.similarity_score * 100)}% match
                          </span>
                        </div>

                        {m.headline && (
                          <p className="text-xs text-ink-2">{m.headline}</p>
                        )}

                        {m.match_reasons.length > 0 && (
                          <div className="flex flex-wrap items-center gap-1.5 pt-1">
                            <span className="text-[10px] text-ink-3 font-data">Pontes:</span>
                            {m.match_reasons.map((reason, idx) => (
                              <span
                                key={idx}
                                className="text-[10px] font-sans px-1.5 py-0.5 rounded bg-dark-900 text-brand-light/90 border border-brand-light/20"
                              >
                                {reason}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={() => setSelectedMentor(m)}
                      className="w-full sm:w-auto px-4 py-2 text-xs font-semibold btn-primary shrink-0"
                    >
                      Conectar
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
