"use client";

import { motion } from "framer-motion";
import { Card } from "@/components/ui/card";
import { Search, Quote, ShieldAlert } from "lucide-react";

export function Features() {
    return (
        <section className="py-16 md:py-24 px-4 sm:px-6 space-y-16 md:space-y-32 max-w-7xl mx-auto overflow-hidden">
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
                        Most AI misses the obvious. Keyword search misses the context. DevFrames Synapse combines vector embeddings with BM25 keyword matching to find the exact needle in the haystack.
                    </p>
                </div>
            </div>

            {/* Feature 2: Citations */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 md:gap-16 items-center">
                <div className="space-y-4 sm:space-y-6">
                    <div className="inline-flex items-center gap-2 text-amber-500 text-xs sm:text-sm font-mono uppercase tracking-wider">
                        <Quote size={16} />
                        <span>Zero Hallucinations</span>
                    </div>
                    <h2 className="font-display text-3xl sm:text-4xl md:text-5xl tracking-tight leading-tight">Every answer has a receipt.</h2>
                    <p className="text-text-secondary text-sm sm:text-base md:text-lg leading-relaxed">
                        If we can't find it in the document, we don't invent it. Every claim is backed by a clickable citation that takes you directly to the source paragraph.
                    </p>
                </div>

                <motion.div
                    initial={{ opacity: 0, x: 50 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    className="relative"
                >
                    <Card className="p-4 sm:p-8 bg-surface/50 flex flex-col gap-3 sm:gap-4">
                        <div className="self-end bg-accent/10 text-accent-light p-3 sm:p-4 rounded-lg rounded-tr-none max-w-[95%] sm:max-w-[80%] text-xs sm:text-sm leading-relaxed">
                            The policy strictly prohibits use of personal devices for company data.
                            <span className="ml-2 inline-flex items-center justify-center bg-amber-500/10 text-amber-600 border border-amber-500/20 px-1.5 py-0.5 rounded text-[10px] sm:text-xs font-mono cursor-pointer hover:bg-amber-500/20">[p.7]</span>
                        </div>

                        {/* Source snippet popover mock */}
                        <div className="self-end mt-1 sm:mt-2 w-full max-w-[95%] sm:max-w-[80%] bg-amber-500/5 border border-amber-500/20 p-2.5 sm:p-3 rounded text-[11px] sm:text-xs font-mono text-text-secondary">
                            <div className="text-amber-700 mb-1 font-semibold">[Page 7] Security Policy</div>
                            <div className="text-text-secondary leading-relaxed">...employees shall not create, store, or access Company Data on <span className="bg-amber-500/10 text-amber-800 font-medium px-1">personal devices</span> under any circumstances...</div>
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
                    <Card className="p-6 sm:p-8 bg-surface/50 border-red-500/10 flex items-center justify-center min-h-[220px] sm:h-[300px]">
                        <div className="flex flex-col items-center gap-3 sm:gap-4 text-center">
                            <div className="h-12 w-12 sm:h-16 sm:w-16 rounded-full bg-red-500/10 flex items-center justify-center text-red-500 border border-red-500/20">
                                <ShieldAlert size={28} />
                            </div>
                            <div className="space-y-1 sm:space-y-2">
                                <div className="font-mono text-red-500 font-bold text-xs sm:text-sm">NO INFORMATION FOUND</div>
                                <div className="text-xs sm:text-sm text-text-muted">I cannot answer this based on the provided documents.</div>
                            </div>
                        </div>
                    </Card>
                </motion.div>

                <div className="order-1 md:order-2 space-y-4 sm:space-y-6">
                    <div className="inline-flex items-center gap-2 text-red-500 text-xs sm:text-sm font-mono uppercase tracking-wider">
                        <ShieldAlert size={16} />
                        <span>Refusal Engine</span>
                    </div>
                    <h2 className="font-display text-3xl sm:text-4xl md:text-5xl tracking-tight leading-tight">It refuses rather than guesses.</h2>
                    <p className="text-text-secondary text-sm sm:text-base md:text-lg leading-relaxed">
                        When the answer isn't there, DevFrames Synapse admits it. We prioritize silence over plausible-sounding fiction. Ideal for administrative and audit use cases where accuracy is paramount.
                    </p>
                </div>
            </div>
        </section>
    );
}
