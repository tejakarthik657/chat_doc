import { Card } from "@/components/ui/card";
import { FileText, MessageSquare, Database, CheckCircle, Loader2 } from "lucide-react";

interface StatsRowProps {
    totalDocs?: number;
    totalQueries?: number;
    storageUsed?: number;
    loading?: boolean;
}

export function StatsRow({ totalDocs, totalQueries, storageUsed, loading }: StatsRowProps) {
    const stats = [
        { label: "DOCUMENTS INDEXED", value: totalDocs?.toString() ?? "-", icon: FileText },
        { label: "QUERIES TODAY", value: totalQueries?.toString() ?? "-", icon: MessageSquare },
        { label: "STORAGE USED", value: storageUsed ? `${storageUsed.toFixed(1)} MB` : "-", icon: Database },
        { label: "ANSWERS GROUNDED", value: "100%", icon: CheckCircle },
    ];

    if (loading) {
        return (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
                {[1, 2, 3, 4].map(i => (
                    <Card key={i} className="p-4 bg-surface flex items-center justify-center h-[110px]">
                        <Loader2 className="animate-spin text-text-muted" />
                    </Card>
                ))}
            </div>
        )
    }

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
            {stats.map((stat) => (
                <Card key={stat.label} className="p-4 bg-surface flex flex-col justify-between h-[110px]">
                    <div className="flex justify-between items-start">
                        <div className="p-2 rounded bg-surface-high/50 text-text-muted">
                            <stat.icon size={16} />
                        </div>
                        {/* <span className={"text-xs font-mono " + (stat.trend === "up" ? "text-accent" : "text-text-muted")}>
                            {stat.change}
                        </span> */}
                    </div>
                    <div>
                        <div className="font-display text-3xl">{stat.value}</div>
                        <div className="text-[10px] font-mono text-text-muted uppercase tracking-wider">{stat.label}</div>
                    </div>
                </Card>
            ))}
        </div>
    );
}
