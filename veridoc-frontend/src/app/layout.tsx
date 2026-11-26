import type { Metadata, Viewport } from "next";
import { Instrument_Serif, DM_Sans, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import clsx from "clsx";
import { ToastProvider } from "@/components/ui/toast-provider";

export const viewport: Viewport = {
    width: "device-width",
    initialScale: 1,
    maximumScale: 5,
    userScalable: true,
    viewportFit: "cover",
    themeColor: "#0b1d36",
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
    title: "Threadwell — Keep what matters in context",
    description: "Bring your notes, documents, images, audio, and links together. Ask across what you save and follow answers back to their sources.",
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
                <ToastProvider>{children}</ToastProvider>
            </body>
        </html>
    );
}
