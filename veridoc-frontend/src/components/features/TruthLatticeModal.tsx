"use client";

import React, { useState, useEffect } from "react";
import { 
    ShieldCheck, 
    AlertCircle, 
    Flame, 
    CheckCircle2, 
    X, 
    RefreshCw, 
    Quote, 
    Layers, 
    Sliders 
} from "lucide-react";
import api from "@/lib/api";

interface TruthLatticeModalProps {
    isOpen: boolean;
    onClose: () => void;
    projectId: string;
    query: string;
    targetText: string;
}

export default function TruthLatticeModal({ 
    isOpen, 
    onClose, 
    projectId, 
    query, 
    targetText 
}: TruthLatticeModalProps) {
    const [loading, setLoading] = useState(false);
    const [auditData, setAuditData] = useState<any>(null);
    const [error, setError] = useState("");

    const runAudit = async () => {
        if (!targetText.trim()) return;
        setLoading(true);
        setError("");
        try {
            const res = await api.post(`/projects/${projectId}/red-team`, {
                query: query || "Verify factual accuracy of claims",
                target_text: targetText
            });
            setAuditData(res.data);
        } catch (err: any) {
            console.error("Truth Lattice Audit failed:", err);
            setError("Failed to run Truth Lattice audit. Please verify backend connection.");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (isOpen && !auditData && !loading) {
            runAudit();
        }
    }, [isOpen]);

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-2 sm:p-4">
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl w-full max-w-4xl max-h-[92dvh] sm:max-h-[90vh] flex flex-col shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
                {/* Header */}
                <div className="flex items-center justify-between px-3.5 sm:px-6 py-3 sm:py-4 border-b border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50 gap-2">
                    <div className="flex items-center gap-2.5 sm:gap-3 min-w-0">
                        <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-emerald-600/10 text-emerald-600 dark:bg-emerald-500/20 dark:text-emerald-400 flex items-center justify-center shrink-0">
                            <ShieldCheck className="w-5 h-5" />
                        </div>
                        <div className="min-w-0">
                            <h2 className="text-sm sm:text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2 truncate">
                                <span>Truth Lattice</span>
                                <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300 hidden xs:inline">
                                    Audit
                                </span>
                            </h2>
                            <p className="text-[11px] sm:text-xs text-slate-500 hidden sm:block truncate">
                                Dual-model consensus arbitration: Qwen-27B vs. GPT-OSS cross-examination against ground truth.
                            </p>
                        </div>
                    </div>
                    <button 
                        onClick={onClose}
                        className="p-1.5 sm:p-2 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-800 transition-all touch-manipulation active:scale-95 shrink-0"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Body */}
                <div className="p-3.5 sm:p-6 overflow-y-auto space-y-4 sm:space-y-6 flex-1 pb-[max(1rem,env(safe-area-inset-bottom))]">
                    {/* Target preview */}
                    <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-800 text-xs">
                        <span className="font-semibold text-slate-500 uppercase tracking-wider block mb-1">Audited Statement</span>
                        <p className="text-slate-800 dark:text-slate-200 line-clamp-3 italic">
                            "{targetText}"
                        </p>
                    </div>

                    {loading && (
                        <div className="py-12 flex flex-col items-center justify-center space-y-3">
                            <RefreshCw className="w-8 h-8 text-emerald-500 animate-spin" />
                            <div className="text-sm font-medium text-slate-700 dark:text-slate-300">
                                Executing Parallel Dual-Model Adversarial Red Teaming...
                            </div>
                            <div className="text-xs text-slate-400">
                                Deconstructing claims • Checking contradictions • Cross-referencing document vectors
                            </div>
                        </div>
                    )}

                    {error && (
                        <div className="p-4 rounded-xl bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900 text-xs text-red-600 dark:text-red-300 flex items-center justify-between">
                            <span>{error}</span>
                            <button onClick={runAudit} className="px-3 py-1 rounded bg-red-600 text-white font-medium">Retry</button>
                        </div>
                    )}

                    {auditData && !loading && (
                        <div className="space-y-6 animate-in fade-in duration-300">
                            {/* Score header */}
                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 sm:gap-4">
                                <div className="p-4 rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-center">
                                    <div className="text-xs text-slate-500 font-medium uppercase">Consensus Score</div>
                                    <div className="text-2xl font-black text-slate-900 dark:text-white mt-1">
                                        {auditData.consensus_score ?? 90}%
                                    </div>
                                </div>
                                <div className="p-4 rounded-xl bg-emerald-50/50 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-900/50 text-center">
                                    <div className="text-xs text-emerald-600 dark:text-emerald-400 font-medium uppercase flex items-center justify-center gap-1">
                                        <CheckCircle2 className="w-3.5 h-3.5" /> Verified
                                    </div>
                                    <div className="text-2xl font-black text-emerald-700 dark:text-emerald-300 mt-1">
                                        {auditData.agreed_count ?? 0}
                                    </div>
                                </div>
                                <div className="p-4 rounded-xl bg-amber-50/50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-900/50 text-center">
                                    <div className="text-xs text-amber-600 dark:text-amber-400 font-medium uppercase flex items-center justify-center gap-1">
                                        <AlertCircle className="w-3.5 h-3.5" /> Disputed
                                    </div>
                                    <div className="text-2xl font-black text-amber-700 dark:text-amber-300 mt-1">
                                        {auditData.disputed_count ?? 0}
                                    </div>
                                </div>
                                <div className="p-4 rounded-xl bg-red-50/50 dark:bg-red-950/20 border border-red-200 dark:border-red-900/50 text-center">
                                    <div className="text-xs text-red-600 dark:text-red-400 font-medium uppercase flex items-center justify-center gap-1">
                                        <Flame className="w-3.5 h-3.5" /> Hallucination
                                    </div>
                                    <div className="text-2xl font-black text-red-700 dark:text-red-300 mt-1">
                                        {auditData.hallucinated_count ?? 0}
                                    </div>
                                </div>
                            </div>

                            {/* Executive Synthesis */}
                            {auditData.red_team_synthesis && (
                                <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/70 border border-slate-200 dark:border-slate-700 text-xs text-slate-700 dark:text-slate-300 leading-relaxed">
                                    <span className="font-semibold text-slate-900 dark:text-white block mb-1">
                                        Red-Team Synthesis:
                                    </span>
                                    {auditData.red_team_synthesis}
                                </div>
                            )}

                            {/* Claims Matrix */}
                            <div className="space-y-3">
                                <h4 className="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider">
                                    Claim-by-Claim Verification Matrix
                                </h4>

                                {auditData.claims?.map((item: any, idx: number) => {
                                    const isVerified = item.status === "VERIFIED";
                                    const isDisputed = item.status === "DISPUTED";
                                    const isSpec = item.status === "UNGROUNDED_SPECULATION";

                                    return (
                                        <div 
                                            key={idx}
                                            className={`p-4 rounded-xl border space-y-2.5 transition-all ${
                                                isVerified 
                                                    ? "bg-emerald-50/30 dark:bg-emerald-950/10 border-emerald-200 dark:border-emerald-900/40"
                                                    : isDisputed 
                                                    ? "bg-amber-50/30 dark:bg-amber-950/10 border-amber-200 dark:border-amber-900/40"
                                                    : "bg-red-50/30 dark:bg-red-950/10 border-red-200 dark:border-red-900/40"
                                            }`}
                                        >
                                            <div className="flex items-start justify-between gap-3">
                                                <div className="text-sm font-semibold text-slate-900 dark:text-white">
                                                    "{item.claim}"
                                                </div>
                                                <span className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wide uppercase shrink-0 ${
                                                    isVerified 
                                                        ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                                                        : isDisputed 
                                                        ? "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300"
                                                        : "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300"
                                                }`}>
                                                    {item.status}
                                                </span>
                                            </div>

                                            {/* Primary vs Challenger insights */}
                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs pt-1 border-t border-slate-100 dark:border-slate-800">
                                                <div>
                                                    <span className="text-[10px] uppercase font-bold text-slate-400 block">Primary Model Verdict</span>
                                                    <span className="text-slate-700 dark:text-slate-300">{item.primary_model_verdict || "Corroborated"}</span>
                                                </div>
                                                <div>
                                                    <span className="text-[10px] uppercase font-bold text-slate-400 block">Challenger Red-Team Verdict</span>
                                                    <span className="text-slate-700 dark:text-slate-300">{item.challenger_model_verdict || "No issues flagged"}</span>
                                                </div>
                                            </div>

                                            {/* Evidence quote */}
                                            {item.evidence_quote && (
                                                <div className="text-xs text-slate-600 dark:text-slate-400 italic bg-white/60 dark:bg-slate-900/60 p-2.5 rounded-lg border border-slate-100 dark:border-slate-800 flex items-start gap-1.5">
                                                    <Quote className="w-3.5 h-3.5 text-slate-400 shrink-0 mt-0.5" />
                                                    <span>"{item.evidence_quote}"</span>
                                                </div>
                                            )}

                                            {/* Dispute note */}
                                            {item.dispute_reason && (
                                                <div className="text-xs text-amber-700 dark:text-amber-400 font-medium">
                                                    Dispute Note: {item.dispute_reason}
                                                </div>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
