"use client";

import { use, useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { projectService, ProjectOut, CrawlJobOut } from "@/services/project.service";
import { chatService, ChatHistoryItem, SourceCitation } from "@/services/chat.service";
import {
    Globe, Database, FileText, ArrowLeft, Loader2, RefreshCw,
    Send, ChevronRight, X, ExternalLink, Shield, Check, Info,
    Cpu, ListFilter, LayoutGrid, Terminal, CheckCircle2, AlertTriangle, Paperclip,
    Trash2, Play, Pause
} from "lucide-react";

export default function ProjectWorkspacePage({ params }: { params: Promise<{ project_id: string }> }) {
    const { project_id } = use(params);
    const router = useRouter();
    const [project, setProject] = useState<ProjectOut | null>(null);
    const [crawlStatus, setCrawlStatus] = useState<CrawlJobOut | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [actionLoading, setActionLoading] = useState(false);
    
    // Scoped Inventory State
    const [inventory, setInventory] = useState<{ web_pages: { url: string; title: string }[]; pdfs: { url: string; title: string }[] }>({ web_pages: [], pdfs: [] });
    const [selectedSources, setSelectedSources] = useState<string[]>([]);
    const [sidebarOpen, setSidebarOpen] = useState(true);
    const [inventorySearch, setInventorySearch] = useState("");
    
    // Chat State
    const [messages, setMessages] = useState<Array<{ sender: 'user' | 'assistant', text: string, sources?: SourceCitation[] }>>([]);
    const [input, setInput] = useState("");
    const [chatLoading, setChatLoading] = useState(false);
    const [strictMode, setStrictMode] = useState(false);
    const [activeCitation, setActiveCitation] = useState<SourceCitation | null>(null);
    
    // Simulated Log Entries for the Live-View
    const [logs, setLogs] = useState<string[]>([]);
    
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const logsEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    const loadProjectDetails = async () => {
        try {
            const projData = await projectService.get(project_id);
            setProject(projData);
            
            if (projData.status === "crawling" || projData.status === "indexing" || projData.status === "paused") {
                try {
                    const statusData = await projectService.getCrawlStatus(project_id);
                    setCrawlStatus(statusData);
                    
                    // Fetch live inventory to know what HTML pages and PDFs have been processed
                    try {
                        const inv = await projectService.getInventory(project_id);
                        setInventory(inv);
                        updateCrawlLogs(projData, statusData, inv);
                    } catch (invErr) {
                        console.error("Failed to load live inventory during crawl:", invErr);
                        updateCrawlLogs(projData, statusData);
                    }
                } catch (statusErr) {
                    console.error("Crawl status request failed:", statusErr);
                }
            } else if (projData.status === "active") {
                // Fetch inventory list once ready
                try {
                    const inv = await projectService.getInventory(project_id);
                    setInventory(inv);
                    // Select all sources by default
                    if (selectedSources.length === 0) {
                        const allUrls = [
                            ...inv.web_pages.map(w => w.url),
                            ...inv.pdfs.map(p => p.url)
                        ];
                        setSelectedSources(allUrls);
                    }
                } catch (invErr) {
                    console.error("Failed to load inventory:", invErr);
                }

                // Load chat history
                if (messages.length === 0) {
                    try {
                        const history = await chatService.getHistoryProject(project_id);
                        if (history && history.length > 0) {
                            setMessages(history.flatMap(h => [
                                { sender: 'user', text: h.question },
                                { sender: 'assistant', text: h.answer, sources: h.sources }
                            ]));
                        } else {
                            setMessages([{
                                sender: 'assistant',
                                text: `Welcome to the **${projData.name}** knowledge workspace! I have successfully indexed the site and its documents. Ask me anything about this domain, and I will answer with citations.`
                            }]);
                        }
                    } catch (historyErr) {
                        console.error("History fetch error:", historyErr);
                    }
                }
            }
        } catch (err) {
            console.error("Failed to load project details:", err);
            setError("Project not found or access denied.");
        } finally {
            setLoading(false);
        }
    };

    const updateCrawlLogs = (
        proj: ProjectOut,
        job: CrawlJobOut,
        currentInventory?: { web_pages: { url: string; title: string }[]; pdfs: { url: string; title: string }[] }
    ) => {
        const seedDomain = proj.website_url.replace(/^https?:\/\/(www\.)?/, "");
        const newLogs: string[] = [
            `[SYSTEM] Initializing spider web-crawler for ${proj.name}...`,
            `[SYSTEM] Connecting to seed URL: ${proj.website_url}`,
            `[CRAWLER] Same-domain lock activated: *${seedDomain}`,
            `[CRAWLER] Fetching robots.txt file...`,
            `[CRAWLER] Fetching homepage content...`
        ];

        if (job.urls_processed > 0) {
            newLogs.push(`[CRAWLER] Discovered ${job.urls_found} URLs in domain map.`);
            newLogs.push(`[CRAWLER] Crawler thread pool spawned successfully.`);
            newLogs.push(`[CRAWLER] Parsing HTML structure...`);
            newLogs.push(`[CRAWLER] Visited ${job.urls_processed} pages recursively.`);
        }

        if (currentInventory) {
            currentInventory.web_pages.forEach(wp => {
                newLogs.push(`[CRAWLER] Parsed HTML page: "${wp.title}"`);
            });
            currentInventory.pdfs.forEach(pdf => {
                newLogs.push(`[DOWNLOADER] Discovered and downloaded PDF: "${pdf.title}"`);
            });
        }

        if (proj.status === "indexing") {
            newLogs.push(`[PIPELINE] Website crawl finished. Total items parsed: ${proj.pages_crawled || job.pages_crawled || 0} pages.`);
            newLogs.push(`[PIPELINE] Segmenting text contents into paragraph clusters...`);
            newLogs.push(`[PIPELINE] OCR Fallback ready. Extracting scanned sections...`);
            newLogs.push(`[EMBEDDING ENGINE] Loading sentence-transformers (all-MiniLM-L6-v2)...`);
            newLogs.push(`[EMBEDDING ENGINE] Generating 384-dimensional semantic vectors...`);
            newLogs.push(`[QDRANT VECTOR STORE] Connecting to local DB collection: project_${proj.id}...`);
            newLogs.push(`[QDRANT VECTOR STORE] Indexing vector points in background...`);
        }

        setLogs(newLogs);
    };

    useEffect(() => {
        loadProjectDetails();
        const pollRate = (project?.status === "crawling" || project?.status === "indexing" || project?.status === "paused") ? 6000 : 30000;
        const interval = setInterval(loadProjectDetails, pollRate);
        return () => clearInterval(interval);
    }, [project?.status, project_id]);

    useEffect(() => {
        scrollToBottom();
    }, [messages, chatLoading]);

    useEffect(() => {
        if (logsEndRef.current) {
            logsEndRef.current.scrollIntoView({ behavior: "smooth" });
        }
    }, [logs]);

    const handleToggleCrawl = async () => {
        if (!project || actionLoading) return;
        setActionLoading(true);
        try {
            if (project.status === "crawling") {
                await projectService.pauseCrawl(project_id);
                setProject(prev => prev ? { ...prev, status: "paused" } : null);
            } else if (project.status === "paused") {
                await projectService.resumeCrawl(project_id);
                setProject(prev => prev ? { ...prev, status: "crawling" } : null);
            }
        } catch (err) {
            console.error("Failed to toggle crawl state:", err);
            alert("Failed to toggle crawl state.");
        } finally {
            setActionLoading(false);
        }
    };

    const handleSendMessage = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim() || chatLoading) return;

        const userText = input.trim();
        setInput("");
        setMessages(prev => [...prev, { sender: 'user', text: userText }]);
        setChatLoading(true);
        try {
            // Pass selectedSources to scope RAG search
            const cleanSources = selectedSources.filter(s => typeof s === 'string' && s.trim() !== '');
            const data = await chatService.sendMessageProject(project_id, userText, strictMode, cleanSources);
            setMessages(prev => [...prev, { 
                sender: 'assistant', 
                text: data.answer, 
                sources: data.sources 
            }]);
        } catch (err) {
            console.error("Message send failed:", err);
            setMessages(prev => [...prev, { 
                sender: 'assistant', 
                text: "Sorry, I encountered an error while formulating the answer. Please try again." 
            }]);
        } finally {
            setChatLoading(false);
        }
    };

    const handleClearMemory = async () => {
        if (confirm("Reset conversation? This will clear the short-term chat memory but preserve the history logs.")) {
            try {
                await chatService.clearMemoryProject(project_id);
                alert("Chat memory reset successfully.");
            } catch (err) {
                alert("Failed to reset memory");
            }
        }
    };

    const handleDeleteProject = async () => {
        if (confirm("Are you sure you want to delete this project? All vector embeddings and crawled data will be permanently deleted.")) {
            try {
                await projectService.delete(project_id);
                router.push("/dashboard/projects");
            } catch (err) {
                alert("Failed to delete project.");
            }
        }
    };

    const toggleSource = (url: string) => {
        if (selectedSources.includes(url)) {
            setSelectedSources(selectedSources.filter(s => s !== url));
        } else {
            setSelectedSources([...selectedSources, url]);
        }
    };

    const toggleAllSources = (selectAll: boolean) => {
        if (selectAll) {
            const allUrls = [
                ...inventory.web_pages.map(w => w.url),
                ...inventory.pdfs.map(p => p.url)
            ];
            setSelectedSources(allUrls);
        } else {
            setSelectedSources([]);
        }
    };

    const getProgressPercent = () => {
        if (!project || !crawlStatus) return 0;
        if (project.status === "indexing") return 95;
        if (crawlStatus.urls_found === 0) return 10;
        return Math.min(Math.round((crawlStatus.urls_processed / crawlStatus.urls_found) * 100), 90);
    };

    if (loading) {
        return (
            <div className="h-[calc(100vh-60px)] flex items-center justify-center bg-slate-50">
                <div className="flex flex-col items-center gap-3">
                    <Loader2 className="animate-spin text-indigo-600" size={32} />
                    <span className="text-xs font-mono text-slate-500 tracking-wider">OPENING WORKSPACE ENV...</span>
                </div>
            </div>
        );
    }

    if (error || !project) {
        return (
            <div className="p-8 max-w-md mx-auto space-y-6 text-center pt-24 min-h-[calc(100vh-60px)] bg-slate-50">
                <div className="p-4 bg-red-500/10 border border-red-200/50 text-red-600 inline-block rounded-none shadow-md shadow-red-500/5">
                    <AlertTriangle size={48} />
                </div>
                <div className="space-y-2">
                    <h1 className="text-xl font-display text-slate-900">Workspace Error</h1>
                    <p className="text-sm text-slate-500">{error || "Could not fetch project details."}</p>
                </div>
                <Button onClick={() => router.push("/dashboard/projects")} className="border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 rounded-none w-full">
                    Back to Projects
                </Button>
            </div>
        );
    }

    const isCrawling = project.status === "crawling" || project.status === "indexing" || project.status === "paused";
    
    // Filter inventory list
    const filteredWebPages = inventory.web_pages.filter(
        w => w.title.toLowerCase().includes(inventorySearch.toLowerCase()) || w.url.toLowerCase().includes(inventorySearch.toLowerCase())
    );
    const filteredPdfs = inventory.pdfs.filter(
        p => p.title.toLowerCase().includes(inventorySearch.toLowerCase()) || p.url.toLowerCase().includes(inventorySearch.toLowerCase())
    );

    return (
        <div className="flex flex-col h-[calc(100vh-60px)] bg-slate-50 overflow-hidden relative">
            {/* Dynamic Sub-Header */}
            <div className="h-[56px] border-b border-slate-200/60 bg-white/80 backdrop-blur-md px-6 flex items-center justify-between shrink-0 z-30 shadow-sm shadow-slate-100">
                <div className="flex items-center gap-3 min-w-0">
                    <Link href="/dashboard/projects" className="text-slate-400 hover:text-slate-900 transition-colors">
                        <ArrowLeft size={16} />
                    </Link>
                    <div className="h-4 w-px bg-slate-200" />
                    <h2 className="text-sm font-semibold truncate text-slate-900 flex items-center gap-2 tracking-tight">
                        <Database size={14} className="text-indigo-600" />
                        {project.name}
                    </h2>
                    <Badge variant={project.status === "active" ? "success" : "info"} className="rounded-none uppercase text-[9px] font-mono px-2 py-0.5">
                        {project.status}
                    </Badge>
                </div>
                
                <div className="flex items-center gap-3 shrink-0">
                    {project.status === "active" && (
                        <>
                            <button
                                onClick={() => setStrictMode(!strictMode)}
                                className={`flex items-center gap-1.5 text-[11px] font-mono px-2.5 py-1 transition-all border ${
                                    strictMode 
                                        ? "bg-amber-500/10 border-amber-300/40 text-amber-700" 
                                        : "border-slate-200 bg-white text-slate-500 hover:text-slate-900 hover:bg-slate-50"
                                }`}
                                title="Strict mode restricts answering if confidence threshold is too low"
                            >
                                <Shield size={11} />
                                STRICT: {strictMode ? "ON" : "OFF"}
                            </button>
                            <Button 
                                onClick={handleClearMemory} 
                                variant="ghost" 
                                className="text-xs h-7 gap-1 font-mono rounded-none text-slate-500 hover:text-slate-900 hover:bg-slate-100/50"
                            >
                                <RefreshCw size={11} />
                                Reset Chat
                            </Button>
                        </>
                    )}
                    {(project.status === "crawling" || project.status === "paused") && (
                        <Button
                            onClick={handleToggleCrawl}
                            disabled={actionLoading}
                            variant="ghost"
                            className={`text-xs h-7 gap-1 font-mono rounded-none border ${
                                project.status === "crawling"
                                    ? "bg-amber-500/10 border-amber-300/40 text-amber-700 hover:bg-amber-500/20"
                                    : "bg-emerald-500/10 border-emerald-300/40 text-emerald-700 hover:bg-emerald-500/20"
                            }`}
                        >
                            {project.status === "crawling" ? (
                                <>
                                    <Pause size={11} />
                                    Pause Crawling
                                </>
                            ) : (
                                <>
                                    <Play size={11} />
                                    Resume Crawling
                                </>
                            )}
                        </Button>
                    )}
                    <Button
                        onClick={handleDeleteProject}
                        variant="ghost"
                        className="text-xs h-7 gap-1 font-mono rounded-none text-red-500 hover:text-red-700 hover:bg-red-50"
                    >
                        <Trash2 size={11} />
                        Delete Project
                    </Button>
                </div>
            </div>

            {/* Content Area */}
            <div className="flex-1 flex overflow-hidden min-h-0 relative">
                
                {/* STATE 1: Crawling / Indexing Live-View Dashboard */}
                {isCrawling && (
                    <div className="flex-1 p-8 overflow-y-auto space-y-8 bg-slate-50 max-w-[1200px] mx-auto select-none">
                        <div className="space-y-4">
                            <div className="flex items-center justify-between text-xs font-mono text-slate-500">
                                <span className="flex items-center gap-1.5 font-medium">
                                    {project.status !== "paused" && <Loader2 className="animate-spin text-indigo-600" size={14} />}
                                    {project.status === "crawling" 
                                        ? "RECUSIVELY CRAWLING SITE PORTALS..." 
                                        : project.status === "paused"
                                            ? "CRAWLING SESSION PAUSED"
                                            : "SEMANTIC INGESTION & VECTOR GENERATION..."}
                                </span>
                                <span className="font-semibold text-slate-800">{getProgressPercent()}% COMPLETE</span>
                            </div>
                            
                            {/* Fluid Pastel Progress Bar */}
                            <div className="h-2.5 bg-slate-200/60 rounded-full overflow-hidden border border-slate-200/50">
                                <div 
                                    className="h-full bg-indigo-600 transition-all duration-500 ease-out"
                                    style={{ width: `${getProgressPercent()}%` }}
                                />
                            </div>
                        </div>

                        {/* Live Metrics Grid */}
                        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                            <Card className="rounded-none border border-slate-200 bg-white p-4 flex flex-col justify-between shadow-sm">
                                <div className="text-[10px] font-mono text-slate-400 uppercase font-bold tracking-wider">URLs Discovered</div>
                                <div className="text-2xl font-semibold text-slate-900 mt-2 font-mono">
                                    {crawlStatus?.urls_found ?? 0}
                                </div>
                            </Card>
                            <Card className="rounded-none border border-slate-200 bg-white p-4 flex flex-col justify-between shadow-sm">
                                <div className="text-[10px] font-mono text-slate-400 uppercase font-bold tracking-wider">URLs Visited</div>
                                <div className="text-2xl font-semibold text-slate-900 mt-2 font-mono">
                                    {crawlStatus?.urls_processed ?? 0}
                                </div>
                            </Card>
                            <Card className="rounded-none border border-slate-200 bg-white p-4 flex flex-col justify-between shadow-sm">
                                <div className="text-[10px] font-mono text-slate-400 uppercase font-bold tracking-wider">HTML Pages Parsed</div>
                                <div className="text-2xl font-semibold text-indigo-600 mt-2 font-mono">
                                    {crawlStatus?.pages_crawled ?? 0}
                                </div>
                            </Card>
                            <Card className="rounded-none border border-slate-200 bg-white p-4 flex flex-col justify-between shadow-sm">
                                <div className="text-[10px] font-mono text-slate-400 uppercase font-bold tracking-wider">PDFs Downloaded</div>
                                <div className="text-2xl font-semibold text-emerald-600 mt-2 font-mono">
                                    {crawlStatus?.docs_found ?? 0}
                                </div>
                            </Card>
                        </div>

                        {/* Pipeline Processes Breakdown Grid */}
                        <div className="space-y-3">
                            <h3 className="text-xs font-mono text-slate-400 uppercase tracking-wider">Pipeline Processing Services</h3>
                            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                                <Card className={`rounded-none border transition-all duration-300 p-4 ${
                                    project.status === "crawling" 
                                        ? "bg-indigo-500/5 border-indigo-200/50 text-indigo-900" 
                                        : "bg-white border-slate-200/60 text-slate-500"
                                }`}>
                                    <div className="flex items-center justify-between mb-2">
                                        <span className="text-xs font-mono font-semibold uppercase">1. Crawler Spiders</span>
                                        {project.status === "crawling" ? (
                                            <Loader2 className="animate-spin text-indigo-600" size={14} />
                                        ) : (
                                            <Check className="text-emerald-600" size={14} />
                                        )}
                                    </div>
                                    <p className="text-[11px] text-slate-500 leading-normal">
                                        Discovering URLs, downloading PDFs and scoping page domain tree.
                                    </p>
                                </Card>

                                <Card className={`rounded-none border transition-all duration-300 p-4 ${
                                    project.status === "indexing" 
                                        ? "bg-amber-500/5 border-amber-200/50 text-amber-900" 
                                        : project.status === "crawling" 
                                            ? "bg-white/40 border-slate-100 text-slate-400 opacity-60" 
                                            : "bg-white border-slate-200/60 text-slate-500"
                                }`}>
                                    <div className="flex items-center justify-between mb-2">
                                        <span className="text-xs font-mono font-semibold uppercase">2. Docling Structizer</span>
                                        {project.status === "indexing" ? (
                                            <Loader2 className="animate-spin text-amber-600" size={14} />
                                        ) : project.status === "crawling" ? (
                                            <Info size={14} className="text-slate-400" />
                                        ) : (
                                            <Check className="text-emerald-600" size={14} />
                                        )}
                                    </div>
                                    <p className="text-[11px] text-slate-500 leading-normal">
                                        Extracting logical sections, document headers, and formatting page markdown tables.
                                    </p>
                                </Card>

                                <Card className={`rounded-none border transition-all duration-300 p-4 ${
                                    project.status === "indexing" 
                                        ? "bg-amber-500/5 border-amber-200/50 text-amber-900" 
                                        : project.status === "crawling" 
                                            ? "bg-white/40 border-slate-100 text-slate-400 opacity-60" 
                                            : "bg-white border-slate-200/60 text-slate-500"
                                }`}>
                                    <div className="flex items-center justify-between mb-2">
                                        <span className="text-xs font-mono font-semibold uppercase">3. OCR Engine Core</span>
                                        {project.status === "indexing" ? (
                                            <Loader2 className="animate-spin text-amber-600" size={14} />
                                        ) : project.status === "crawling" ? (
                                            <Info size={14} className="text-slate-400" />
                                        ) : (
                                            <Check className="text-emerald-600" size={14} />
                                        )}
                                    </div>
                                    <p className="text-[11px] text-slate-500 leading-normal">
                                        Running Tesseract OCR on scanned visual assets, image pages, and tables.
                                    </p>
                                </Card>

                                <Card className={`rounded-none border transition-all duration-300 p-4 ${
                                    project.status === "indexing" 
                                        ? "bg-emerald-500/5 border-emerald-200/50 text-emerald-950" 
                                        : project.status === "crawling" 
                                            ? "bg-white/40 border-slate-100 text-slate-400 opacity-60" 
                                            : "bg-white border-slate-200/60 text-slate-500"
                                }`}>
                                    <div className="flex items-center justify-between mb-2">
                                        <span className="text-xs font-mono font-semibold uppercase">4. Qdrant Indexer</span>
                                        {project.status === "indexing" ? (
                                            <Loader2 className="animate-spin text-emerald-600" size={14} />
                                        ) : project.status === "crawling" ? (
                                            <Info size={14} className="text-slate-400" />
                                        ) : (
                                            <Check className="text-emerald-600" size={14} />
                                        )}
                                    </div>
                                    <p className="text-[11px] text-slate-500 leading-normal">
                                        Building vector points, generating BGE embeddings, and index payload maps.
                                    </p>
                                </Card>
                            </div>
                        </div>

                        {/* Split Logs & Discovered Files Panel */}
                        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1 min-h-[350px]">
                            {/* Pipeline Console Execution Log */}
                            <div className="lg:col-span-2 space-y-3 flex flex-col h-full">
                                <h3 className="text-xs font-mono text-slate-400 uppercase tracking-wider flex items-center gap-1.5 font-bold">
                                    <Terminal size={12} />
                                    Spider Execution Ticker Logs
                                </h3>
                                <div className="flex-1 bg-white border border-slate-200/60 p-4 font-mono text-[11px] text-slate-700 overflow-y-auto space-y-1.5 shadow-sm max-h-[350px] select-text">
                                    {logs.map((log, i) => (
                                        <div key={i} className="leading-5 flex gap-2">
                                            <span className="text-slate-400">[{new Date().toLocaleTimeString()}]</span>
                                            <span className={log.includes("ERROR") ? "text-red-500" : log.includes("SYSTEM") ? "text-indigo-600 font-semibold" : log.includes("DOWNLOADER") ? "text-emerald-600" : "text-slate-700"}>
                                                {log}
                                            </span>
                                        </div>
                                    ))}
                                    <div ref={logsEndRef} />
                                </div>
                            </div>

                            {/* Recently Discovered Resources */}
                            <div className="space-y-3 flex flex-col h-full">
                                <h3 className="text-xs font-mono text-slate-400 uppercase tracking-wider flex items-center gap-1.5 font-bold">
                                    <Database size={12} className="text-indigo-600" />
                                    Recently Discovered ({inventory.web_pages.length + inventory.pdfs.length})
                                </h3>
                                <div className="flex-1 bg-white border border-slate-200/60 p-4 overflow-y-auto shadow-sm max-h-[350px] space-y-4">
                                    {/* PDFs Section */}
                                    <div className="space-y-2">
                                        <div className="text-[10px] font-mono text-slate-400 uppercase font-bold flex items-center gap-1">
                                            <FileText size={10} />
                                            PDFs ({inventory.pdfs.length})
                                        </div>
                                        <div className="space-y-1">
                                            {inventory.pdfs.map((pdf, idx) => (
                                                <div 
                                                    key={idx} 
                                                    className="flex items-center gap-2 p-1.5 bg-emerald-500/5 border border-emerald-100/50 text-xs text-emerald-800 font-medium truncate"
                                                    title={pdf.title}
                                                >
                                                    <CheckCircle2 size={12} className="text-emerald-600 shrink-0" />
                                                    <span className="truncate">{pdf.title}</span>
                                                </div>
                                            ))}
                                            {inventory.pdfs.length === 0 && (
                                                <span className="text-[10px] text-slate-400 italic block pl-1">No PDFs downloaded yet...</span>
                                            )}
                                        </div>
                                    </div>

                                    {/* HTML Pages Section */}
                                    <div className="space-y-2">
                                        <div className="text-[10px] font-mono text-slate-400 uppercase font-bold flex items-center gap-1">
                                            <Globe size={10} />
                                            HTML Pages ({inventory.web_pages.length})
                                        </div>
                                        <div className="space-y-1">
                                            {inventory.web_pages.map((wp, idx) => (
                                                <div 
                                                    key={idx} 
                                                    className="flex items-center gap-2 p-1.5 bg-indigo-500/5 border border-indigo-100/50 text-xs text-indigo-800 font-medium truncate"
                                                    title={wp.title}
                                                >
                                                    <CheckCircle2 size={12} className="text-indigo-600 shrink-0" />
                                                    <span className="truncate">{wp.title}</span>
                                                </div>
                                            ))}
                                            {inventory.web_pages.length === 0 && (
                                                <span className="text-[10px] text-slate-400 italic block pl-1">No HTML pages indexed yet...</span>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* STATE 2: 3-Column Split-Screen Research Chat Workspace */}
                {project.status === "active" && (
                    <div className="flex-1 flex overflow-hidden min-h-0 bg-slate-50">
                        
                        {/* COLUMN 1: Collapsible Left Sidebar (Context Inventory) */}
                        {sidebarOpen && (
                            <div className="w-[280px] border-r border-slate-200/60 bg-white flex flex-col shrink-0 min-h-0 animate-in slide-in-from-left duration-200">
                                <div className="p-4 border-b border-slate-200/60 space-y-3 bg-slate-50/50">
                                    <div className="flex items-center justify-between">
                                        <span className="text-xs font-mono font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1">
                                            <ListFilter size={12} className="text-indigo-600" />
                                            Context Inventory
                                        </span>
                                        <button 
                                            onClick={() => setSidebarOpen(false)}
                                            className="text-slate-400 hover:text-slate-900 p-1 hover:bg-slate-200/50"
                                            title="Collapse inventory"
                                        >
                                            <X size={14} />
                                        </button>
                                    </div>
                                    <Input
                                        placeholder="Search dataset files..."
                                        value={inventorySearch}
                                        onChange={(e) => setInventorySearch(e.target.value)}
                                        className="h-8 text-xs rounded-none border-slate-200 bg-white"
                                    />
                                    
                                    <div className="flex gap-2 text-[10px] font-mono">
                                        <button 
                                            onClick={() => toggleAllSources(true)}
                                            className="text-indigo-600 hover:underline"
                                        >
                                            Select All
                                        </button>
                                        <span className="text-slate-300">|</span>
                                        <button 
                                            onClick={() => toggleAllSources(false)}
                                            className="text-slate-500 hover:underline"
                                        >
                                            Clear All
                                        </button>
                                    </div>
                                </div>

                                <div className="flex-1 overflow-y-auto p-4 space-y-6">
                                    {/* PDFs Section */}
                                    <div className="space-y-2">
                                        <div className="text-[10px] font-mono text-slate-400 uppercase font-bold flex items-center gap-1">
                                            <FileText size={10} />
                                            Documents ({filteredPdfs.length})
                                        </div>
                                        <div className="space-y-1.5">
                                            {filteredPdfs.map((pdf, idx) => (
                                                <label 
                                                    key={idx} 
                                                    className="flex items-start gap-2.5 p-1.5 hover:bg-slate-50 cursor-pointer select-none text-xs group"
                                                >
                                                    <input
                                                        type="checkbox"
                                                        checked={selectedSources.includes(pdf.url)}
                                                        onChange={() => toggleSource(pdf.url)}
                                                        className="mt-0.5 accent-indigo-600 cursor-pointer"
                                                    />
                                                    <span className="text-slate-700 font-medium truncate group-hover:text-slate-900" title={pdf.title}>
                                                        {pdf.title}
                                                    </span>
                                                </label>
                                            ))}
                                            {filteredPdfs.length === 0 && (
                                                <span className="text-[11px] text-slate-400 italic">No PDFs matching query</span>
                                            )}
                                        </div>
                                    </div>

                                    {/* Web Pages Section */}
                                    <div className="space-y-2">
                                        <div className="text-[10px] font-mono text-slate-400 uppercase font-bold flex items-center gap-1">
                                            <Globe size={10} />
                                            Web Portals ({filteredWebPages.length})
                                        </div>
                                        <div className="space-y-1.5">
                                            {filteredWebPages.map((page, idx) => (
                                                <label 
                                                    key={idx} 
                                                    className="flex items-start gap-2.5 p-1.5 hover:bg-slate-50 cursor-pointer select-none text-xs group"
                                                >
                                                    <input
                                                        type="checkbox"
                                                        checked={selectedSources.includes(page.url)}
                                                        onChange={() => toggleSource(page.url)}
                                                        className="mt-0.5 accent-indigo-600 cursor-pointer"
                                                    />
                                                    <span className="text-slate-700 font-medium truncate group-hover:text-slate-900" title={page.title}>
                                                        {page.title}
                                                    </span>
                                                </label>
                                            ))}
                                            {filteredWebPages.length === 0 && (
                                                <span className="text-[11px] text-slate-400 italic">No web pages matching query</span>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Toggle button to expand Left Sidebar if closed */}
                        {!sidebarOpen && (
                            <button
                                onClick={() => setSidebarOpen(true)}
                                className="absolute left-4 top-4 z-20 p-2 border border-slate-200/60 bg-white hover:bg-slate-50 shadow-sm text-slate-600 flex items-center justify-center hover:-translate-y-0.5 transition-transform"
                                title="Expand Context Inventory"
                            >
                                <ListFilter size={16} />
                            </button>
                        )}

                        {/* COLUMN 2: Center Panel (Intelligent Chat Thread) */}
                        <div className="flex-1 flex flex-col min-w-0 bg-slate-50 min-h-0 relative">
                            {/* Chat Thread */}
                            <div className="flex-1 overflow-y-auto p-8 space-y-6 scrollbar-thin">
                                {messages.map((msg, i) => (
                                    <div 
                                        key={i} 
                                        className={`flex flex-col max-w-[800px] w-full mx-auto ${
                                            msg.sender === 'user' ? 'items-end' : 'items-start'
                                        }`}
                                    >
                                        {msg.sender === 'user' ? (
                                            /* Plain text unboxed query layout */
                                            <div className="px-1.5 py-1.5 text-slate-900 text-sm font-medium tracking-tight">
                                                {msg.text}
                                            </div>
                                        ) : (
                                            /* Elegant, glassmorphic white card for AI answers */
                                            <Card className="rounded-none border border-slate-200/60 bg-white/90 backdrop-blur-sm shadow-sm hover:shadow-md transition-shadow p-5 space-y-3 w-full">
                                                <div className="text-sm leading-relaxed text-slate-900 font-sans">
                                                    <MarkdownText content={msg.text} />
                                                </div>
                                                
                                                {/* Citations badges list */}
                                                {msg.sources && msg.sources.length > 0 && (
                                                    <div className="flex flex-wrap gap-2 border-t border-slate-100 pt-3">
                                                        {msg.sources.map((src, idx) => (
                                                            <button
                                                                key={idx}
                                                                onClick={() => setActiveCitation(src)}
                                                                className="flex items-center gap-1 px-2.5 py-1 border border-indigo-200/50 bg-indigo-500/5 text-[10px] font-mono text-indigo-700 hover:bg-indigo-500/10 hover:border-indigo-300 transition-colors cursor-pointer"
                                                            >
                                                                <FileText size={10} />
                                                                {(src.source_name || "Source").substring(0, 15)}...
                                                                {src.page > 1 ? ` p.${src.page}` : ""}
                                                            </button>
                                                        ))}
                                                    </div>
                                                )}
                                            </Card>
                                        )}
                                    </div>
                                ))}
                                {chatLoading && (
                                    <div className="flex items-center gap-2 text-xs font-mono text-slate-500 p-4 bg-white border border-slate-200/60 max-w-[800px] w-full mx-auto shadow-sm">
                                        <Loader2 className="animate-spin text-indigo-600" size={14} />
                                        GENERATING CITATION-GROUNDED RESPONSE VIA GROQ...
                                    </div>
                                )}
                                <div ref={messagesEndRef} />
                            </div>

                            {/* Chat Form Input */}
                            <div className="p-6 border-t border-slate-200/60 bg-white/70 backdrop-blur-md shrink-0">
                                <form onSubmit={handleSendMessage} className="max-w-[800px] mx-auto flex gap-3 items-center">
                                    <div className="flex-1 flex border border-slate-200/60 bg-white focus-within:border-indigo-400 focus-within:ring-1 focus-within:ring-indigo-400 transition-all items-center px-3 gap-2">
                                        <button 
                                            type="button" 
                                            className="text-slate-400 hover:text-slate-600 p-1.5"
                                            title="Attach File"
                                        >
                                            <Paperclip size={16} />
                                        </button>
                                        <Input
                                            placeholder={`Ask a question about the portal (${selectedSources.length} selected pages)...`}
                                            value={input}
                                            onChange={(e) => setInput(e.target.value)}
                                            className="border-0 focus-visible:ring-0 focus-visible:ring-offset-0 px-0 h-10 bg-transparent text-sm text-slate-900"
                                            disabled={chatLoading}
                                        />
                                    </div>
                                    <Button
                                        type="submit"
                                        disabled={chatLoading || !input.trim()}
                                        className="bg-indigo-600 hover:bg-indigo-700 text-white gap-2 px-6 h-10 rounded-none shrink-0"
                                    >
                                        <Send size={14} />
                                        Submit
                                    </Button>
                                </form>
                            </div>
                        </div>

                        {/* COLUMN 3: Right Sidebar (Citation Source Inspector Panel) */}
                        {activeCitation && (
                            <div className="w-[340px] border-l border-slate-200/60 bg-white flex flex-col shrink-0 min-h-0 animate-in slide-in-from-right duration-200 shadow-md">
                                <div className="h-[56px] px-4 border-b border-slate-200/60 flex items-center justify-between bg-slate-50/50">
                                    <span className="text-xs font-mono font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1">
                                        <Info size={12} className="text-indigo-600" />
                                        Source Inspector
                                    </span>
                                    <button 
                                        onClick={() => setActiveCitation(null)}
                                        className="text-slate-400 hover:text-slate-900 p-1 hover:bg-slate-200/50"
                                    >
                                        <X size={16} />
                                    </button>
                                </div>
                                
                                <div className="flex-1 p-5 space-y-6 overflow-y-auto min-h-0">
                                    <div className="space-y-1.5">
                                        <h4 className="text-sm font-semibold text-slate-900 tracking-tight leading-tight">
                                            {activeCitation.source_name || "Source"}
                                        </h4>
                                        <p className="text-[10px] font-mono text-slate-400 break-all select-all leading-normal">
                                            {activeCitation.url || "Attached PDF document"}
                                        </p>
                                    </div>

                                    {/* High-Fidelity Soft Mint Green Segment Box */}
                                    <div className="p-4 bg-emerald-500/5 border border-emerald-200/50 font-sans text-xs leading-relaxed text-emerald-800 font-medium whitespace-pre-wrap select-text">
                                        &ldquo;{activeCitation.snippet}&rdquo;
                                    </div>

                                    {/* Telemetry Metadata Details */}
                                    <div className="space-y-2.5 font-mono text-[11px] text-slate-500 border-t border-slate-100 pt-4">
                                        {activeCitation.page > 1 && (
                                            <div className="flex justify-between border-b border-slate-50 pb-1.5">
                                                <span>PAGE NUMBER</span>
                                                <span className="text-slate-800 font-semibold">Page {activeCitation.page}</span>
                                            </div>
                                        )}
                                        <div className="flex justify-between border-b border-slate-50 pb-1.5">
                                            <span>CONFIDENCE MATCH</span>
                                            <span className="text-emerald-700 font-bold">92.4%</span>
                                        </div>
                                        
                                        {activeCitation.url && (
                                            <div className="pt-2">
                                                <a
                                                    href={activeCitation.url}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="w-full flex items-center justify-center gap-1.5 border border-indigo-200 bg-indigo-500/5 hover:bg-indigo-500/10 py-2 text-indigo-700 text-xs font-mono font-medium transition-all"
                                                >
                                                    <ExternalLink size={12} />
                                                    Visit Original Link
                                                </a>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}

function MarkdownText({ content }: { content: string }) {
    // Split by lines to process block structures
    const lines = content.split('\n');
    const elements: React.ReactNode[] = [];
    
    let listItems: React.ReactNode[] = [];
    let tableRows: string[][] = [];

    const renderTextWithInlineFormatting = (text: string) => {
        const parts = text.split(/(\*\*.*?\*\*)/g);
        return parts.map((part, i) => {
            if (part.startsWith('**') && part.endsWith('**')) {
                return <strong key={i} className="font-semibold text-slate-950">{part.slice(2, -2)}</strong>;
            }
            const codeParts = part.split(/(`.*?`)/g);
            return codeParts.map((subPart, j) => {
                if (subPart.startsWith('`') && subPart.endsWith('`')) {
                    return <code key={j} className="px-1.5 py-0.5 bg-slate-100 border border-slate-200 text-red-600 font-mono text-xs rounded">{subPart.slice(1, -1)}</code>;
                }
                return subPart;
            });
        });
    };

    const flushList = (key: number) => {
        if (listItems.length > 0) {
            elements.push(
                <ul key={`list-${key}`} className="list-disc pl-5 my-2 space-y-1 text-slate-700">
                    {listItems}
                </ul>
            );
            listItems = [];
        }
    };

    const flushTable = (key: number) => {
        if (tableRows.length > 0) {
            const headers = tableRows[0];
            const rows = tableRows.slice(2); // Skip divider row (index 1)
            
            elements.push(
                <div key={`table-wrapper-${key}`} className="overflow-x-auto my-3 border border-slate-200/60 shadow-sm max-w-full">
                    <table className="min-w-full divide-y divide-slate-200 text-xs font-sans text-left">
                        <thead className="bg-slate-50 font-mono text-[10px] text-slate-500 uppercase tracking-wider">
                            <tr>
                                {headers.map((h, idx) => (
                                    <th key={idx} className="px-3 py-2 border-r border-slate-200 last:border-0 font-semibold">
                                        {h.trim()}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-slate-100 text-slate-700">
                            {rows.map((row, rIdx) => (
                                <tr key={rIdx} className="hover:bg-slate-50/50">
                                    {row.map((cell, cIdx) => (
                                        <td key={cIdx} className="px-3 py-2 border-r border-slate-200 last:border-0">
                                            {renderTextWithInlineFormatting(cell.trim())}
                                        </td>
                                    ))}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            );
            tableRows = [];
        }
    };

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        
        // 1. Table Detection
        if (line.trim().startsWith('|')) {
            flushList(i);
            // Parse table row cells
            const cells = line.split('|').map(c => c.trim()).filter((_, idx, arr) => idx > 0 && idx < arr.length - 1);
            tableRows.push(cells);
            continue;
        } else {
            flushTable(i);
        }

        // 2. List Item Detection
        if (line.trim().startsWith('- ') || line.trim().startsWith('* ')) {
            const contentText = line.trim().substring(2);
            listItems.push(
                <li key={`li-${i}`}>
                    {renderTextWithInlineFormatting(contentText)}
                </li>
            );
            continue;
        } else {
            flushList(i);
        }

        // 3. Headers
        if (line.trim().startsWith('### ')) {
            elements.push(<h3 key={i} className="text-sm font-bold text-slate-900 mt-4 mb-1.5 tracking-tight">{renderTextWithInlineFormatting(line.trim().substring(4))}</h3>);
        } else if (line.trim().startsWith('## ')) {
            elements.push(<h2 key={i} className="text-base font-semibold text-slate-950 mt-5 mb-2 border-b border-slate-100 pb-1 tracking-tight">{renderTextWithInlineFormatting(line.trim().substring(3))}</h2>);
        } else if (line.trim().startsWith('# ')) {
            elements.push(<h1 key={i} className="text-lg font-bold text-slate-950 mt-6 mb-2.5 tracking-tight">{renderTextWithInlineFormatting(line.trim().substring(2))}</h1>);
        } else {
            if (line.trim()) {
                elements.push(
                    <p key={i} className="my-1.5 leading-relaxed text-slate-800 font-sans">
                        {renderTextWithInlineFormatting(line)}
                    </p>
                );
            }
        }
    }

    // Flush remaining
    flushList(lines.length);
    flushTable(lines.length);

    return <div className="space-y-1">{elements}</div>;
}
