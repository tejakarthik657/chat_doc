import type { Metadata } from "next";
import { Instrument_Serif, DM_Sans, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import clsx from "clsx";

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
    title: "DevFrames Synapse | Document Intelligence System",
    description: "High-fidelity document search and RAG retrieval system for academic, governance, and institutional files.",
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
