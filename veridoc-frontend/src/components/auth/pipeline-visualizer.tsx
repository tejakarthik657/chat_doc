"use client";

import { motion } from "framer-motion";
import { FileText, Database, Search, ArrowRight, Zap } from "lucide-react";

export function PipelineVisualizer() {
    return (
        <div className="relative w-full h-full bg-slate-50 overflow-hidden flex items-center justify-center">
            <div className="absolute inset-0 bg-[url('/grid.svg')] opacity-10" />

            {/* Central visualization container */}
            <div className="relative w-[400px] h-[400px]">
                {/* Document Node (Top) */}
                <motion.div
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5 }}
                    className="absolute top-0 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2"
                >
                    <div className="h-16 w-12 bg-surface border border-border rounded flex items-center justify-center text-accent">
                        <FileText size={24} />
                    </div>
                    <div className="text-xs font-mono text-text-muted">RAW PDF</div>
                </motion.div>

                {/* Chunks (Middle) */}
                <motion.div
                    className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full flex justify-center gap-4"
                >
                    {[1, 2, 3].map((i) => (
                        <motion.div
                            key={i}
                            initial={{ opacity: 0, scale: 0 }}
                            animate={{
                                opacity: [0, 1, 0],
                                y: [0, 50, 100],
                                scale: [0.8, 1, 0.8]
                            }}
                            transition={{
                                duration: 3,
                                repeat: Infinity,
                                delay: i * 1,
                                ease: "easeInOut"
                            }}
                            className="h-2 w-12 bg-accent/20 border border-accent/50 rounded-sm"
                        />
                    ))}
                </motion.div>

                {/* Vector Database (Bottom) */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5 }}
                    className="absolute bottom-0 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2"
                >
                    <div className="h-24 w-24 relative flex items-center justify-center">
                        <div className="absolute inset-0 border border-accent/20 rotate-45" />
                        <div className="absolute inset-0 border border-accent/20 rotate-[135deg]" />
                        <Database size={32} className="text-accent relative z-10" />
                        <div className="absolute inset-0 bg-accent/5 blur-xl animate-pulse" />
                    </div>
                    <div className="text-xs font-mono text-text-muted">VECTOR INDEX</div>
                </motion.div>

                {/* Connection Lines */}
                <svg className="absolute inset-0 w-full h-full pointer-events-none opacity-20">
                    <line x1="50%" y1="20%" x2="50%" y2="80%" stroke="#4ADE80" strokeWidth="1" strokeDasharray="4 4" />
                </svg>

                {/* Query Matches Animation */}
                <motion.div
                    className="absolute bottom-10 right-0"
                    animate={{ x: [20, 0], opacity: [0, 1] }}
                    transition={{ repeat: Infinity, duration: 4, repeatDelay: 1 }}
                >
                    <div className="flex items-center gap-2 bg-surface border border-border px-3 py-1.5 rounded-full text-xs font-mono text-text-primary">
                        <Search size={12} className="text-accent" />
                        <span>Does it cover...</span>
                    </div>
                </motion.div>

                <motion.div
                    className="absolute top-20 right-10"
                    animate={{ x: [0, -20], opacity: [0, 1, 0] }}
                    transition={{ repeat: Infinity, duration: 4, delay: 2, repeatDelay: 1 }}
                >
                    <div className="flex items-center gap-2 bg-accent/10 border border-accent/20 px-3 py-1.5 rounded text-xs font-mono text-accent">
                        <Zap size={12} />
                        <span>Match Found (0.92)</span>
                    </div>
                </motion.div>
            </div>

            {/* Stats Overlay */}
            <div className="absolute top-8 right-8 text-right space-y-1">
                <div className="text-xs font-mono text-text-muted">DOCUMENTS INDEXED</div>
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="text-2xl font-display text-text-primary"
                >
                    2,847
                </motion.div>
            </div>
        </div>
    );
}
