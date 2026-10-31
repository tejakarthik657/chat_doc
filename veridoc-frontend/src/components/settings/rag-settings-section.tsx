"use client";

import { useState } from "react";
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export function RagSettingsSection() {
    const [inferenceMode, setInferenceMode] = useState<string>(() => {
        if (typeof window !== "undefined") {
            return localStorage.getItem("veridoc_inference_mode") || "fast_cloud";
        }
        return "fast_cloud";
    });

    const handleModeChange = (mode: string) => {
        setInferenceMode(mode);
        if (typeof window !== "undefined") {
            localStorage.setItem("veridoc_inference_mode", mode);
        }
    };

    return (
        <div className="space-y-6">
            <div>
                <h2 className="font-display text-2xl mb-1">Retrieval & Privacy Architecture</h2>
                <p className="text-text-secondary text-sm">Configure how clinical documents are vectorized, retrieved, and processed with verifiable privacy guarantees.</p>
            </div>

            {/* Privacy & Air-Gapped Mode Selector */}
            <Card className="p-6 space-y-4 border-accent/20 bg-accent/5">
                <div className="flex justify-between items-start">
                    <div className="space-y-1">
                        <div className="flex items-center gap-2">
                            <span className="font-medium text-text-primary">Inference Privacy Boundary</span>
                            <Badge variant="default" className={inferenceMode === "air_gapped_local" ? "bg-emerald-600 text-white" : "bg-blue-600 text-white"}>
                                {inferenceMode === "air_gapped_local" ? "AIR-GAPPED LOCAL (0 BYTES LEAVE)" : "GROQ LPU (ZERO DATA RETENTION)"}
                            </Badge>
                        </div>
                        <p className="text-xs text-text-muted">
                            Choose between ultra-fast LPU generation or 100% on-premise air-gapped execution for sensitive healthcare and clinical trial documents.
                        </p>
                    </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
                    <button
                        onClick={() => handleModeChange("fast_cloud")}
                        className={`p-4 rounded-xl border text-left transition-all cursor-pointer ${
                            inferenceMode === "fast_cloud"
                                ? "border-accent bg-surface shadow-md ring-2 ring-accent/20"
                                : "border-border bg-surface/50 hover:bg-surface"
                        }`}
                    >
                        <div className="flex items-center justify-between mb-1.5">
                            <span className="font-mono text-xs font-bold text-accent uppercase tracking-wider">Ultra-Fast LPU</span>
                            <span className="text-[10px] font-mono bg-blue-500/10 text-blue-700 border border-blue-500/20 px-1.5 py-0.5 rounded">ZDR Verified</span>
                        </div>
                        <div className="font-semibold text-text-primary text-sm mb-1">Groq LPU (Sub-Second)</div>
                        <p className="text-xs text-text-muted leading-relaxed">
                            Sends only top-5 relevant chunks under enterprise Zero Data Retention agreements. Ideal for high throughput.
                        </p>
                    </button>

                    <button
                        onClick={() => handleModeChange("air_gapped_local")}
                        className={`p-4 rounded-xl border text-left transition-all cursor-pointer ${
                            inferenceMode === "air_gapped_local"
                                ? "border-emerald-500 bg-surface shadow-md ring-2 ring-emerald-500/20"
                                : "border-border bg-surface/50 hover:bg-surface"
                        }`}
                    >
                        <div className="flex items-center justify-between mb-1.5">
                            <span className="font-mono text-xs font-bold text-emerald-600 uppercase tracking-wider">Air-Gapped Mode</span>
                            <span className="text-[10px] font-mono bg-emerald-500/10 text-emerald-700 border border-emerald-500/20 px-1.5 py-0.5 rounded">100% Offline</span>
                        </div>
                        <div className="font-semibold text-text-primary text-sm mb-1">Local Ollama / CPU</div>
                        <p className="text-xs text-text-muted leading-relaxed">
                            Zero network transit. Runs on local Ollama or CPU models directly inside your private VPC. Full HIPAA compliance.
                        </p>
                    </button>
                </div>
            </Card>

            {/* Hybrid Search Toggle */}
            <Card className="flex flex-row items-center justify-between p-6">
                <div className="space-y-1">
                    <div className="font-medium text-text-primary">Hybrid Search (Dense + BM25)</div>
                    <div className="text-sm text-text-muted">Fuses dense semantic vectors with Reciprocal Rank Fusion (RRF k=60) for exact clinical keyword recall.</div>
                </div>
                <div className="bg-accent rounded-full p-1 w-12 flex justify-end cursor-pointer">
                    <div className="h-4 w-4 bg-black rounded-full shadow-sm" />
                </div>
            </Card>

            {/* Similarity Threshold */}
            <Card className="p-6 space-y-6">
                <div className="flex justify-between items-center">
                    <div className="space-y-1">
                        <div className="font-medium text-text-primary">Similarity Threshold & Grounded Refusal</div>
                        <div className="text-sm text-text-muted">Minimum relevance match score before triggering grounded refusal.</div>
                    </div>
                    <Badge variant="default" className="text-base px-3 py-1 bg-surface-high font-mono">0.75</Badge>
                </div>
                <div className="relative h-2 bg-surface-high rounded-full overflow-hidden">
                    <div className="absolute top-0 left-0 bottom-0 w-[75%] bg-accent rounded-full" />
                </div>
                <div className="flex justify-between text-xs font-mono text-text-muted">
                    <span>Permissive (0.40)</span>
                    <span>Strict Regulatory (0.85)</span>
                </div>
            </Card>

            {/* Reranker Config */}
            <Card className="p-6 space-y-4">
                <div className="flex justify-between items-center">
                    <div className="space-y-1">
                        <div className="font-medium text-text-primary">Cross-Encoder Context Budget</div>
                        <div className="text-sm text-text-muted">Number of high-precision chunks passed after BGE cross-encoder reranking.</div>
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="font-mono text-sm font-bold px-3 py-1 bg-surface-high rounded border border-border">Top 5 Chunks</span>
                    </div>
                </div>
            </Card>
        </div>
    );
}
