"use client";

import { useCallback, useState } from 'react';
import dynamic from 'next/dynamic';
import { PHASES, Phase } from '@/lib/three/scene-engine';
import HudOverlay from './hud-overlay';
import QueryFeed from './query-feed';
import MarqueeStrip from './marquee-strip';
import { Button } from '@/components/ui/button';
import Link from 'next/link';

// Canvas must be client-only (no SSR for WebGL)
const HeroCanvas = dynamic(() => import('./hero-canvas'), { ssr: false });

const NAV_LINKS = ['How it works', 'Features', 'Pricing', 'Docs'];

export default function HeroSection() {
    const [phase, setPhase] = useState<Phase>(PHASES.SINGULARITY);

    const handlePhaseChange = useCallback((p: Phase) => {
        setPhase(p);
    }, []);

    const isEarly = phase === PHASES.SINGULARITY || phase === PHASES.EXPLODING;

    return (
        <section className="relative w-screen h-screen overflow-hidden bg-[#02020A] cursor-none">
            {/* ── Three.js Canvas ─────────────────────────────── */}
            <HeroCanvas onPhaseChange={handlePhaseChange} />

            {/* ── Vignette overlay ────────────────────────────── */}
            <div className="absolute inset-0 z-[5] bg-[radial-gradient(ellipse_at_50%_50%,transparent_40%,rgba(2,2,10,0.7)_100%)] pointer-events-none" />

            {/* ── Scanline texture ────────────────────────────── */}
            <div className="absolute inset-0 z-[6] pointer-events-none opacity-20"
                style={{ backgroundImage: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,255,136,0.05) 2px, rgba(0,255,136,0.05) 4px)' }}
            />

            {/* ── NAV ─────────────────────────────────────────── */}
            <nav className="absolute top-0 left-0 right-0 z-30 flex items-center justify-between px-12 py-6 bg-gradient-to-b from-[#02020A]/90 to-transparent backdrop-blur-sm">
                <div className="flex items-center gap-2.5 font-mono text-[13px] font-medium text-text-primary tracking-[0.15em] uppercase">
                    <span className="w-2 h-2 bg-accent rounded-full inline-block animate-[pulse_2s_ease-in-out_infinite]" />
                    VERIDOC
                </div>

                <ul className="flex gap-10 list-none m-0 p-0">
                    {NAV_LINKS.map((l) => (
                        <li key={l}>
                            <a href="#" className="font-mono text-[11px] text-text-secondary hover:text-text-primary transition-colors tracking-[0.1em] uppercase no-underline">
                                {l}
                            </a>
                        </li>
                    ))}
                </ul>

                <Link href="/login">
                    <Button size="sm" className="font-mono text-[11px] uppercase tracking-widest cursor-none">
                        Start Free
                    </Button>
                </Link>
            </nav>

            {/* ── HUD Overlays ─────────────────────────────────── */}
            {!isEarly && <HudOverlay phase={phase} />}

            {/* ── HERO HEADLINE ────────────────────────────────── */}
            <div className="absolute inset-0 flex items-center justify-center z-15 pointer-events-none">
                <div
                    className="text-center max-w-[860px] px-8 transition-all duration-1000 ease-[cubic-bezier(0.16,1,0.3,1)]"
                    style={{
                        opacity: isEarly ? 0 : 1,
                        transform: isEarly ? 'translateY(24px) scale(0.97)' : 'translateY(0) scale(1)',
                    }}
                >
                    {/* Eyebrow */}
                    <div className="font-mono text-[11px] text-accent tracking-[0.22em] uppercase mb-7 flex items-center justify-center gap-3.5 animate-in fade-in slide-in-from-bottom-4 duration-1000 delay-300 fill-mode-both">
                        <span className="w-9 h-px bg-accent/40 inline-block" />
                        Source-Grounded Document Intelligence
                        <span className="w-9 h-px bg-accent/40 inline-block" />
                    </div>

                    {/* Headline */}
                    <h1 className="font-serif text-[clamp(48px,7.5vw,104px)] leading-[1.04] font-normal text-text-primary m-0 animate-in fade-in slide-in-from-bottom-8 duration-1000 delay-500 fill-mode-both">
                        Your documents.
                        <br />
                        <span className="italic text-accent drop-shadow-[0_0_60px_rgba(0,255,136,0.35)]">
                            Finally, honest answers.
                        </span>
                    </h1>

                    {/* Sub */}
                    <p className="font-mono text-[13px] text-text-secondary tracking-[0.04em] mx-auto my-[30px] mb-[52px] max-w-[520px] leading-[1.85] animate-in fade-in slide-in-from-bottom-4 duration-1000 delay-700 fill-mode-both">
                        Every answer is{' '}
                        <span className="text-amber-500">grounded in your PDF</span>
                        {'. '}Every claim has a page number.
                        If the answer isn&apos;t there —{' '}
                        <span className="text-red-500">we say so</span>.
                    </p>

                    {/* CTAs */}
                    <div className="flex items-center justify-center gap-4 pointer-events-auto animate-in fade-in slide-in-from-bottom-4 duration-1000 delay-900 fill-mode-both">
                        <Link href="/register">
                            <button
                                className="font-mono text-xs font-medium text-black bg-accent border-none px-10 py-[18px] cursor-none tracking-[0.1em] uppercase transition-all duration-200 hover:bg-emerald-400 hover:-translate-y-0.5 hover:shadow-[0_20px_50px_rgba(0,255,136,0.3)]"
                            >
                                Upload Your First Document →
                            </button>
                        </Link>

                        <button
                            className="font-mono text-xs font-normal text-accent bg-transparent border border-accent/30 px-9 py-[17px] cursor-none tracking-[0.1em] uppercase transition-all duration-200 hover:border-accent hover:bg-accent/10 hover:-translate-y-0.5"
                        >
                            See How It Works
                        </button>
                    </div>

                    {/* Click hint */}
                    <p className="font-mono text-[9px] text-text-muted tracking-[0.16em] uppercase mt-7 animate-in fade-in slide-in-from-bottom-2 duration-1000 delay-1000 fill-mode-both">
                        Click the graph to fire a retrieval query
                    </p>
                </div>
            </div>

            {/* ── Query Feed ───────────────────────────────────── */}
            {!isEarly && <QueryFeed />}

            {/* ── Scroll Hint ──────────────────────────────────── */}
            <div
                className="absolute bottom-12 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 z-20 pointer-events-none transition-opacity duration-1000 delay-[2000ms]"
                style={{ opacity: isEarly ? 0 : 1 }}
            >
                <span className="font-mono text-[9px] text-text-muted tracking-[0.2em] uppercase">scroll</span>
                <div className="w-px h-10 bg-gradient-to-b from-text-muted to-transparent relative overflow-hidden">
                    <div className="absolute top-0 w-full h-1/2 bg-gradient-to-b from-transparent to-text-primary animate-[scroll_1.5s_ease-in-out_infinite]" />
                </div>
            </div>

            {/* ── Marquee ──────────────────────────────────────── */}
            <MarqueeStrip />
        </section>
    );
}
