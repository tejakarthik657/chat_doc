"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { motion } from "framer-motion";

export function FrequencyChart() {
    const data = [
        { day: "Mon", count: 12 },
        { day: "Tue", count: 18 },
        { day: "Wed", count: 24 },
        { day: "Thu", count: 42, isToday: true },
        { day: "Fri", count: 15 },
        { day: "Sat", count: 8 },
        { day: "Sun", count: 5 },
    ];

    const max = Math.max(...data.map(d => d.count));

    return (
        <Card>
            <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle>Questions Over Time</CardTitle>
                <div className="text-xs font-mono text-text-muted">LAST 7 DAYS</div>
            </CardHeader>
            <CardContent>
                <div className="h-[200px] flex items-end justify-between gap-2 pt-8 relative">
                    {/* Limit Line */}
                    <div className="absolute top-[20%] left-0 right-0 border-t border-dashed border-amber-500/30 flex justify-end">
                        <span className="text-[10px] font-mono text-amber-500 bg-surface -mt-2 px-1">DAILY LIMIT (50)</span>
                    </div>

                    {data.map((d, i) => (
                        <div key={d.day} className="flex flex-col items-center gap-2 flex-1 group">
                            <div className="relative w-full flex justify-center h-full items-end">
                                <motion.div
                                    initial={{ height: 0 }}
                                    animate={{ height: `${(d.count / 50) * 100}%` }}
                                    transition={{ duration: 0.5, delay: i * 0.1 }}
                                    className={`w-2 rounded-t-sm transition-all group-hover:w-3 ${d.isToday ? "bg-accent" : "bg-surface-high"}`}
                                />

                                {/* Tooltip */}
                                <div className="absolute bottom-full mb-2 opacity-0 group-hover:opacity-100 transition-opacity bg-surface-high text-xs font-mono px-2 py-1 rounded border border-border">
                                    {d.count}
                                </div>
                            </div>
                            <span className={`text-xs font-mono ${d.isToday ? "text-text-primary" : "text-text-muted"}`}>
                                {d.day}
                            </span>
                        </div>
                    ))}
                </div>
            </CardContent>
        </Card>
    );
}
