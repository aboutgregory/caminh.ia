import { useState } from "react";
import { X, Lock, CheckCircle2, AlertCircle } from "lucide-react";
import { supabase } from "../lib/supabase";

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
  reasonMessage?: string;
}

export const AuthModal: React.FC<AuthModalProps> = ({
  isOpen,
  onClose,
  reasonMessage = "Acesse sua conta para conversar com mentores e salvar seus caminhos mapeados.",
}) => {
  const [loading, setLoading] = useState<"google" | "linkedin" | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleOAuthLogin = async (provider: "google" | "linkedin_oidc") => {
    try {
      setLoading(provider === "google" ? "google" : "linkedin");
      setError(null);
      const { error } = await supabase.auth.signInWithOAuth({
        provider,
        options: {
          redirectTo: window.location.origin,
        },
      });
      if (error) {
        setError(error.message);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Falha na comunicação com o servidor de autenticação.");
    } finally {
      setLoading(null);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="auth-modal-title"
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
          title="Fechar"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="w-12 h-12 rounded-2xl bg-brand-light/15 border border-brand-light/30 text-brand-light flex items-center justify-center mx-auto mb-4">
          <Lock className="w-6 h-6" />
        </div>

        <h2 id="auth-modal-title" className="text-xl sm:text-2xl font-display font-bold text-ink mb-2">
          Acesso Seguro
        </h2>

        <p className="text-xs sm:text-sm text-ink-2 leading-relaxed mb-6">
          {reasonMessage}
        </p>

        {error && (
          <div className="mb-4 p-3 rounded-xl bg-danger/60 border border-danger/40 text-danger text-xs flex items-center gap-2 text-left">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div className="space-y-3">
          <button
            type="button"
            onClick={() => handleOAuthLogin("google")}
            disabled={loading !== null}
            className="w-full py-3 px-4 rounded-xl border border-line bg-dark-700/90 hover:bg-dark-700 hover:border-brand-light/50 text-ink text-sm font-semibold flex items-center justify-center gap-3 transition-all"
          >
            {loading === "google" ? (
              <div className="w-4 h-4 border-2 border-brand-light border-t-transparent rounded-full animate-spin" />
            ) : (
              <svg className="w-4 h-4" viewBox="0 0 24 24">
                <path
                  fill="#EA4335"
                  d="M12 5c1.6 0 3 .6 4.1 1.6l3.1-3.1C17.3 1.7 14.8 1 12 1 7.5 1 3.7 3.6 1.9 7.3l3.7 2.9C6.5 7.4 9 5 12 5z"
                />
                <path
                  fill="#4285F4"
                  d="M23.5 12.3c0-.8-.1-1.7-.2-2.3H12v4.5h6.5c-.3 1.5-1.1 2.8-2.4 3.7l3.7 2.9c2.2-2 3.7-5.1 3.7-8.8z"
                />
                <path
                  fill="#FBBC05"
                  d="M5.6 14.8c-.2-.7-.4-1.5-.4-2.8s.2-2.1.4-2.8L1.9 6.3C.7 8.7 0 10.8 0 12s.7 3.3 1.9 5.7l3.7-2.9z"
                />
                <path
                  fill="#34A853"
                  d="M12 23c3.2 0 6-1.1 8-3l-3.7-2.9c-1.1.7-2.5 1.2-4.3 1.2-3 0-5.5-2.4-6.4-5.2L1.9 16C3.7 19.7 7.5 23 12 23z"
                />
              </svg>
            )}
            <span>Continuar com Google</span>
          </button>

          <button
            type="button"
            onClick={() => handleOAuthLogin("linkedin_oidc")}
            disabled={loading !== null}
            className="w-full py-3 px-4 rounded-xl border border-line bg-dark-700/90 hover:bg-dark-700 hover:border-brand-light/50 text-ink text-sm font-semibold flex items-center justify-center gap-3 transition-all"
          >
            {loading === "linkedin" ? (
              <div className="w-4 h-4 border-2 border-brand-light border-t-transparent rounded-full animate-spin" />
            ) : (
              <svg className="w-4 h-4 fill-[#0A66C2]" viewBox="0 0 24 24">
                <path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.28 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.75M6.88 8.56a1.68 1.68 0 0 0 1.68-1.68c0-.93-.75-1.69-1.68-1.69a1.69 1.69 0 0 0-1.69 1.69c0 .93.76 1.68 1.69 1.68m1.39 9.94v-8.37H5.5v8.37h2.77z" />
              </svg>
            )}
            <span>Continuar com LinkedIn</span>
          </button>
        </div>

        <div className="mt-6 pt-4 border-t border-line text-center">
          <p className="text-[11px] text-ink-3 flex items-center justify-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-brand-light/80" />
            <span>Nenhum dado é publicado sem sua autorização explícita</span>
          </p>
        </div>
      </div>
    </div>
  );
};
