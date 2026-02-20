"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

export function DocumentBreakdown() {
    const docs = [
        { name: "clinical_protocols_v2.pdf", count: 145, percent: 80, active: true },
        { name: "project_nebula_specs.pdf", count: 32, percent: 15, active: false },
        { name: "employee_handbook.pdf", count: 12, percent: 5, active: false },
    ];

    return (
        <Card className="h-full">
            <CardHeader>
                <CardTitle>Questions by Document</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
                {docs.map((doc, i) => (
                    <div key={i} className="group cursor-pointer">
                        <div className="flex justify-between items-end mb-2">
                            <div className="flex items-center gap-2">
                                {doc.active && <div className="h-1.5 w-1.5 rounded-full bg-accent animate-pulse" />}
                                <span className="font-medium text-sm truncate max-w-[180px]" title={doc.name}>{doc.name}</span>
                            </div>
                            <span className="font-mono text-lg">{doc.count}</span>
                        </div>

                        <div className="h-1.5 w-full bg-surface-high rounded-full overflow-hidden">
                            <div
                                className={`h-full rounded-full ${doc.active ? "bg-accent" : "bg-surface-high/50 group-hover:bg-text-secondary"}`}
                                style={{ width: `${doc.percent}%` }}
                            />
                        </div>
                    </div>
                ))}

                <div className="pt-8 mt-auto">
                    <h4 className="font-display text-lg mb-4">Storage</h4>
                    <div className="flex items-center gap-4">
                        <div className="h-24 w-24 rounded-full border-4 border-surface-high flex items-center justify-center relative">
                            <svg className="absolute inset-0 -rotate-90" viewBox="0 0 100 100">
                                <circle cx="50" cy="50" r="46" fill="none" stroke="#4ADE80" strokeWidth="8" strokeDasharray="289" strokeDashoffset="200" />
                            </svg>
                            <div className="text-center">
                                <div className="text-xs font-mono text-text-secondary">USED</div>
                                <div className="font-bold text-sm">29%</div>
                            </div>
                        </div>
                        <div className="text-sm space-y-1">
                            <div className="flex justify-between w-32 items-center">
                                <span className="text-text-muted text-xs">Total</span>
                                <span className="font-mono">50 MB</span>
                            </div>
                            <div className="flex justify-between w-32 items-center">
                                <span className="text-text-muted text-xs">Used</span>
                                <span className="font-mono text-accent">14.6 MB</span>
                            </div>
                            <a href="#" className="text-xs text-amber-500 hover:underline block mt-2">Upgrade Storage →</a>
                        </div>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}
