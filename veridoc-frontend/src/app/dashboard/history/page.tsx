"use client";

import { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { 
    Clock, Search, FileText, ArrowLeft, ArrowUpRight, MessageSquare, 
    Sparkles, Filter, RefreshCw, Loader2, CheckCircle2, Database
} from "lucide-react";
import { formatDistanceToNow, format } from "date-fns";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { analyticsService, RecentActivityItem, AnalyticsSummary } from "@/services/analytics.service";

export default function HistoryPage() {
    const [stats, setStats] = useState<AnalyticsSummary | null>(null);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState("");
    const [selectedDoc, setSelectedDoc] = useState<string>("all");

    const loadData = async () => {
        setLoading(true);
        try {
            const data = await analyticsService.getSummary();
            setStats(data);
        } catch (error) {
            console.error("Failed to load history data:", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadData();
    }, []);

    const recentActivity = stats?.recent_activity || [];

    // Distinct document names for filtering
    const documentOptions = useMemo(() => {
        const docs = new Set<string>();
        recentActivity.forEach(item => {
            if (item.document_filename) docs.add(item.document_filename);
        });
        return Array.from(docs);
    }, [recentActivity]);

    // Filtered questions
    const filteredActivity = useMemo(() => {
        return recentActivity.filter(item => {
            const matchesSearch = 
                item.question.toLowerCase().includes(searchQuery.toLowerCase()) ||
                item.document_filename.toLowerCase().includes(searchQuery.toLowerCase());
            const matchesDoc = selectedDoc === "all" || item.document_filename === selectedDoc;
            return matchesSearch && matchesDoc;
        });
    }, [recentActivity, searchQuery, selectedDoc]);

    return (
        <div className="p-8 max-w-[1400px] mx-auto min-h-[calc(100vh-60px)]">
            <div className="space-y-6">
                {/* Header Navigation */}
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div>
                        <Link href="/dashboard">
                            <Button variant="ghost" size="sm" className="pl-0 hover:pl-2 transition-all text-text-muted hover:text-text-primary mb-2">
                                <ArrowLeft className="mr-2 h-4 w-4" /> Back to Dashboard
                            </Button>
                        </Link>
                        <h1 className="font-display text-3xl font-bold flex items-center gap-3">
                            <Clock className="h-7 w-7 text-accent" />
                            Activity & Query History
                        </h1>
                        <p className="text-text-secondary text-sm mt-1">
                            Comprehensive audit trail of questions, citations, and RAG retrieval sessions.
                        </p>
                    </div>

                    <div className="flex items-center gap-3">
                        <Button 
                            variant="outline" 
                            size="sm" 
                            onClick={loadData} 
                            disabled={loading}
                            className="gap-2 text-xs font-mono"
                        >
                            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
                            Refresh
                        </Button>
                    </div>
                </div>

                {/* Quick Metrics */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <div className="bg-surface/50 border border-border rounded-xl p-4 flex items-center gap-4">
                        <div className="h-10 w-10 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center text-accent">
                            <MessageSquare className="h-5 w-5" />
                        </div>
                        <div>
                            <div className="text-xs font-mono text-text-muted uppercase tracking-wider">Total Questions</div>
                            <div className="text-2xl font-bold text-text-primary">{stats?.total_questions || 0}</div>
                        </div>
                    </div>

                    <div className="bg-surface/50 border border-border rounded-xl p-4 flex items-center gap-4">
                        <div className="h-10 w-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
                            <Sparkles className="h-5 w-5" />
                        </div>
                        <div>
                            <div className="text-xs font-mono text-text-muted uppercase tracking-wider">Today's Queries</div>
                            <div className="text-2xl font-bold text-emerald-400">{stats?.questions_today || 0}</div>
                        </div>
                    </div>

                    <div className="bg-surface/50 border border-border rounded-xl p-4 flex items-center gap-4">
                        <div className="h-10 w-10 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
                            <Database className="h-5 w-5" />
                        </div>
                        <div>
                            <div className="text-xs font-mono text-text-muted uppercase tracking-wider">Indexed Documents</div>
                            <div className="text-2xl font-bold text-cyan-400">{stats?.total_documents || 0}</div>
                        </div>
                    </div>
                </div>

                {/* Filters & Search */}
                <div className="bg-surface/40 border border-border rounded-xl p-4 flex flex-col md:flex-row gap-4 items-center justify-between">
                    <div className="relative w-full md:w-96">
                        <Search className="absolute left-3 top-2.5 h-4 w-4 text-text-muted" />
                        <Input
                            placeholder="Search questions or document names..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="pl-9 bg-background/50 border-border text-sm"
                        />
                    </div>

                    {documentOptions.length > 0 && (
                        <div className="flex items-center gap-2 w-full md:w-auto overflow-x-auto pb-1 md:pb-0">
                            <span className="text-xs font-mono text-text-muted flex items-center gap-1 shrink-0">
                                <Filter className="h-3 w-3" /> Filter:
                            </span>
                            <button
                                onClick={() => setSelectedDoc("all")}
                                className={`text-xs px-2.5 py-1 rounded-full border transition-colors shrink-0 font-mono ${
                                    selectedDoc === "all"
                                        ? "bg-accent/20 border-accent text-accent font-medium"
                                        : "bg-surface border-border text-text-muted hover:text-text-primary"
                                }`}
                            >
                                All
                            </button>
                            {documentOptions.map((doc) => (
                                <button
                                    key={doc}
                                    onClick={() => setSelectedDoc(doc)}
                                    className={`text-xs px-2.5 py-1 rounded-full border transition-colors shrink-0 font-mono truncate max-w-[180px] ${
                                        selectedDoc === doc
                                            ? "bg-accent/20 border-accent text-accent font-medium"
                                            : "bg-surface border-border text-text-muted hover:text-text-primary"
                                    }`}
                                >
                                    {doc}
                                </button>
                            ))}
                        </div>
                    )}
                </div>

                {/* History Content */}
                <div className="bg-surface/30 border border-border rounded-xl overflow-hidden">
                    {loading ? (
                        <div className="flex flex-col items-center justify-center py-20 text-text-muted">
                            <Loader2 className="h-8 w-8 animate-spin text-accent mb-3" />
                            <p className="text-sm font-mono">Loading activity history...</p>
                        </div>
                    ) : filteredActivity.length === 0 ? (
                        <div className="text-center py-20 px-4">
                            <Clock className="h-12 w-12 text-text-muted/40 mx-auto mb-3" />
                            <h3 className="font-semibold text-lg text-text-primary mb-1">
                                {searchQuery ? "No matching queries found" : "No query history recorded yet"}
                            </h3>
                            <p className="text-text-secondary text-sm max-w-md mx-auto mb-6">
                                {searchQuery 
                                    ? "Try adjusting your search terms or clearing the filter."
                                    : "Upload medical documents or crawl a knowledge base to begin asking clinical questions."
                                }
                            </p>
                            <div className="flex justify-center gap-3">
                                <Link href="/dashboard/documents">
                                    <Button size="sm" className="gap-2">
                                        <FileText className="h-4 w-4" /> Go to Documents
                                    </Button>
                                </Link>
                                <Link href="/dashboard/projects">
                                    <Button variant="outline" size="sm" className="gap-2">
                                        <Database className="h-4 w-4" /> Go to Knowledge Projects
                                    </Button>
                                </Link>
                            </div>
                        </div>
                    ) : (
                        <div className="divide-y divide-border">
                            {filteredActivity.map((item) => (
                                <div 
                                    key={item.id} 
                                    className="p-4 hover:bg-surface-high/30 transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-4"
                                >
                                    <div className="space-y-1.5 flex-1 min-w-0">
                                        <div className="flex items-center gap-2">
                                            <span className="text-sm font-medium text-text-primary">
                                                {item.question}
                                            </span>
                                        </div>
                                        <div className="flex flex-wrap items-center gap-3 text-xs text-text-muted font-mono">
                                            <span className="flex items-center gap-1 text-accent">
                                                <FileText className="h-3 w-3" />
                                                <span className="truncate max-w-[200px]">{item.document_filename}</span>
                                            </span>
                                            <span>•</span>
                                            <span>
                                                {formatDistanceToNow(new Date(item.timestamp), { addSuffix: true })}
                                            </span>
                                            {item.citation_count > 0 && (
                                                <>
                                                    <span>•</span>
                                                    <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] bg-accent/10 text-accent border border-accent/20">
                                                        {item.citation_count} citation{item.citation_count !== 1 ? 's' : ''}
                                                    </span>
                                                </>
                                            )}
                                        </div>
                                    </div>

                                    <div className="shrink-0 flex items-center gap-2">
                                        <Link href="/dashboard/documents">
                                            <Button variant="ghost" size="sm" className="h-8 gap-1.5 text-xs text-text-muted hover:text-accent">
                                                <span>View Chat</span>
                                                <ArrowUpRight className="h-3.5 w-3.5" />
                                            </Button>
                                        </Link>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
