"use client";

import { useCallback, useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { analyticsService } from "@/services/analytics.service";
import type { AnalyticsSummary } from "@/services/analytics.service";
import { authService } from "@/services/auth.service";
import type { UserOut } from "@/services/auth.service";

function UsageMeter({
    label,
    used,
    limit,
    unit,
}: {
    label: string;
    used: number;
    limit: number;
    unit: string;
}) {
    const percent = limit > 0 ? Math.min((used / limit) * 100, 100) : 0;
    return (
        <div className="space-y-2">
            <div className="flex items-center justify-between gap-4 text-sm">
                <span className="font-medium">{label}</span>
                <span className="font-mono text-text-secondary">
                    {used.toFixed(unit === "MB" ? 1 : 0)} / {limit.toFixed(unit === "MB" ? 1 : 0)} {unit}
                </span>
            </div>
            <div
                className="h-2 overflow-hidden rounded-full bg-surface-high"
                role="progressbar"
                aria-label={label}
                aria-valuenow={Math.min(used, limit)}
                aria-valuemin={0}
                aria-valuemax={limit}
            >
                <div className="h-full rounded-full bg-accent transition-[width]" style={{ width: `${percent}%` }} />
            </div>
        </div>
    );
}

export function UsageLimitsSection() {
    const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
    const [user, setUser] = useState<UserOut | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    const loadUsage = useCallback(async () => {
        setLoading(true);
        setError("");
        try {
            const [analytics, account] = await Promise.all([
                analyticsService.getSummary(),
                authService.getMe(),
            ]);
            setSummary(analytics);
            setUser(account);
        } catch {
            setError("Usage information couldn’t be loaded. Please try again.");
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        void loadUsage();
    }, [loadUsage]);

    return (
        <div className="space-y-6">
            <div>
                <h2 className="mb-1 font-display text-2xl">Usage & limits</h2>
                <p className="text-sm text-text-secondary">See your current plan and live usage against account limits.</p>
            </div>

            {loading ? (
                <p className="text-sm text-text-muted" role="status">Loading usage…</p>
            ) : error ? (
                <Card>
                    <CardContent className="flex flex-wrap items-center justify-between gap-4 p-5">
                        <p className="text-sm text-blue-500" role="alert">{error}</p>
                        <Button variant="ghost" onClick={() => void loadUsage()}>Retry</Button>
                    </CardContent>
                </Card>
            ) : summary && user ? (
                <>
                    <Card>
                        <CardContent className="flex flex-wrap items-center justify-between gap-4 p-5 sm:p-6">
                            <div>
                                <p className="text-xs font-mono uppercase tracking-wider text-text-muted">Current plan</p>
                                <p className="mt-1 font-display text-2xl">{user.plan}</p>
                            </div>
                            <p className="max-w-md text-sm leading-relaxed text-text-secondary">
                                Limits shown here come from your account and current plan.
                            </p>
                        </CardContent>
                    </Card>

                    <Card>
                        <CardContent className="space-y-7 p-5 sm:p-6">
                            <UsageMeter
                                label="Questions today"
                                used={summary.questions_today}
                                limit={summary.daily_limit}
                                unit="questions"
                            />
                            <UsageMeter
                                label="Storage used"
                                used={summary.storage_used_mb}
                                limit={summary.storage_limit_mb}
                                unit="MB"
                            />
                            <div className="flex items-center justify-between border-t border-border pt-5 text-sm">
                                <span className="text-text-secondary">Indexed documents</span>
                                <span className="font-mono">{summary.total_documents}</span>
                            </div>
                        </CardContent>
                    </Card>
                </>
            ) : (
                <p className="text-sm text-text-muted">Usage information is not available.</p>
            )}
        </div>
    );
}
