"use client";

import { useCallback, useEffect, useState } from "react";
import { TopicClusters } from "@/components/analytics/topic-clusters";
import { FrequencyChart } from "@/components/analytics/frequency-chart";
import { DocumentBreakdown } from "@/components/analytics/document-breakdown";
import { StatsRow } from "@/components/dashboard/stats-row";
import { analyticsService, AnalyticsSummary } from "@/services/analytics.service";
import { Button } from "@/components/ui/button";

export default function AnalyticsPage() {
    const [stats, setStats] = useState<AnalyticsSummary | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    const loadStats = useCallback(async (showLoading = true) => {
        if (showLoading) setLoading(true);
        setError("");
        try {
            const data = await analyticsService.getSummary();
            setStats(data);
        } catch {
            setError("Analytics couldn’t be loaded. Check your connection and try again.");
        } finally {
            if (showLoading) setLoading(false);
        }
    }, []);

    useEffect(() => {
        void loadStats();
    }, [loadStats]);

    useEffect(() => {
        const interval = setInterval(() => {
            void loadStats(false);
        }, 10000);
        return () => clearInterval(interval);
    }, [loadStats]);

    return (
        <div className="p-8 max-w-[1600px] mx-auto min-h-[calc(100vh-60px)]">
            <div className="space-y-8">
                <div className="flex items-center justify-between">
                    <h1 className="font-display text-3xl">Analytics</h1>
                </div>

                <StatsRow
                    totalDocs={stats?.total_documents}
                    totalQueries={stats?.total_questions}
                    storageUsed={stats?.storage_used_mb}
                    questionsToday={stats?.questions_today}
                    loading={loading}
                />

                {error && (
                    <div className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-blue-500/30 bg-blue-500/5 p-4 text-sm">
                        <p role="alert">{error}</p>
                        <Button variant="ghost" onClick={() => void loadStats()}>Retry</Button>
                    </div>
                )}

                <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">
                    <div className="lg:col-span-3 space-y-8">
                        <TopicClusters data={stats?.top_clusters} />
                        <FrequencyChart data={stats?.questions_by_day} dailyLimit={stats?.daily_limit} />
                    </div>

                    <div className="lg:col-span-2 space-y-8">
                        <DocumentBreakdown
                            docs={stats?.questions_by_document}
                            storageUsed={stats?.storage_used_mb}
                            storageLimit={stats?.storage_limit_mb}
                        />
                    </div>
                </div>
            </div>
        </div>
    );
}
