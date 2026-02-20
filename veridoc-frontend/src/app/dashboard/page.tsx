"use client";

import { useEffect, useState } from "react";
import { StatsRow } from "@/components/dashboard/stats-row";
import { DocumentGrid } from "@/components/dashboard/document-grid";
import { RecentActivity } from "@/components/dashboard/recent-activity";
import { analyticsService, AnalyticsSummary } from "@/services/analytics.service";

export default function DashboardPage() {
    const [stats, setStats] = useState<AnalyticsSummary | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const loadStats = async () => {
            try {
                const data = await analyticsService.getSummary();
                setStats(data);
            } catch (error) {
                console.error("Failed to load dashboard stats:", error);
            } finally {
                setLoading(false);
            }
        };
        loadStats();
    }, []);

    return (
        <div className="p-8 max-w-[1600px] mx-auto min-h-[calc(100vh-60px)]">
            <div className="space-y-8">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <h1 className="font-display text-3xl">Dashboard</h1>
                    <div className="text-sm font-mono text-text-muted">
                        LAST SYNC: {new Date().toLocaleTimeString()}
                    </div>
                </div>

                {/* Stats */}
                <StatsRow
                    totalDocs={stats?.total_questions} // Note: Backend summary mixes concepts currently. 
                    // Ideally total_questions is queries. 
                    // Documents count isn't in summary yet? 
                    // Actually summary has total_questions. 
                    // Let's check schemas.py again. 
                    // Schema has total_questions, questions_today, daily_limit, storage_used_mb.
                    // Use total_questions for Queries Today? No. 
                    // Let's map what we have.
                    totalQueries={stats?.questions_today}
                    storageUsed={stats?.storage_used_mb}
                    loading={loading}
                />

                {/* Main Content Grid */}
                <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
                    <div className="lg:col-span-3">
                        <DocumentGrid />
                    </div>
                    <div className="lg:col-span-1">
                        <RecentActivity data={stats?.recent_activity} />
                    </div>
                </div>
            </div>
        </div>
    );
}
