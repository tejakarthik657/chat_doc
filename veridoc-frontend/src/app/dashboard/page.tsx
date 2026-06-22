"use client";

import { useEffect, useState } from "react";
import { StatsRow } from "@/components/dashboard/stats-row";
import { DocumentGrid } from "@/components/dashboard/document-grid";
import { RecentActivity } from "@/components/dashboard/recent-activity";
import { analyticsService, AnalyticsSummary } from "@/services/analytics.service";

export default function DashboardPage() {
    const [stats, setStats] = useState<AnalyticsSummary | null>(null);
    const [loading, setLoading] = useState(true);
    const [syncTime, setSyncTime] = useState("");

    useEffect(() => {
        setSyncTime(new Date().toLocaleTimeString());

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
                        LAST SYNC: {syncTime || "--:--:--"}
                    </div>
                </div>

                {/* Stats */}
                <StatsRow
                    totalDocs={stats?.total_documents}
                    totalQueries={stats?.total_questions}
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
