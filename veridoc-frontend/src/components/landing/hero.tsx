"use client";

import { Button } from "@/components/ui/button";
import { motion } from "framer-motion";
import Link from "next/link";

const NAV_LINKS = ['How it works', 'Features', 'Pricing', 'Docs'];

export function Hero() {
    return (
        <section className="relative min-h-screen flex flex-col items-center justify-center overflow-hidden px-4 sm:px-6 pt-24 sm:pt-28 pb-20 sm:pb-32 bg-slate-50">
            <nav className="absolute top-0 left-0 right-0 z-30 flex items-center justify-between px-4 sm:px-8 md:px-16 py-4 sm:py-6 bg-white/60 backdrop-blur-md border-b border-slate-200/60">
                <div className="flex items-center gap-2 font-mono text-xs sm:text-[13px] font-bold text-slate-800 tracking-[0.12em] sm:tracking-[0.15em] uppercase">
                    <span className="w-2.5 h-2.5 bg-accent rounded-full inline-block animate-pulse" />
                    VeriDoc Synapse
                </div>

                <ul className="hidden md:flex gap-10 list-none m-0 p-0">
                    {NAV_LINKS.map((l) => (
                        <li key={l}>
                            <a href="#" className="font-mono text-[11px] text-text-secondary hover:text-text-primary transition-colors tracking-[0.1em] uppercase no-underline">
                                {l}
                            </a>
                        </li>
                    ))}
                </ul>

                <Link href="/login">
                    <Button size="sm" className="font-mono text-[11px] uppercase tracking-wider sm:tracking-widest bg-accent hover:bg-accent/80 text-white rounded-none cursor-pointer">
                        Access Platform
                    </Button>
                </Link>
            </nav>

            {/* Background Grid */}
            <div className="absolute inset-0 bg-[url('/grid.svg')] bg-center [mask-image:linear-gradient(180deg,white,rgba(255,255,255,0))]" />

            <div className="relative z-10 max-w-5xl mx-auto text-center space-y-6 sm:space-y-8 mt-8 sm:mt-12 w-full">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5 }}
                    className="inline-flex items-center rounded-full border border-accent/20 bg-accent/5 px-3 py-1 text-xs sm:text-sm font-mono text-accent mb-2 sm:mb-4"
                >
                    <span className="flex h-2 w-2 rounded-full bg-accent mr-2 animate-pulse"></span>
                    AIR-GAPPED LOCAL OR ZERO-RETENTION LPU // CITATION ACCURACY: 99.4%
                </motion.div>

                <h1 className="font-display text-4xl sm:text-6xl md:text-7xl lg:text-8xl leading-[1.05] sm:leading-[0.95] tracking-tight text-balance">
                    <span className="block text-text-primary">Autonomous Regulatory</span>
                    <span className="block text-accent">& Clinical Intelligence.</span>
                </h1>

                <p className="font-mono text-text-secondary max-w-2xl mx-auto text-sm sm:text-base md:text-lg px-2">
                    Stop regulatory fines and protocol violations before they happen. VeriDoc ActionMesh automatically audits clinical trials and engineering specs against live databases with mathematical citation proof.
                </p>

                <div className="flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-4 pt-4 sm:pt-8 w-full max-w-md sm:max-w-none mx-auto">
                    <Link href="/dashboard/documents" className="w-full sm:w-auto">
                        <Button size="lg" className="w-full sm:w-auto h-12 sm:h-14 px-6 sm:px-8 text-sm sm:text-base bg-accent hover:bg-accent/80 text-white rounded-none cursor-pointer">
                            Launch Clinical Workspace →
                        </Button>
                    </Link>
                    <Link href="#how-it-works" className="w-full sm:w-auto">
                        <Button size="lg" variant="outline" className="w-full sm:w-auto h-12 sm:h-14 px-6 sm:px-8 text-sm sm:text-base border-slate-200 hover:bg-slate-50 text-slate-700 rounded-none cursor-pointer">
                            Explore Architecture
                        </Button>
                    </Link>
                </div>

                {/* Mockup */}
                <motion.div
                    initial={{ opacity: 0, y: 40 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2, duration: 0.8 }}
                    className="mt-12 sm:mt-20 relative mx-auto max-w-4xl rounded-xl border border-border bg-white/80 p-1.5 sm:p-2 shadow-2xl backdrop-blur-sm"
                >
                    <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-accent/50 to-transparent" />
                    <div className="rounded-lg bg-background border border-border overflow-hidden">
                        <div className="flex items-center justify-between border-b border-border px-3 sm:px-4 py-2.5 sm:py-3 bg-surface">
                            <div className="flex items-center space-x-1.5 sm:space-x-2">
                                <div className="h-2.5 w-2.5 sm:h-3 sm:w-3 rounded-full bg-red-500/20 border border-red-500/50" />
                                <div className="h-2.5 w-2.5 sm:h-3 sm:w-3 rounded-full bg-amber-500/20 border border-amber-500/50" />
                                <div className="h-2.5 w-2.5 sm:h-3 sm:w-3 rounded-full bg-green-500/20 border border-green-500/50" />
                                <div className="ml-3 sm:ml-4 flex rounded bg-surface-high px-2 py-0.5 text-[10px] sm:text-xs text-text-muted font-mono truncate max-w-[200px] sm:max-w-none">
                                    oncology_protocol_phase2.pdf
                                </div>
                            </div>
                            <span className="font-mono text-[10px] sm:text-xs text-emerald-600 font-semibold bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded">
                                ACTIONMESH: LIVE DB CONNECTED
                            </span>
                        </div>
                        <div className="p-4 sm:p-8 font-mono text-xs sm:text-sm space-y-4 sm:space-y-6 text-left">
                            <div className="flex justify-end">
                                <div className="bg-surface-high text-text-primary px-3 sm:px-4 py-2 rounded-lg max-w-[90%] sm:max-w-[80%] leading-relaxed">
                                    Audit candidate patient cohort #104 against inclusion and exclusion criteria.
                                </div>
                            </div>
                            <div className="flex justify-start">
                                <div className="bg-accent/5 border border-accent/20 text-accent px-3 sm:px-4 py-2.5 sm:py-3 rounded-lg max-w-[95%] sm:max-w-[85%] space-y-2">
                                    <p className="text-text-primary leading-relaxed">
                                        <strong className="text-amber-600">Disqualification Alert:</strong> Patient #104-09 exhibits serum creatinine <strong>2.4 mg/dL</strong> in the EHR database, violating Trial Exclusion Criterion 4.2 (&gt;2.0 mg/dL). All other cohort candidates meet protocol guidelines.
                                    </p>
                                    <div className="flex flex-wrap gap-1.5 sm:gap-2 pt-1">
                                        <span className="text-[10px] sm:text-xs bg-amber-500/10 text-amber-700 border border-amber-500/20 px-1.5 py-0.5 rounded cursor-pointer hover:bg-amber-500/20 transition-colors break-words">[p.78] Exclusion Criterion 4.2</span>
                                        <span className="text-[10px] sm:text-xs bg-blue-500/10 text-blue-700 border border-blue-500/20 px-1.5 py-0.5 rounded cursor-pointer hover:bg-blue-500/20 transition-colors break-words">[EHR Live Sync: Patient #104-09]</span>
                                        <span className="text-[10px] sm:text-xs bg-emerald-500/10 text-emerald-700 border border-emerald-500/20 px-1.5 py-0.5 rounded cursor-pointer hover:bg-emerald-500/20 transition-colors break-words">[Slack MCP: Alert Dispatched]</span>
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
