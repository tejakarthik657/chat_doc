"use client";

import Link from "next/link";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { FileText, Trash2, ArrowRight, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import { documentService, DocumentOut } from "@/services/document.service";
import { useSearch } from "@/lib/contexts/search-context";

export function DocumentGrid() {
    const { searchQuery } = useSearch();
    const [documents, setDocuments] = useState<DocumentOut[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchDocs = async (showLoading = true) => {
        if (showLoading) setLoading(true);
        try {
            const data = await documentService.list();
            setDocuments(data.documents);
        } catch (error) {
            console.error(error);
        } finally {
            if (showLoading) setLoading(false);
        }
    };

    useEffect(() => {
        fetchDocs();
    }, []);

    const handleDelete = async (e: React.MouseEvent, docId: string, filename: string) => {
        e.preventDefault();
        e.stopPropagation();
        if (confirm(`Are you sure you want to delete "${filename}"? All associated vectors and chunk metadata will be permanently deleted.`)) {
            try {
                await documentService.delete(docId);
                setDocuments(prev => prev.filter(d => d.id !== docId));
            } catch (err) {
                alert("Failed to delete document.");
            }
        }
    };

    // ── Real-time Status Polling ─────────────────────────────────────────────
    useEffect(() => {
        const hasProcessing = documents.some(doc => doc.status === 'processing');

        if (hasProcessing) {
            const interval = setInterval(() => {
                fetchDocs(false); // Silent refresh
            }, 5000);
            return () => clearInterval(interval);
        }
    }, [documents]);

    const filteredDocuments = documents.filter(doc =>
        doc.filename.toLowerCase().includes(searchQuery.toLowerCase())
    );

    if (loading) {
        return (
            <div className="flex h-40 items-center justify-center">
                <Loader2 className="animate-spin text-accent" />
            </div>
        );
    }

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <h2 className="font-display text-2xl">My Documents</h2>
                <Link href="/dashboard/documents/upload">
                    <Button variant="primary" size="sm">
                        + Upload
                    </Button>
                </Link>
            </div>

            {filteredDocuments.length === 0 ? (
                <div className="border border-dashed border-border rounded-lg p-12 flex flex-col items-center justify-center text-center hover:bg-surface-high/20 transition-colors cursor-pointer group">
                    <Link href="/dashboard/documents/upload">
                        <div className="h-16 w-16 bg-surface-high rounded-full flex items-center justify-center mb-4 group-hover:scale-110 transition-transform mx-auto">
                            <FileText size={32} className="text-text-muted" />
                        </div>
                        <h3 className="font-display text-xl mb-2">
                            {searchQuery ? "No documents match your search." : "Your first document is waiting."}
                        </h3>
                        <p className="text-text-muted text-sm max-w-xs mb-6 mx-auto">
                            {searchQuery ? "Try a different search term or upload a new file." : "Drop a PDF here or click to browse."}
                        </p>
                        <Button variant="primary">{searchQuery ? "Clear Search" : "Upload Document"}</Button>
                    </Link>
                </div>
            ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
                    {filteredDocuments.map((doc) => (
                        <Card key={doc.id} className="group relative overflow-hidden transition-all hover:-translate-y-1 hover:border-accent/50 cursor-pointer">
                            {/* Colored header strip */}
                            <div className={`h-1.5 w-full ${doc.status === 'error' ? 'bg-red-500' :
                                doc.status === 'processing' ? 'bg-amber-500' :
                                    'bg-gradient-to-r from-accent to-blue-500'
                                }`} />

                            <div className="p-4 sm:p-5 space-y-3 sm:space-y-4">
                                <div className="flex justify-between items-start">
                                    <div className="p-2 bg-surface-high rounded text-text-primary">
                                        <FileText size={18} />
                                    </div>
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        className="h-8 w-8 text-text-muted hover:text-red-500 hover:bg-red-50/50 rounded-none transition-colors"
                                        onClick={(e) => handleDelete(e, doc.id, doc.filename)}
                                        title="Delete Document"
                                    >
                                        <Trash2 size={16} />
                                    </Button>
                                </div>

                                <div>
                                    <Link href={doc.status === 'ready' ? `/dashboard/chat/${doc.id}` : '#'}>
                                        <h3 className="font-medium text-base sm:text-lg leading-tight truncate mb-1 hover:text-accent transition-colors" title={doc.filename}>{doc.filename}</h3>
                                    </Link>
                                    <p className="text-[11px] sm:text-xs font-mono text-text-muted">{doc.page_count} pages · {doc.size_mb} MB · {new Date(doc.uploaded_at).toLocaleDateString()}</p>
                                </div>

                                <div className="flex items-center justify-between pt-1 sm:pt-2">
                                    <Badge variant={doc.status as any} className="text-[10px] sm:text-xs">
                                        {doc.status.toUpperCase()}
                                    </Badge>

                                    {doc.status === 'ready' && (
                                        <Link href={`/dashboard/chat/${doc.id}`} className="opacity-100 md:opacity-0 md:group-hover:opacity-100 transition-opacity">
                                            <div className="flex items-center gap-1 text-xs font-mono text-accent hover:underline font-medium">
                                                Ask <ArrowRight size={12} />
                                            </div>
                                        </Link>
                                    )}
                                </div>
                            </div>
                        </Card>
                    ))}
                </div>
            )}
        </div>
    );
}
