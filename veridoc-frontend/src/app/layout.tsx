import type { Metadata, Viewport } from "next";
import { Instrument_Serif, DM_Sans, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import clsx from "clsx";

export const viewport: Viewport = {
    width: "device-width",
    initialScale: 1,
    maximumScale: 5,
    userScalable: true,
    viewportFit: "cover",
    themeColor: "#F8FAFC",
};


const instrumentSerif = Instrument_Serif({
    weight: "400",
    subsets: ["latin"],
    variable: "--font-instrument-serif",
});

const dmSans = DM_Sans({
    subsets: ["latin"],
    variable: "--font-dm-sans",
});

const jetbrainsMono = JetBrains_Mono({
    subsets: ["latin"],
    variable: "--font-jetbrains-mono",
});

export const metadata: Metadata = {
    title: "NEXUS AI | Intelligence You Can Explore and Use",
    description: "Autonomous Web Intelligence, Living Memory (ECHO), Spatial Thought Canvas (MINDSPACE), and Live Interactive Artifacts (FORGE).",
    icons: {
        icon: "/favicon.svg",
        shortcut: "/favicon.svg",
        apple: "/favicon.svg",
    },
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="en">
            <body
                className={clsx(
                    instrumentSerif.variable,
                    dmSans.variable,
                    jetbrainsMono.variable,
                    "font-sans bg-background text-text-primary antialiased selection:bg-accent selection:text-surface"
                )}
            >
                {children}
            </body>
        </html>
    );
}
