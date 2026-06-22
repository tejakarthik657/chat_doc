import type { Config } from "tailwindcss";

const config: Config = {
    content: [
        "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
        "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
        "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
    ],
    theme: {
        extend: {
            colors: {
                background: "#F8FAFC",     // slate-50 Canvas
                surface: {
                    DEFAULT: "#FFFFFF",    // pure white
                    high: "#F1F5F9",       // slate-100
                },
                border: "rgba(226, 232, 240, 0.6)", // slate-200/60 subtle separator
                accent: {
                    DEFAULT: "#6366F1",    // lavender-indigo primary
                    success: "#10B981",    // sage-mint active states
                    warm: "#F59E0B",       // amber warning
                    blue: "#3B82F6",       // sky blue info
                },
                text: {
                    primary: "#0F172A",    // deep charcoal text
                    secondary: "#475569",  // slate-600 description
                    muted: "#64748B",      // slate-500 helper text
                },
            },
            fontFamily: {
                display: ["var(--font-instrument-serif)", "serif"],
                sans: ["var(--font-dm-sans)", "sans-serif"],
                mono: ["var(--font-jetbrains-mono)", "monospace"],
            },
            animation: {
                fadeUp: "fadeUp 0.4s cubic-bezier(0.16, 1, 0.3, 1) both",
                pulse: "pulse 2s ease-in-out infinite",
                shimmer: "shimmer 1.5s infinite",
            },
            keyframes: {
                fadeUp: {
                    "0%": { opacity: "0", transform: "translateY(16px)" },
                    "100%": { opacity: "1", transform: "translateY(0)" },
                },
                pulse: {
                    "0%, 100%": { opacity: "1", transform: "scale(1)" },
                    "50%": { opacity: "0.4", transform: "scale(0.8)" },
                },
                shimmer: {
                    "from": { backgroundPosition: "-200% 0" },
                    "to": { backgroundPosition: "200% 0" },
                },
            },
        },
    },
    plugins: [],
};
export default config;
