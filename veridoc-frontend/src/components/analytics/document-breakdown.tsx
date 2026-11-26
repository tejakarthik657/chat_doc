"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

interface DocumentQuestionCount {
    name: string;
    count: number;
}

interface DocumentBreakdownProps {
    docs?: DocumentQuestionCount[];
    storageUsed?: number;
    storageLimit?: number;
}

export function DocumentBreakdown({
    docs = [],
    storageUsed = 0,
    storageLimit = 0,
}: DocumentBreakdownProps) {
    const largestCount = Math.max(...docs.map((doc) => doc.count), 1);
    const storagePercent = storageLimit > 0
        ? Math.min((storageUsed / storageLimit) * 100, 100)
        : 0;

    return (
        <Card className="h-full">
            <CardHeader>
                <CardTitle>Questions by Document</CardTitle>
            </CardHeader>
            <CardContent className="flex h-full flex-col space-y-6">
                {docs.length > 0 ? (
                    docs.map((doc, index) => (
                        <div key={`${doc.name}-${index}`}>
                            <div className="mb-2 flex items-end justify-between gap-3">
                                <span className="max-w-[180px] truncate text-sm font-medium" title={doc.name}>{doc.name}</span>
                                <span className="font-mono text-lg">{doc.count}</span>
                            </div>
                            <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-high">
                                <div
                                    className="h-full rounded-full bg-accent"
                                    style={{ width: `${(doc.count / largestCount) * 100}%` }}
                                />
                            </div>
                        </div>
                    ))
                ) : (
                    <p className="text-sm text-text-muted">No questions have been asked about your sources yet.</p>
                )}

                <div className="mt-auto border-t border-border/70 pt-6">
                    <h4 className="mb-4 font-display text-lg">Storage</h4>
                    <div className="flex items-center gap-4">
                        <div className="h-24 w-24 rounded-full border-4 border-surface-high flex items-center justify-center relative">
                            <svg className="absolute inset-0 -rotate-90" viewBox="0 0 100 100">
                                <circle
                                    cx="50"
                                    cy="50"
                                    r="46"
                                    fill="none"
                                    stroke="currentColor"
                                    className="text-accent"
                                    strokeWidth="8"
                                    strokeDasharray="289"
                                    strokeDashoffset={289 - (289 * storagePercent) / 100}
                                />
                            </svg>
                            <div className="text-center">
                                <div className="text-xs font-mono text-text-secondary">USED</div>
                                <div className="text-sm font-bold">{Math.round(storagePercent)}%</div>
                            </div>
                        </div>
                        <div className="text-sm space-y-1">
                            <p className="font-mono text-accent">{storageUsed.toFixed(1)} MB used</p>
                            <p className="text-xs text-text-muted">
                                {storageLimit > 0 ? `of ${storageLimit.toFixed(1)} MB available` : "Storage limit unavailable"}
                            </p>
                        </div>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}
