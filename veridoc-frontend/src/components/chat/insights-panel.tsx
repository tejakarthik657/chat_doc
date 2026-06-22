"use client";

import { useEffect, useMemo, useState } from "react";
import { Brain, Sparkles, FileText, Tags, Search, Loader2 } from "lucide-react";
import { featuresService, DocumentInsights } from "@/services/features.service";

export function InsightsPanel({ docId }: { docId: string }) {
    const [insights, setInsights] = useState<DocumentInsights | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    useEffect(() => {
        let active = true;
        const run = async () => {
            setLoading(true);
            setError("");
            try {
                const data = await featuresService.getInsights(docId);
                if (active) setInsights(data);
            } catch (e: any) {
                if (active) setError(e?.response?.data?.detail || "Failed to load insights.");
            } finally {
                if (active) setLoading(false);
            }
        };
        run();
        return () => {
            active = false;
        };
    }, [docId]);

    const entityCount = useMemo(() => {
        if (!insights) return 0;
        return Object.values(insights.entities || {}).reduce((acc, list) => acc + list.length, 0);
    }, [insights]);

    return (
        <div className="h-full overflow-y-auto p-4 space-y-4 bg-surface-high/10 border-l border-border">
            <div className="flex items-center gap-2">
                <Brain size={16} className="text-accent" />
                <h3 className="font-display text-lg">Document Intelligence</h3>
            </div>

            {loading && (
                <div className="flex items-center gap-2 text-text-muted text-sm">
                    <Loader2 size={14} className="animate-spin" />
                    Running lightweight models on CPU...
                </div>
            )}

            {error && <div className="text-red-400 text-sm">{error}</div>}

            {!loading && insights && (
                <>
                    <div className="rounded-lg border border-border p-3 bg-surface/50">
                        <div className="text-xs font-mono text-text-muted mb-1">DOCUMENT TYPE</div>
                        <div className="text-sm font-medium">{insights.document_type}</div>
                        <div className="text-xs text-text-muted mt-1">Confidence: {(insights.document_type_confidence * 100).toFixed(1)}%</div>
                    </div>

                    <div className="rounded-lg border border-border p-3 bg-surface/50">
                        <div className="flex items-center gap-2 text-xs font-mono text-text-muted mb-2">
                            <FileText size={12} /> SUMMARY
                        </div>
                        <p className="text-sm leading-relaxed">{insights.summary || "No summary generated."}</p>
                    </div>

                    <div className="rounded-lg border border-border p-3 bg-surface/50">
                        <div className="flex items-center gap-2 text-xs font-mono text-text-muted mb-2">
                            <Tags size={12} /> KEYPHRASES
                        </div>
                        <div className="flex flex-wrap gap-2">
                            {insights.keyphrases.slice(0, 12).map((k) => (
                                <span key={k} className="text-xs px-2 py-1 rounded bg-accent/10 text-accent border border-accent/20">
                                    {k}
                                </span>
                            ))}
                        </div>
                    </div>

                    <div className="rounded-lg border border-border p-3 bg-surface/50">
                        <div className="flex items-center justify-between mb-2">
                            <div className="text-xs font-mono text-text-muted">ENTITY SNAPSHOT</div>
                            <div className="text-xs text-text-muted">{entityCount} found</div>
                        </div>
                        <div className="space-y-2">
                            {Object.entries(insights.entities || {})
                                .filter(([, values]) => values.length > 0)
                                .slice(0, 4)
                                .map(([name, values]) => (
                                    <div key={name}>
                                        <div className="text-xs uppercase text-text-muted">{name}</div>
                                        <div className="text-xs text-text-secondary truncate">{values.slice(0, 3).join(", ")}</div>
                                    </div>
                                ))}
                        </div>
                    </div>

                    <div className="rounded-lg border border-border p-3 bg-surface/50">
                        <div className="flex items-center gap-2 text-xs font-mono text-text-muted mb-2">
                            <Search size={12} /> OUTLIER SECTIONS
                        </div>
                        <div className="space-y-2">
                            {insights.outlier_sections.length === 0 && (
                                <div className="text-xs text-text-muted">No unusual sections detected.</div>
                            )}
                            {insights.outlier_sections.map((o) => (
                                <div key={o.section_index} className="text-xs border border-border rounded p-2">
                                    <div className="text-text-muted mb-1">Section #{o.section_index} · score {o.anomaly_score}</div>
                                    <div className="text-text-secondary line-clamp-3">{o.snippet}</div>
                                </div>
                            ))}
                        </div>
                    </div>

                    <div className="rounded-lg border border-border p-3 bg-surface/50">
                        <div className="flex items-center gap-2 text-xs font-mono text-text-muted mb-2">
                            <Sparkles size={12} /> SMART QUESTION STARTERS
                        </div>
                        <ul className="space-y-1 text-xs text-text-secondary">
                            {insights.suggested_questions.map((q) => (
                                <li key={q}>- {q}</li>
                            ))}
                        </ul>
                    </div>
                </>
            )}
        </div>
    );
}
