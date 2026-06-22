import { Hero } from "@/components/landing/hero";
import { Marquee } from "@/components/landing/marquee";
import { HowItWorks } from "@/components/landing/how-it-works";
import { Features } from "@/components/landing/features";
import { Footer } from "@/components/layout/footer";

export default function Home() {
    return (
        <main className="min-h-screen bg-background text-text-primary selection:bg-accent selection:text-surface">
            <Hero />
            <Marquee />
            <HowItWorks />
            <Features />
            <Footer />
        </main>
    );
}
