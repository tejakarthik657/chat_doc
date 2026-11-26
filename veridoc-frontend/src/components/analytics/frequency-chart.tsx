"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { motion } from "framer-motion";

interface QuestionDay {
    day: string;
    count: number;
    isToday: boolean;
}

interface FrequencyChartProps {
    data?: QuestionDay[];
    dailyLimit?: number;
}

export function FrequencyChart({ data = [], dailyLimit = 0 }: FrequencyChartProps) {
    const max = Math.max(dailyLimit, ...data.map((item) => item.count), 1);
    const limitPosition = Math.min((dailyLimit / max) * 100, 100);

    return (
        <Card>
            <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle>Questions Over Time</CardTitle>
                <div className="text-xs font-mono text-text-muted">LAST 7 DAYS</div>
            </CardHeader>
            <CardContent>
                {data.length === 0 ? (
                    <p className="flex h-[200px] items-center justify-center text-sm text-text-muted">
                        No question activity in the last 7 days.
                    </p>
                ) : (
                    <div className="pt-8">
                        <div className="relative flex h-[160px] items-end justify-between gap-2">
                            {dailyLimit > 0 && (
                                <div
                                    className="absolute inset-x-0 z-10 flex justify-end border-t border-dashed border-blue-500/40"
                                    style={{ bottom: `${limitPosition}%` }}
                                >
                                    <span className="-mt-2 bg-surface px-1 text-[10px] font-mono text-blue-500">
                                        DAILY LIMIT ({dailyLimit})
                                    </span>
                                </div>
                            )}
                            {data.map((d, i) => (
                                <div key={d.day} className="group flex h-full flex-1 flex-col items-center">
                                    <div className="relative flex min-h-0 w-full flex-1 items-end justify-center">
                                        <motion.div
                                            initial={{ height: 0 }}
                                            animate={{ height: `${(d.count / max) * 100}%` }}
                                            transition={{ duration: 0.5, delay: i * 0.1 }}
                                            className={`w-2 rounded-t-sm transition-all group-hover:w-3 ${d.isToday ? "bg-accent" : "bg-surface-high"}`}
                                        />
                                        <div className="absolute bottom-full mb-2 rounded border border-border bg-surface-high px-2 py-1 font-mono text-xs opacity-0 transition-opacity group-hover:opacity-100">
                                            {d.count}
                                        </div>
                                    </div>
                                    <span className={`pt-2 text-xs font-mono ${d.isToday ? "text-text-primary" : "text-text-muted"}`}>
                                        {d.day}
                                    </span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
