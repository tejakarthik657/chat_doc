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
                background: "#F8FAFC",
                surface: {
                    DEFAULT: "#FFFFFF",
                    high: "#EFF6FF",
                },
                border: "rgba(203, 213, 225, 0.8)",
                accent: {
                    DEFAULT: "#1D4ED8",
                    success: "#2563EB",
                    warm: "#60A5FA",
                    blue: "#3B82F6",
                },
                text: {
                    primary: "#0F172A",
                    secondary: "#334155",
                    muted: "#64748B",
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
