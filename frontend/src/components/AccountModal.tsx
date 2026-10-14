import { useState } from "react";
import { X, Download, Trash2, LogOut, ShieldAlert, CheckCircle2, AlertTriangle } from "lucide-react";
import { api } from "../lib/api";
import { supabase } from "../lib/supabase";

interface AccountModalProps {
  isOpen: boolean;
  onClose: () => void;
  userEmail?: string | null;
  onLoggedOut: () => void;
}

export const AccountModal: React.FC<AccountModalProps> = ({
  isOpen,
  onClose,
  userEmail,
  onLoggedOut,
}) => {
  const [isExporting, setIsExporting] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteConfirmation, setDeleteConfirmation] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleExportData = async () => {
    try {
      setIsExporting(true);
      setError(null);
      const data = await api.exportUserData();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `caminhia-meus-dados-${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      setSuccessMsg("Arquivo de dados exportado com sucesso.");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Falha ao exportar dados.");
    } finally {
      setIsExporting(false);
    }
  };

  const handleDeleteAccount = async () => {
    if (deleteConfirmation.trim().toUpperCase() !== "EXCLUIR") return;
    try {
      setIsDeleting(true);
      setError(null);
      await api.deleteAccount();
      await supabase.auth.signOut();
      onLoggedOut();
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Falha ao excluir a conta.");
      setIsDeleting(false);
    }
  };

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    onLoggedOut();
    onClose();
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="account-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-dark-900/80 backdrop-blur-md animate-fadeUp"
      onClick={onClose}
    >
      <div
        className="glass-strong w-full max-w-lg rounded-3xl p-6 sm:p-8 relative border border-brand-light/40 shadow-2xl text-ink"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={onClose}
          className="absolute top-5 right-5 p-2 rounded-full text-ink-3 hover:text-ink hover:bg-dark-700 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <h2 id="account-modal-title" className="text-xl sm:text-2xl font-display font-bold mb-1">
          Sua Conta & Privacidade (LGPD)
        </h2>
        {userEmail && (
          <p className="text-xs font-data text-brand-light mb-6">
            Conectado como: {userEmail}
          </p>
        )}

        {error && (
          <div className="mb-4 p-3 rounded-xl bg-danger/60 border border-danger/40 text-danger text-xs flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {successMsg && (
          <div className="mb-4 p-3 rounded-xl bg-success/60 border border-success/40 text-success text-xs flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{successMsg}</span>
          </div>
        )}

        <div className="space-y-6">
          {/* Exportação de Dados */}
          <div className="p-4 rounded-xl bg-dark-700/70 border border-line space-y-2">
            <h3 className="text-sm font-semibold flex items-center gap-2 text-ink">
              <Download className="w-4 h-4 text-brand-light" />
              Portabilidade de Dados (Art. 18 LGPD)
            </h3>
            <p className="text-xs text-ink-2 leading-relaxed">
              Baixe uma cópia integral em formato JSON de todas as suas experiências, caminhos de carreira salvos e eventos de uso registrados.
            </p>
            <div className="pt-2">
              <button
                type="button"
                onClick={handleExportData}
                disabled={isExporting}
                className="px-4 py-2 text-xs font-semibold rounded-lg btn-secondary flex items-center gap-2"
              >
                {isExporting ? "Preparando arquivo..." : "Baixar Meus Dados (.json)"}
              </button>
            </div>
          </div>

          {/* Exclusão Definitiva */}
          <div className="p-4 rounded-xl bg-danger/30 border border-danger/30 space-y-3">
            <h3 className="text-sm font-semibold flex items-center gap-2 text-danger">
              <ShieldAlert className="w-4 h-4 text-danger" />
              Exclusão Definitiva da Conta
            </h3>
            <p className="text-xs text-ink-2 leading-relaxed">
              Esta ação apaga irreversivelmente todas as suas experiências, conexões e credenciais. Não há recuperação após a confirmação.
            </p>
            <div>
              <label className="text-[11px] font-data text-ink-3 block mb-1">
                Digite <strong className="text-danger">EXCLUIR</strong> para confirmar:
              </label>
              <input
                type="text"
                value={deleteConfirmation}
                onChange={(e) => setDeleteConfirmation(e.target.value)}
                placeholder="EXCLUIR"
                className="w-full px-3 py-2 bg-dark-900 border border-danger/40 rounded-lg text-xs font-data text-ink placeholder-ink-3 focus:outline-none focus:border-danger"
              />
            </div>
            <button
              type="button"
              onClick={handleDeleteAccount}
              disabled={deleteConfirmation.trim().toUpperCase() !== "EXCLUIR" || isDeleting}
              className="px-4 py-2 text-xs font-semibold rounded-lg bg-danger/60 hover:bg-danger text-danger border border-danger/40 flex items-center gap-2 disabled:opacity-40 transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>{isDeleting ? "Excluindo..." : "Excluir Definitivamente Minha Conta"}</span>
            </button>
          </div>

          {/* Sair da Conta */}
          <div className="pt-2 flex justify-between items-center border-t border-line">
            <button
              type="button"
              onClick={handleSignOut}
              className="text-xs font-medium text-ink-3 hover:text-ink flex items-center gap-1.5 transition-colors"
            >
              <LogOut className="w-4 h-4" />
              <span>Encerrar Sessão</span>
            </button>

            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold rounded-lg bg-dark-700/80 hover:bg-dark-700 text-ink border border-line"
            >
              Fechar
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
