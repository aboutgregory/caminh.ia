/** @type {import('tailwindcss').Config} */
// Tokens de "bho: sistema visual · pré-proposta" — valores vêm das variáveis CSS em src/index.css.
// O caminh.ia consome a marca-mãe; cores da campanha terra fértil não existem aqui de propósito.
const withAlpha = (variable, hex) => `color-mix(in srgb, var(${variable}, ${hex}) calc(<alpha-value> * 100%), transparent)`;

export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        brand: {
          deep: withAlpha("--brand-deep", "#3A246A"),
          mid: withAlpha("--brand-mid", "#7B5494"),
          light: withAlpha("--brand-light", "#B48DDA"),
        },
        dark: {
          900: withAlpha("--dark-900", "#0D0720"),
          800: withAlpha("--dark-800", "#150A2A"),
          700: withAlpha("--dark-700", "#1E1040"),
          600: withAlpha("--dark-600", "#2A1555"),
          500: withAlpha("--dark-500", "#3D2070"),
        },
        // texto sobre escuro: branco ou lavanda (nunca --brand-deep)
        ink: {
          DEFAULT: "rgb(255 255 255 / <alpha-value>)",
          2: "rgb(255 255 255 / 0.78)",  // secundário
          3: "rgb(255 255 255 / 0.60)",  // apoio, placeholders (≥ 7:1 sobre --dark-900)
        },
        line: "rgb(180 141 218 / 0.22)", // borda do vidro
        success: withAlpha("--success", "#34C88A"),
        warning: withAlpha("--warning", "#E8A93A"),
        danger: withAlpha("--danger", "#E84DB6"),
      },
      fontFamily: {
        // uma família só: Montserrat (display, texto, UI e números)
        sans: ['"Montserrat Variable"', "system-ui", '"Segoe UI"', "Arial", "sans-serif"],
        display: ['"Montserrat Variable"', "system-ui", "sans-serif"],
        data: ['"Montserrat Variable"', "system-ui", "sans-serif"],
      },
      // escala modular 1,25 sobre 16px: 12 · 14 · 16 · 20 · 25 · 31 · 39 · 49 · 61
      fontSize: {
        "bho-12": ["12px", { lineHeight: "1.3" }],
        "bho-14": ["14px", { lineHeight: "1.5" }],
        "bho-16": ["16px", { lineHeight: "1.6" }],
        "bho-20": ["20px", { lineHeight: "1.3" }],
        "bho-25": ["25px", { lineHeight: "1.3" }],
        "bho-31": ["31px", { lineHeight: "1.2", letterSpacing: "-0.01em" }],
        "bho-39": ["39px", { lineHeight: "1.2", letterSpacing: "-0.01em" }],
        "bho-49": ["49px", { lineHeight: "1.1", letterSpacing: "-0.02em" }],
        "bho-61": ["61px", { lineHeight: "1.1", letterSpacing: "-0.02em" }],
      },
      keyframes: {
        fadeUp: {
          "0%": { opacity: "0", transform: "translateY(20px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        floatIsland: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-10px)" },
        },
        driftBoat: {
          "0%, 100%": { transform: "rotate(-1deg) translateY(0px)" },
          "50%": { transform: "rotate(1.5deg) translateY(-5px)" },
        },
        pulseGlow: {
          "0%, 100%": { boxShadow: "0 0 15px rgba(180, 141, 218, 0.2)" },
          "50%": { boxShadow: "0 0 30px rgba(180, 141, 218, 0.45)" },
        },
      },
      animation: {
        fadeUp: "fadeUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards",
        floatIsland: "floatIsland 5s ease-in-out infinite",
        driftBoat: "driftBoat 6s ease-in-out infinite",
        pulseGlow: "pulseGlow 3s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
