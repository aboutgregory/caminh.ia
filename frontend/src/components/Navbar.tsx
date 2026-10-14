import { Compass, User, LogIn } from "lucide-react";

interface NavbarProps {
  userEmail?: string | null;
  onOpenAuth: () => void;
  onOpenAccount: () => void;
  onReset: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  userEmail,
  onOpenAuth,
  onOpenAccount,
  onReset,
}) => {
  return (
    <header className="sticky top-0 z-40 w-full border-b border-line bg-dark-900/80 backdrop-blur-xl">
      <div className="max-w-6xl mx-auto px-4 md:px-8 h-16 flex items-center justify-between">
        {/* Logo caminh.ia */}
        <div
          onClick={onReset}
          className="flex items-center gap-2.5 cursor-pointer group"
        >
          <div className="w-9 h-9 rounded-xl bg-brand-light/15 border border-brand-light/30 text-brand-light flex items-center justify-center group-hover:scale-105 transition-transform">
            <Compass className="w-5 h-5 text-brand-light animate-driftBoat" />
          </div>
          <div className="flex flex-col">
            <span className="font-display font-bold text-lg text-ink tracking-wider flex items-center">
              caminh<span className="text-brand-light">.ia</span>
            </span>
            <span className="text-[10px] font-data text-ink-3 -mt-1 tracking-widest uppercase">
              CarrerMatch by BHO
            </span>
          </div>
        </div>

        {/* Ações da Direita */}
        <div className="flex items-center gap-3">
          {userEmail ? (
            <button
              onClick={onOpenAccount}
              className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-data glass border-brand-light/30 text-brand-light hover:border-brand-light transition-all"
            >
              <User className="w-3.5 h-3.5 text-brand-light" />
              <span className="max-w-[150px] truncate">{userEmail}</span>
            </button>
          ) : (
            <button
              onClick={onOpenAuth}
              className="flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold btn-secondary transition-all"
            >
              <LogIn className="w-3.5 h-3.5 text-brand-light" />
              <span>Entrar</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
};
