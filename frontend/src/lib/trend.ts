import type { CareerPath } from "../types";

/**
 * Selo de tendência de mercado. Tendência é dado categórico, não status: usa a paleta da
 * marca (as cores success/warning/danger ficam reservadas para mensagens de UI).
 */
export function trendBadgeClass(trend: CareerPath["market_trend"]): string {
  switch (trend) {
    case "Em Alta":
      return "bg-brand-light/15 text-brand-light border border-brand-light/40";
    case "Emergente":
      return "bg-brand-mid/25 text-ink border border-brand-mid/50";
    default:
      return "bg-dark-600/70 text-ink-2 border border-line";
  }
}
