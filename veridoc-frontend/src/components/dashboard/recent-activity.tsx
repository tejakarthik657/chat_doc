import Link from "next/link";
import { Clock } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { RecentActivityItem } from "@/services/analytics.service";

interface RecentActivityProps {
    data?: RecentActivityItem[];
}

export function RecentActivity({ data = [] }: RecentActivityProps) {
    return (
        <div className="w-full bg-surface-high/20 border border-border rounded-lg p-4 h-full">
            <div className="flex items-center gap-2 mb-4 text-text-muted uppercase tracking-wider text-xs font-mono">
                <Clock size={14} />
                <span>Recent Questions</span>
            </div>

            <div className="space-y-4">
                {data.length === 0 ? (
                    <div className="text-center text-text-muted text-xs py-10 font-mono">No recent activity</div>
                ) : (
                    data.map((item) => (
                        <div key={item.id} className="group cursor-pointer hover:bg-surface-high/40 p-2 rounded -mx-2 transition-colors">
                            <div className="text-sm text-text-primary line-clamp-2 mb-1 group-hover:text-accent transition-colors">
                                {item.question}
                            </div>
                            <div className="flex items-center justify-between">
                                <div className="text-[10px] font-mono text-text-muted truncate max-w-[120px]">
                                    {item.document_filename}
                                </div>
                                <div className="text-[10px] text-text-muted">
                                    {formatDistanceToNow(new Date(item.timestamp), { addSuffix: true })}
                                </div>
                            </div>
                            <div className="mt-1 flex gap-1">
                                <span className="text-[10px] px-1 bg-surface-high text-text-muted border border-border rounded">
                                    {item.citation_count} citations
                                </span>
                            </div>
                        </div>
                    ))
                )}
            </div>

            <Link href="/dashboard/history" className="block mt-6 text-center text-xs font-mono text-text-muted hover:text-accent transition-colors border-t border-border pt-3">
                View All History →
            </Link>
        </div>
    );
}
