"use client";

import { motion } from "framer-motion";

export function Marquee() {
    const items = [
        "SOURCE GROUNDED",
        "ZERO HALLUCINATIONS",
        "CITATION ON EVERY ANSWER",
        "CPU-SAFE",
        "PRIVATE BY DESIGN",
        "FREE TIER AVAILABLE",
    ];

    return (
        <div className="relative w-full overflow-hidden bg-[#0D1F0D] py-4 border-y border-[#1A3A1A]">
            <div className="flex">
                <motion.div
                    initial={{ x: 0 }}
                    animate={{ x: "-50%" }}
                    transition={{ duration: 20, ease: "linear", repeat: Infinity }}
                    className="flex whitespace-nowrap"
                >
                    {[...items, ...items, ...items].map((item, i) => (
                        <div key={i} className="flex items-center mx-8">
                            <span className="text-accent font-mono text-sm tracking-wider font-bold">{item}</span>
                            <span className="mx-8 h-1.5 w-1.5 rounded-full bg-accent/50" />
                        </div>
                    ))}
                </motion.div>
            </div>
        </div>
    );
}
