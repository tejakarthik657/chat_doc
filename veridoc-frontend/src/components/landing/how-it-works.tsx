"use client";

import { motion } from "framer-motion";
import { Upload, Database, MessageSquare } from "lucide-react";

export function HowItWorks() {
    const steps = [
        {
            id: "01",
            title: "Ingest Knowledge",
            description: "Crawl website directories or upload academic, administrative, and compliance PDFs.",
            icon: Upload,
        },
        {
            id: "02",
            title: "AI Semantic Indexing",
            description: "DevFrames Synapse chunks, embeds, and indexes records automatically using hybrid search (Keyword + Semantic).",
            icon: Database,
        },
        {
            id: "03",
            title: "Cited Query Search",
            description: "Get precise, grounded answers accompanied by clickable, page-level citations.",
            icon: MessageSquare,
        },
    ];

    return (
        <section id="how-it-works" className="py-16 md:py-32 px-4 sm:px-6 relative bg-background overflow-hidden">
            <div className="max-w-6xl mx-auto">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-8 sm:gap-12">
                    {steps.map((step, index) => (
                        <motion.div
                            key={step.id}
                            initial={{ opacity: 0, y: 20 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            transition={{ delay: index * 0.2, duration: 0.5 }}
                            viewport={{ once: true }}
                            className="relative group"
                        >
                            {/* Large background number */}
                            <div className="absolute -top-10 sm:-top-12 left-0 sm:-left-6 text-[80px] sm:text-[120px] font-display text-text-muted/5 select-none z-0 group-hover:text-accent/5 transition-colors duration-500 pointer-events-none">
                                {step.id}
                            </div>

                            <div className="relative z-10 border-l border-border pl-5 sm:pl-8 py-2">
                                <div className="mb-4 sm:mb-6 inline-flex items-center justify-center p-2.5 sm:p-3 rounded-lg bg-surface-high/50 text-accent border border-white/5">
                                    <step.icon size={22} />
                                </div>

                                <div className="font-mono text-accent text-xs sm:text-sm mb-1.5 sm:mb-2">STEP {step.id}</div>
                                <h3 className="font-display text-2xl sm:text-3xl mb-2 sm:mb-4 text-text-primary">{step.title}</h3>
                                <p className="text-text-secondary leading-relaxed font-sans text-sm sm:text-base md:text-lg">{step.description}</p>
                            </div>
                        </motion.div>
                    ))}
                </div>
            </div>
        </section>
    );
}
