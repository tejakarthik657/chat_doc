"use client";

import { useEffect, useState } from "react";
import { TopicClusters } from "@/components/analytics/topic-clusters";
import { FrequencyChart } from "@/components/analytics/frequency-chart";
import { DocumentBreakdown } from "@/components/analytics/document-breakdown";
import { StatsRow } from "@/components/dashboard/stats-row";
import { analyticsService, AnalyticsSummary } from "@/services/analytics.service";

export default function AnalyticsPage() {
    const [stats, setStats] = useState<AnalyticsSummary | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const loadStats = async () => {
            try {
                const data = await analyticsService.getSummary();
                setStats(data);
            } catch (error) {
                console.error("Failed to load analytics:", error);
            } finally {
                setLoading(false);
            }
        };
        loadStats();
    }, []);

    return (
        <div className="p-8 max-w-[1600px] mx-auto min-h-[calc(100vh-60px)]">
            <div className="space-y-8">
                <div className="flex items-center justify-between">
                    <h1 className="font-display text-3xl">Analytics</h1>
                </div>

                <StatsRow
                    totalDocs={stats?.total_questions}
                    totalQueries={stats?.questions_today}
                    storageUsed={stats?.storage_used_mb}
                    loading={loading}
                />

                <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">
                    {/* Left Column (60%) */}
                    <div className="lg:col-span-3 space-y-8">
                        <TopicClusters data={stats?.top_clusters} />
                        <FrequencyChart />
                    </div>

                    {/* Right Column (40%) */}
                    <div className="lg:col-span-2 space-y-8">
                        <DocumentBreakdown />
                    </div>
                </div>
            </div>
        </div>
    );
}
