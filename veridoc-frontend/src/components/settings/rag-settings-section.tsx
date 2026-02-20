"use client";

import { useState } from "react";
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export function RagSettingsSection() {
    return (
        <div className="space-y-6">
            <div>
                <h2 className="font-display text-2xl mb-1">Retrieval Configuration</h2>
                <p className="text-text-secondary text-sm">Control how your documents are searched and answered.</p>
            </div>

            {/* Hybrid Search Toggle */}
            <Card className="flex flex-row items-center justify-between p-6">
                <div className="space-y-1">
                    <div className="font-medium text-text-primary">Hybrid Search</div>
                    <div className="text-sm text-text-muted">Combines keyword matching with semantic vector search.</div>
                </div>
                <div className="bg-accent rounded-full p-1 w-12 flex justify-end cursor-pointer">
                    <div className="h-4 w-4 bg-black rounded-full shadow-sm" />
                </div>
            </Card>

            {/* Similarity Threshold */}
            <Card className="p-6 space-y-6">
                <div className="flex justify-between items-center">
                    <div className="space-y-1">
                        <div className="font-medium text-text-primary">Similarity Threshold</div>
                        <div className="text-sm text-text-muted">Minimum relevance match score (0.0 - 1.0).</div>
                    </div>
                    <Badge variant="default" className="text-base px-3 py-1 bg-surface-high">0.75</Badge>
                </div>
                <div className="relative h-2 bg-surface-high rounded-full overflow-hidden">
                    <div className="absolute top-0 left-0 bottom-0 w-[75%] bg-accent rounded-full" />
                </div>
                <div className="flex justify-between text-xs font-mono text-text-muted">
                    <span>Loose (More Results)</span>
                    <span>Strict (Higher Accuracy)</span>
                </div>
            </Card>

            {/* Reranker Config */}
            <Card className="p-6 space-y-4">
                <div className="flex justify-between items-center">
                    <div className="space-y-1">
                        <div className="font-medium text-text-primary">Chunk Limit</div>
                        <div className="text-sm text-text-muted">Number of chunks to feed into the context window.</div>
                    </div>
                    <div className="flex items-center gap-2">
                        <button className="h-8 w-8 rounded bg-surface-high border border-border flex items-center justify-center">-</button>
                        <span className="font-mono w-4 text-center">4</span>
                        <button className="h-8 w-8 rounded bg-surface-high border border-border flex items-center justify-center">+</button>
                    </div>
                </div>
            </Card>
        </div>
    );
}
