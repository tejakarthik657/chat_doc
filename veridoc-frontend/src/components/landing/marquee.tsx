"use client";

import { motion } from "framer-motion";

export function Marquee() {
    const items = [
        "NOTES, FILES & LINKS",
        "ONE SEARCHABLE SPACE",
        "ANSWERS WITH SOURCES",
        "CAPTURE FIRST, SORT LATER",
        "ASK ACROSS WHAT YOU SAVE",
        "YOUR KNOWLEDGE, CONNECTED",
    ];

    return (
        <div className="relative w-full overflow-hidden border-y border-[#e2e8f0] bg-[#f1f5f9] py-4">
            <div className="flex">
                <motion.div
                    initial={{ x: 0 }}
                    animate={{ x: "-50%" }}
                    transition={{ duration: 20, ease: "linear", repeat: Infinity }}
                    className="flex whitespace-nowrap"
                >
                    {[...items, ...items, ...items].map((item, i) => (
                        <div key={i} className="flex items-center mx-8">
                            <span className="font-mono text-xs font-semibold tracking-[0.12em] text-[#334155] sm:text-sm">{item}</span>
                            <span className="mx-8 h-1.5 w-1.5 rounded-full bg-[#1d4ed8]/60" />
                        </div>
                    ))}
                </motion.div>
            </div>
        </div>
    );
}
