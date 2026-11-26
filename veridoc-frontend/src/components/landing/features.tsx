"use client";

import { motion } from "framer-motion";
import { Card } from "@/components/ui/card";
import { Search, Quote, ShieldAlert } from "lucide-react";

export function Features() {
    return (
        <section id="features" className="mx-auto max-w-7xl space-y-16 overflow-hidden px-4 py-16 sm:px-6 md:space-y-32 md:py-24">
            {/* Feature 1: Hybrid Search */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 md:gap-16 items-center">
                <motion.div
                    initial={{ opacity: 0, x: -50 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    className="order-2 md:order-1 relative"
                >
                    <Card className="p-5 sm:p-8 bg-surface/50 backdrop-blur border-border/50 min-h-[280px] sm:h-[400px] flex items-center justify-center relative overflow-hidden group">
                        <div className="absolute inset-0 bg-gradient-to-br from-accent/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />

                        {/* Diagram */}
                        <div className="relative z-10 flex flex-col sm:flex-row items-center gap-3 sm:gap-4 w-full justify-center">
                            <div className="flex flex-row sm:flex-col gap-2 sm:gap-4 text-center w-full sm:w-auto">
                                <div className="p-3 sm:p-4 bg-surface border border-border rounded text-xs sm:text-sm font-mono text-text-secondary flex-1 sm:flex-none">Semantic Search</div>
                                <div className="p-3 sm:p-4 bg-surface border border-border rounded text-xs sm:text-sm font-mono text-text-secondary flex-1 sm:flex-none">Keyword Search</div>
                            </div>
                            <div className="text-accent text-lg rotate-90 sm:rotate-0">→</div>
                            <div className="p-4 sm:p-6 bg-accent/10 border border-accent/20 rounded-lg text-accent font-bold text-center text-sm sm:text-base">Best Answer</div>
                        </div>
                    </Card>
                </motion.div>

                <div className="order-1 md:order-2 space-y-4 sm:space-y-6">
                    <div className="inline-flex items-center gap-2 text-accent text-xs sm:text-sm font-mono uppercase tracking-wider">
                        <Search size={16} />
                        <span>Hybrid Search</span>
                    </div>
                    <h2 className="font-display text-3xl sm:text-4xl md:text-5xl tracking-tight leading-tight">It reads between the lines AND reads the lines.</h2>
                    <p className="text-text-secondary text-sm sm:text-base md:text-lg leading-relaxed">
                        Search naturally across your saved sources. Threadwell brings together meaning and exact words, so an idea can resurface even when you don’t remember where you put it.
                    </p>
                </div>
            </div>

            {/* Feature 2: Citations */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 md:gap-16 items-center">
                <div className="space-y-4 sm:space-y-6">
                    <div className="inline-flex items-center gap-2 text-blue-500 text-xs sm:text-sm font-mono uppercase tracking-wider">
                        <Quote size={16} />
                        <span>Traceable answers</span>
                    </div>
                    <h2 className="font-display text-3xl sm:text-4xl md:text-5xl tracking-tight leading-tight">See what brought an answer together.</h2>
                    <p className="text-text-secondary text-sm sm:text-base md:text-lg leading-relaxed">
                        Answers show which saved sources informed them. Open a reference, check the original context, and decide what matters to you.
                    </p>
                </div>

                <motion.div
                    initial={{ opacity: 0, x: 50 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    className="relative"
                >
                    <Card className="p-4 sm:p-8 bg-surface/50 flex flex-col gap-3 sm:gap-4">
                        <div className="self-end bg-accent/10 text-accent p-3 sm:p-4 rounded-lg rounded-tr-none max-w-[95%] sm:max-w-[80%] text-xs sm:text-sm leading-relaxed">
                            Your notes mention keeping Sunday open. The event page says the exhibition closes at six.
                            <span className="ml-2 inline-flex items-center justify-center bg-blue-500/10 text-blue-600 border border-blue-500/20 px-1.5 py-0.5 rounded text-[10px] sm:text-xs font-mono">[2 sources]</span>
                        </div>

                        {/* Source snippet popover mock */}
                        <div className="self-end mt-1 sm:mt-2 w-full max-w-[95%] sm:max-w-[80%] bg-blue-500/5 border border-blue-500/20 p-2.5 sm:p-3 rounded text-[11px] sm:text-xs font-mono text-text-secondary">
                            <div className="text-blue-700 mb-1 font-semibold">Your weekend note · City exhibition page</div>
                            <div className="text-text-secondary leading-relaxed">...you wanted to leave Sunday free, and the exhibition is open until <span className="bg-blue-500/10 text-blue-800 font-medium px-1">6 pm</span>...</div>
                        </div>
                    </Card>
                </motion.div>
            </div>

            {/* Feature 3: Guardrails */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 md:gap-16 items-center">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    className="order-2 md:order-1"
                >
                    <Card className="p-6 sm:p-8 bg-surface/50 border-blue-500/10 flex items-center justify-center min-h-[220px] sm:h-[300px]">
                        <div className="flex flex-col items-center gap-3 sm:gap-4 text-center">
                            <div className="h-12 w-12 sm:h-16 sm:w-16 rounded-full bg-blue-500/10 flex items-center justify-center text-blue-500 border border-blue-500/20">
                                <ShieldAlert size={28} />
                            </div>
                            <div className="space-y-1 sm:space-y-2">
                                <div className="font-mono text-blue-500 font-bold text-xs sm:text-sm">NOT IN YOUR SOURCES</div>
                                <div className="text-xs sm:text-sm text-text-muted">I couldn’t find this in what you’ve saved.</div>
                            </div>
                        </div>
                    </Card>
                </motion.div>

                <div className="order-1 md:order-2 space-y-4 sm:space-y-6">
                    <div className="inline-flex items-center gap-2 text-blue-500 text-xs sm:text-sm font-mono uppercase tracking-wider">
                        <ShieldAlert size={16} />
                        <span>Honest boundaries</span>
                    </div>
                    <h2 className="font-display text-3xl sm:text-4xl md:text-5xl tracking-tight leading-tight">Clear when your sources come up short.</h2>
                    <p className="text-text-secondary text-sm sm:text-base md:text-lg leading-relaxed">
                        If your saved sources don’t contain an answer, Threadwell says so. It keeps what it knows—and what it doesn’t—clear.
                    </p>
                </div>
            </div>
        </section>
    );
}
