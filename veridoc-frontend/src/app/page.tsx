import HeroSection from "@/components/hero-3d/hero-section";
import { Marquee } from "@/components/landing/marquee";
import { HowItWorks } from "@/components/landing/how-it-works";
import { Features } from "@/components/landing/features";
import { Footer } from "@/components/layout/footer";

export default function Home() {
    return (
        <main className="min-h-screen bg-background text-text-primary selection:bg-accent selection:text-surface">
            <HeroSection />
            <Marquee />
            <HowItWorks />
            <Features />
            <Footer />
        </main>
    );
}
