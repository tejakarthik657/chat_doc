"use client";

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const QUERIES = [
    "Analyzing patient history...",
    "Cross-referencing drug interactions...",
    "Retrieving clinical protocol 7-B...",
    "Checking contraindications...",
    "Summarizing discharge notes...",
    "Verifying dosage guidelines...",
    "Scanning radiology reports...",
    "Indexing genomic markers..."
];

export default function QueryFeed() {
    const [activeQuery, setActiveQuery] = useState(QUERIES[0]);

    useEffect(() => {
        const interval = setInterval(() => {
            setActiveQuery(QUERIES[Math.floor(Math.random() * QUERIES.length)]);
        }, 2500);
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="absolute left-8 bottom-24 z-20">
            <div className="flex flex-col gap-2">
                <span className="font-mono text-[10px] text-white/30 uppercase tracking-widest">Live Activity</span>
                <div className="flex items-center gap-3 bg-black/40 backdrop-blur border border-white/5 rounded-lg p-3 pr-6">
                    <div className="relative">
                        <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                        <div className="absolute inset-0 rounded-full bg-emerald-500/50 animate-ping" />
                    </div>
                    <AnimatePresence mode="wait">
                        <motion.span
                            key={activeQuery}
                            initial={{ opacity: 0, y: 5 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -5 }}
                            className="font-mono text-xs text-emerald-400"
                        >
                            {activeQuery}
                        </motion.span>
                    </AnimatePresence>
                </div>
            </div>
        </div>
    );
}
