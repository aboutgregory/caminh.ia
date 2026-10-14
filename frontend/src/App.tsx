import { useState, useEffect, useRef } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Navbar } from "./components/Navbar";
import { HeroSection } from "./components/HeroSection";
import { CareerMapVisualization } from "./components/CareerMapVisualization";
import { ResultsSection } from "./components/ResultsSection";
import { CareerDetailsModal } from "./components/CareerDetailsModal";
import { MentorForm } from "./components/MentorForm";
import { AuthModal } from "./components/AuthModal";
import { AccountModal } from "./components/AccountModal";
import { ConsentBanner, loadConsent, type ConsentDecision } from "./components/ConsentBanner";
import { useRecommendations } from "./hooks/useRecommendations";
import { useTrackEvent } from "./hooks/useTrackEvent";
import { supabase } from "./lib/supabase";
import type { CareerPath, RecommendationResponse } from "./types";
import { AlertCircle, RotateCcw } from "lucide-react";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

function MainApp() {
  const [user, setUser] = useState<{ email?: string | null; id?: string } | null>(null);
  // LGPD: null = ainda não decidiu → nada é enviado até a pessoa responder ao banner
  const [consent, setConsent] = useState<ConsentDecision>(loadConsent);
  const [consentAttention, setConsentAttention] = useState(0);
  const [recommendations, setRecommendations] = useState<RecommendationResponse | null>(null);
  const [submittedExperiences, setSubmittedExperiences] = useState<string[]>([]);
  const [selectedPath, setSelectedPath] = useState<CareerPath | null>(null);
  const [mentorPath, setMentorPath] = useState<CareerPath | null>(null);
  const [isAuthOpen, setIsAuthOpen] = useState(false);
  const [isAccountOpen, setIsAccountOpen] = useState(false);
  const [authReason, setAuthReason] = useState<string | undefined>();

  const mapRef = useRef<HTMLDivElement>(null);
  const { track } = useTrackEvent();
  const { mutate: fetchRecommendations, isPending, error } = useRecommendations();

  // Monitora sessão Supabase
  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session?.user) {
        setUser({ email: session.user.email, id: session.user.id });
      }
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session?.user) {
        setUser({ email: session.user.email, id: session.user.id });
      } else {
        setUser(null);
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  const handleGenerate = (experiences: string[], riskTolerance: number) => {
    if (consent === null) {
      setConsentAttention((n) => n + 1); // banner pisca e recebe o foco
      return;
    }
    setSubmittedExperiences(experiences);
    fetchRecommendations(
      {
        experiences,
        risk_tolerance: riskTolerance,
        consent_data: consent,
      },
      {
        onSuccess: (data) => {
          setRecommendations(data);
          // Registra visualização de recomendação (RN-10)
          track({
            event_type: "recommendation_viewed",
            request_id: data.request_id,
          });

          // PRD §6.3: scroll suave para o mapa
          setTimeout(() => {
            mapRef.current?.scrollIntoView({ behavior: "smooth" });
          }, 150);
        },
      }
    );
  };

  const handleReset = () => {
    setRecommendations(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className="min-h-screen flex flex-col bg-dark-900 text-ink selection:bg-brand-light/30 selection:text-brand-light">
      <Navbar
        userEmail={user?.email}
        onOpenAuth={() => {
          setAuthReason(undefined);
          setIsAuthOpen(true);
        }}
        onOpenAccount={() => setIsAccountOpen(true)}
        onReset={handleReset}
      />

      <main className="flex-1">
        <HeroSection onSubmit={handleGenerate} isLoading={isPending} />

        {error && (
          <div className="max-w-3xl mx-auto px-4 mb-8">
            <div role="alert" className="p-4 rounded-2xl bg-danger/10 border border-danger/40 text-ink text-sm flex items-start gap-3 shadow-lg">
              <AlertCircle className="w-5 h-5 text-danger shrink-0 mt-0.5" aria-hidden />
              <div className="space-y-1">
                <span className="font-semibold block">{error.message}</span>
                {error.correlationId && (
                  <span className="text-xs font-data text-ink-3 block">
                    ID da transação: {error.correlationId}
                  </span>
                )}
                {error.retryAfter && (
                  <span className="text-xs font-data text-warning block">
                    Limite de requisições excedido. Tente novamente em {error.retryAfter} segundos.
                  </span>
                )}
              </div>
            </div>
          </div>
        )}

        {recommendations && (
          <div ref={mapRef} className="space-y-12 pb-24">
            {/* Visualização de Ilhas Mario World */}
            <CareerMapVisualization
              paths={recommendations.paths}
              onSelectPath={(path) => setSelectedPath(path)}
              selectedPathId={selectedPath?.id}
            />

            {/* Catálogo de Resultados em Cards */}
            <ResultsSection
              paths={recommendations.paths}
              onOpenDetails={(path) => setSelectedPath(path)}
              onOpenMentors={(path) => {
                if (!user) {
                  setAuthReason("É necessário entrar para solicitar mentoria com profissionais desta área.");
                  setIsAuthOpen(true);
                } else {
                  setMentorPath(path);
                }
              }}
            />

            <div className="text-center pt-8">
              <button
                onClick={handleReset}
                className="px-6 py-2.5 rounded-full glass border-brand-light/30 text-brand-light hover:border-brand-light text-xs font-medium inline-flex items-center gap-2 transition-all"
              >
                <RotateCcw className="w-3.5 h-3.5 text-brand-light" />
                <span>Explorar Novas Vivências</span>
              </button>
            </div>
          </div>
        )}
      </main>

      {/* Modais */}
      <CareerDetailsModal
        path={selectedPath}
        onClose={() => setSelectedPath(null)}
        onOpenMentors={(path) => {
          setSelectedPath(null);
          if (!user) {
            setAuthReason("É necessário entrar para solicitar mentoria com profissionais desta área.");
            setIsAuthOpen(true);
          } else {
            setMentorPath(path);
          }
        }}
        requestId={recommendations?.request_id}
      />

      <MentorForm
        path={mentorPath}
        experiences={submittedExperiences}
        isAuthenticated={!!user}
        onRequireAuth={() => {
          setAuthReason("É necessário entrar para ver e solicitar mentoria.");
          setIsAuthOpen(true);
        }}
        onClose={() => setMentorPath(null)}
      />

      <AuthModal
        isOpen={isAuthOpen}
        onClose={() => setIsAuthOpen(false)}
        reasonMessage={authReason}
      />

      <AccountModal
        isOpen={isAccountOpen}
        onClose={() => setIsAccountOpen(false)}
        userEmail={user?.email}
        onLoggedOut={() => setUser(null)}
      />

      {/* Banner de Consentimento LGPD Obrigatório */}
      <ConsentBanner decision={consent} onDecide={setConsent} attentionSignal={consentAttention} />
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <MainApp />
    </QueryClientProvider>
  );
}
