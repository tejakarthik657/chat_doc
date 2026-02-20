"use client";

import Link from "next/link";
import { FileText, ChevronLeft, Clock, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { useEffect, useState } from "react";
import { documentService, DocumentOut } from "@/services/document.service";
import { useParams } from "next/navigation";

export function DocumentSidebar({ activeDocId }: { activeDocId: string }) {
    const [documents, setDocuments] = useState<DocumentOut[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchDocs = async () => {
            try {
                const data = await documentService.list();
                setDocuments(data.documents);
            } catch (error) {
                console.error(error);
            } finally {
                setLoading(false);
            }
        };
        fetchDocs();
    }, []);

    return (
        <div className="flex flex-col h-full">
            <div className="p-4 border-b border-border">
                <Link href="/dashboard" className="flex items-center text-sm text-text-muted hover:text-text-primary transition-colors mb-4">
                    <ChevronLeft size={14} className="mr-1" /> Back to Dashboard
                </Link>
                <h2 className="font-display text-lg">Documents</h2>
            </div>

            <div className="flex-1 overflow-y-auto p-2 space-y-1">
                {loading ? (
                    <div className="flex justify-center p-4">
                        <Loader2 className="animate-spin text-text-muted" size={20} />
                    </div>
                ) : (
                    documents.map((doc) => (
                        <Link key={doc.id} href={`/dashboard/chat/${doc.id}`}>
                            <div className={cn(
                                "p-3 rounded-lg cursor-pointer transition-colors border border-transparent",
                                activeDocId === doc.id
                                    ? "bg-surface-high border-border text-text-primary shadow-sm"
                                    : "text-text-secondary hover:bg-surface-high/30 hover:text-text-primary"
                            )}>
                                <div className="flex items-start gap-3">
                                    <FileText size={16} className={cn("mt-1", activeDocId === doc.id ? "text-accent" : "text-text-muted")} />
                                    <div className="min-w-0 flex-1">
                                        <div className="font-medium text-sm truncate" title={doc.filename}>{doc.filename}</div>
                                        <div className="flex items-center justify-between mt-2">
                                            <span className="text-[10px] font-mono text-text-muted">{doc.page_count} pages</span>
                                            <div className={cn("h-1.5 w-1.5 rounded-full", doc.status === 'ready' ? "bg-accent" : "bg-amber-500 animate-pulse")} />
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </Link>
                    ))
                )}
            </div>

            <div className="p-4 border-t border-border mt-auto bg-surface-high/10">
                <div className="flex items-center gap-2 text-xs text-text-muted">
                    <Clock size={12} />
                    <span>History</span>
                </div>
                <div className="text-[10px] font-mono text-text-muted mt-1 truncate">
                    {documents.find(d => d.id === activeDocId)?.filename || "Select a document"}
                </div>
            </div>
        </div>
    );
}
