"use client";

import { motion } from 'framer-motion';

const COMPANIES = [
    'Pfizer', 'Novartis', 'Roche', 'Merck',
    'GlaxoSmithKline', 'Sanofi', 'AbbVie', 'AstraZeneca'
];

export default function MarqueeStrip() {
    return (
        <div className="absolute bottom-0 w-full z-20 border-t border-white/5 bg-black/60 backdrop-blur-md">
            <div className="flex items-center h-12 overflow-hidden relative">
                <div className="absolute left-0 w-20 h-full bg-gradient-to-r from-background to-transparent z-10" />
                <div className="absolute right-0 w-20 h-full bg-gradient-to-l from-background to-transparent z-10" />

                <motion.div
                    className="flex items-center gap-16 whitespace-nowrap"
                    animate={{ x: [0, -1000] }}
                    transition={{ repeat: Infinity, duration: 40, ease: "linear" }}
                >
                    {[...COMPANIES, ...COMPANIES, ...COMPANIES].map((c, i) => (
                        <div key={i} className="flex items-center gap-2 grayscale hover:grayscale-0 opacity-40 hover:opacity-80 transition-all duration-300">
                            <span className="font-mono text-xs uppercase tracking-widest text-text-secondary">Trusted by {c}</span>
                        </div>
                    ))}
                </motion.div>
            </div>
        </div>
    );
}
