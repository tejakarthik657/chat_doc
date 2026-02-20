"use client";

import { Button } from "@/components/ui/button";
import { motion } from "framer-motion";
import Link from "next/link";

export function Hero() {
    return (
        <section className="relative min-h-screen flex flex-col items-center justify-center overflow-hidden px-6 pt-20 pb-32">
            {/* Background Grid */}
            <div className="absolute inset-0 bg-[url('/grid.svg')] bg-center [mask-image:linear-gradient(180deg,white,rgba(255,255,255,0))]" />

            <div className="relative z-10 max-w-5xl mx-auto text-center space-y-8">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5 }}
                    className="inline-flex items-center rounded-full border border-accent/20 bg-accent/5 px-3 py-1 text-sm font-mono text-accent mb-4"
                >
                    <span className="flex h-2 w-2 rounded-full bg-accent mr-2 animate-pulse"></span>
                    RETRIEVAL_ACCURACY: 98.7%
                </motion.div>

                <h1 className="font-display text-6xl md:text-8xl leading-[0.9] tracking-tight">
                    <span className="block text-text-primary">Your documents.</span>
                    <span className="block text-accent">Finally, honest answers.</span>
                </h1>

                <p className="font-mono text-text-secondary max-w-2xl mx-auto text-lg">
                    Source-grounded AI. No hallucinations. No guessing. Just the document.
                </p>

                <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-8">
                    <Link href="/dashboard/documents/upload">
                        <Button size="lg" variant="primary" className="h-14 px-8 text-base">
                            Upload Your First Document →
                        </Button>
                    </Link>
                    <Link href="#how-it-works">
                        <Button size="lg" variant="ghost" className="h-14 px-8 text-base">
                            See How It Works
                        </Button>
                    </Link>
                </div>

                {/* Mockup */}
                <motion.div
                    initial={{ opacity: 0, y: 40 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2, duration: 0.8 }}
                    className="mt-20 relative mx-auto max-w-4xl rounded-xl border border-border bg-surface-high/50 p-2 shadow-2xl backdrop-blur-sm"
                >
                    <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-accent/50 to-transparent" />
                    <div className="rounded-lg bg-background border border-border overflow-hidden">
                        <div className="flex items-center border-b border-border px-4 py-3 bg-surface">
                            <div className="flex space-x-2">
                                <div className="h-3 w-3 rounded-full bg-red-500/20 border border-red-500/50" />
                                <div className="h-3 w-3 rounded-full bg-amber-500/20 border border-amber-500/50" />
                                <div className="h-3 w-3 rounded-full bg-green-500/20 border border-green-500/50" />
                            </div>
                            <div className="ml-4 flex rounded bg-surface-high px-2 py-0.5 text-xs text-text-muted font-mono">
                                research_paper_v2.pdf
                            </div>
                        </div>
                        <div className="p-8 font-mono text-sm space-y-6 text-left">
                            <div className="flex justify-end">
                                <div className="bg-surface-high text-text-primary px-4 py-2 rounded-lg max-w-[80%]">
                                    What is the recommended dosage for adults?
                                </div>
                            </div>
                            <div className="flex justify-start">
                                <div className="bg-accent/10 border border-accent/20 text-accent-light px-4 py-2 rounded-lg max-w-[80%] space-y-2">
                                    <p className="text-text-primary">Based on the clinical trials, the standard dosage is 50mg twice daily.</p>
                                    <div className="flex gap-2">
                                        <span className="text-xs bg-amber-500/10 text-amber-500 border border-amber-500/20 px-1.5 py-0.5 rounded cursor-pointer hover:bg-amber-500/20 transition-colors">[p.4] Clinical Protocols</span>
                                        <span className="text-xs bg-amber-500/10 text-amber-500 border border-amber-500/20 px-1.5 py-0.5 rounded cursor-pointer hover:bg-amber-500/20 transition-colors">[p.12] Safety Data</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </motion.div>
            </div>
        </section>
    );
}
