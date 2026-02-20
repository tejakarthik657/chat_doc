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
                background: "#0A0A0F",
                surface: {
                    DEFAULT: "#111118",
                    high: "#1A1A28",
                },
                border: "#1E1E2E",
                accent: {
                    DEFAULT: "#4ADE80", // Electric Green
                    warm: "#F59E0B",    // Amber
                    blue: "#38BDF8",    // Sky Blue
                },
                text: {
                    primary: "#F0F0F5",
                    secondary: "#6B7280",
                    muted: "#374151",
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
