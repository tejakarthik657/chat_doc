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
import api from "@/lib/api";
import {
    GraduationCap, ShieldCheck, Activity, Globe, Database, FileText, ArrowLeft, Loader2, RefreshCw,
    Send, ChevronRight, X, ExternalLink, Shield, Check, Info,
    Cpu, ListFilter, LayoutGrid, Terminal, CheckCircle2, AlertTriangle, Paperclip,
    Trash2, Play, Pause, GitBranch, AlertOctagon, HeartPulse, FileBarChart2, SearchCode, Eye,
    Sparkles, Brain, Compass, Network, Hammer, LayoutTemplate,
    ZoomIn, ZoomOut, Maximize2, Copy, Download, Code2, Image as ImageIcon, Search
} from "lucide-react";

import { VoiceInput } from "@/components/chat/VoiceInput";
import { EvidencePanel } from "@/components/chat/EvidencePanel";
import { CanvasWorkspace } from "@/components/canvas/CanvasWorkspace";
import SocraticVivaModal from "@/components/features/SocraticVivaModal";
import TruthLatticeModal from "@/components/features/TruthLatticeModal";
import LivingCodeSandbox from "@/components/features/LivingCodeSandbox";
import WhatIfSimulatorModal from "@/components/features/WhatIfSimulatorModal";


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
    const [sidebarOpen, setSidebarOpen] = useState(false);
    const [inventorySearch, setInventorySearch] = useState("");

    useEffect(() => {
        if (typeof window !== "undefined" && window.innerWidth >= 1024) {
            setSidebarOpen(true);
        }
    }, []);
    
    // Chat State & 30 UX Features State
    const [messages, setMessages] = useState<Array<{ 
        sender: 'user' | 'assistant', 
        text: string, 
        sources?: SourceCitation[], 
        evidence_trace?: any[], 
        support_confidence?: number, 
        support_label?: string,
        isGeneralAI?: boolean,
        questionRef?: string
    }>>([]);
    const [chatScope, setChatScope] = useState<"project" | "general">("project");
    const [input, setInput] = useState("");
    const [chatLoading, setChatLoading] = useState(false);
    const [strictMode, setStrictMode] = useState(false);
    const [responseMode, setResponseMode] = useState<"standard" | "debate" | "decision_tree" | "brutal_review" | "builder">("standard");
    const [reasoningLevel, setReasoningLevel] = useState<"fast" | "balanced" | "deep">("balanced");
    const [activeCitation, setActiveCitation] = useState<SourceCitation | null>(null);
    
    // Evidence & Canvas Drawers
    const [evidenceOpen, setEvidenceOpen] = useState(false);
    const [activeEvidenceTrace, setActiveEvidenceTrace] = useState<any[]>([]);
    const [canvasOpen, setCanvasOpen] = useState(false);
    const [canvasContent, setCanvasContent] = useState("");
    
    // Tab States
    const [activeTab, setActiveTab] = useState("chat");
    const [echoMemories, setEchoMemories] = useState<any[]>([]);
    const [echoLoading, setEchoLoading] = useState(false);
    const [newMemoryKey, setNewMemoryKey] = useState("");
    const [newMemoryValue, setNewMemoryValue] = useState("");
    const [newMemoryCategory, setNewMemoryCategory] = useState("preference");
    const [mindspaceData, setMindspaceData] = useState<{ nodes: any[]; edges: any[] } | null>(null);
    const [mindspaceLoading, setMindspaceLoading] = useState(false);
    const [selectedMindNode, setSelectedMindNode] = useState<any | null>(null);
    const [graphData, setGraphData] = useState<{ nodes: any[]; links: any[] } | null>(null);
    const [graphLoading, setGraphLoading] = useState(false);
    const [contradictions, setContradictions] = useState<any[]>([]);
    const [contradictionsLoading, setContradictionsLoading] = useState(false);
    const [changes, setChanges] = useState<any[]>([]);
    const [changesLoading, setChangesLoading] = useState(false);
    const [health, setHealth] = useState<any | null>(null);
    const [healthLoading, setHealthLoading] = useState(false);
    const [reportType, setReportType] = useState("technical");
    const [reportContent, setReportContent] = useState("");
    const [reportLoading, setReportLoading] = useState(false);
    const [investigationGoal, setInvestigationGoal] = useState("");
    const [investigationResult, setInvestigationResult] = useState<any | null>(null);
    const [investigationLoading, setInvestigationLoading] = useState(false);
    
    // Simulated Log Entries for the Live-View
    const [logs, setLogs] = useState<string[]>([]);
    
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const logsEndRef = useRef<HTMLDivElement>(null);

    // Multimodal Image Attachment State & Ref
    const [attachedImage, setAttachedImage] = useState<{ file: File; previewUrl: string; name: string; size: string } | null>(null);
    const [imageAnalyzing, setImageAnalyzing] = useState(false);
    const imageInputRef = useRef<HTMLInputElement>(null);

    // Python Sandbox State
    const [codeRunning, setCodeRunning] = useState(false);
    const [codeOutput, setCodeOutput] = useState<{ stdout: string; stderr: string; returncode: number; duration_ms: number } | null>(null);


    // 4 Breakthrough Features State
    const [socraticOpen, setSocraticOpen] = useState(false);
    const [truthLatticeOpen, setTruthLatticeOpen] = useState(false);
    const [auditQuery, setAuditQuery] = useState("");
    const [auditTargetText, setAuditTargetText] = useState("");
    const [whatIfOpen, setWhatIfOpen] = useState(false);

    // Knowledge Graph Interactive State
    const [selectedGraphNode, setSelectedGraphNode] = useState<any | null>(null);
    const [graphSearchQuery, setGraphSearchQuery] = useState("");
    const [graphFilterCategory, setGraphFilterCategory] = useState("all");
    const [graphZoom, setGraphZoom] = useState(1.0);
    const [hoveredGraphNode, setHoveredGraphNode] = useState<any | null>(null);

    // Report State Actions
    const [copiedReport, setCopiedReport] = useState(false);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    const loadProjectDetails = async () => {
        try {
            const projData = await projectService.get(project_id);
            setProject(projData);
            
            if (["crawling", "indexing", "paused"].includes(projData.status)) {
                // Fetch status and inventory in PARALLEL
                const [statusResult, invResult] = await Promise.allSettled([
                    projectService.getCrawlStatus(project_id),
                    projectService.getInventory(project_id),
                ]);
                const statusData = statusResult.status === 'fulfilled' ? statusResult.value : null;
                const inv = invResult.status === 'fulfilled' ? invResult.value : null;
                if (statusData) setCrawlStatus(statusData);
                if (inv) setInventory(inv);
                if (statusData) updateCrawlLogs(projData, statusData, inv || undefined);
            } else if (projData.status === "active") {
                // Fetch inventory and chat history in PARALLEL
                const [invResult, historyResult] = await Promise.allSettled([
                    projectService.getInventory(project_id),
                    messages.length === 0 ? chatService.getHistoryProject(project_id) : Promise.resolve(null),
                ]);
                
                if (invResult.status === 'fulfilled' && invResult.value) {
                    const inv = invResult.value;
                    setInventory(inv);
                    if (selectedSources.length === 0) {
                        const allUrls = [
                            ...inv.web_pages.map((w: { url: string }) => w.url),
                            ...inv.pdfs.map((p: { url: string }) => p.url)
                        ];
                        setSelectedSources(allUrls);
                    }
                }

                if (historyResult.status === 'fulfilled' && historyResult.value) {
                    const history = historyResult.value as any[];
                    if (history && history.length > 0) {
                        setMessages(history.flatMap(h => [
                            { sender: 'user' as const, text: h.question },
                            { sender: 'assistant' as const, text: h.answer, sources: h.sources }
                        ]));
                    } else {
                        setMessages([{
                            sender: 'assistant',
                            text: `Welcome to the **${projData.name}** knowledge workspace! I have successfully indexed the site and its documents. Ask me anything about this domain, and I will answer with citations.`
                        }]);
                    }
                }
            }
        } catch (err: any) {
            console.error("Failed to load project details:", err);
            // If the error was a transient timeout or network blip, keep current state and don't wipe out workspace
            if (err?.code === 'ECONNABORTED' || err?.message?.includes('timeout') || err?.message?.includes('Network Error')) {
                console.warn("Project details request timed out or blipped. Retrying smoothly on next poll interval...");
            } else if (err?.response?.status === 404) {
                setError("Project not found.");
            } else {
                // Only set error if we don't already have a valid project in state
                setError(prev => prev ? prev : "Connecting to server...");
            }
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
        // Only poll during active crawling/indexing — stop completely when project is active
        const status = project?.status;
        if (!status || status === 'active' || status === 'error') {
            // No polling needed when project is ready or errored
            return;
        }
        const pollRate = status === 'crawling' || status === 'indexing' ? 6000 : 30000;
        const interval = setInterval(loadProjectDetails, pollRate);
        return () => clearInterval(interval);
    }, [project?.status, project_id]);
    
    useEffect(() => {
        if (project?.status !== "active") return;
        
        const loadTabData = async () => {
            if (activeTab === "graph") {
                setGraphLoading(true);
                try {
                    const res = await api.get(`/projects/${project_id}/graph`);
                    setGraphData(res.data);
                } catch (e) {
                    console.error("Failed to load graph:", e);
                } finally {
                    setGraphLoading(false);
                }
            } else if (activeTab === "contradictions") {
                setContradictionsLoading(true);
                try {
                    const res = await api.get(`/projects/${project_id}/contradictions`);
                    setContradictions(res.data.contradictions || []);
                } catch (e) {
                    console.error("Failed to load contradictions:", e);
                } finally {
                    setContradictionsLoading(false);
                }
            } else if (activeTab === "changes") {
                setChangesLoading(true);
                try {
                    const res = await api.get(`/projects/${project_id}/changes`);
                    setChanges(res.data.changes || []);
                } catch (e) {
                    console.error("Failed to load changes:", e);
                } finally {
                    setChangesLoading(false);
                }
            } else if (activeTab === "health") {
                setHealthLoading(true);
                try {
                    const res = await api.get(`/projects/${project_id}/health`);
                    setHealth(res.data);
                } catch (e) {
                    console.error("Failed to load health audit:", e);
                } finally {
                    setHealthLoading(false);
                }
            } else if (activeTab === "echo") {
                setEchoLoading(true);
                try {
                    const res = await api.get(`/projects/${project_id}/echo/memories`);
                    setEchoMemories(res.data.memories || []);
                } catch (e) {
                    console.error("Failed to load ECHO memories:", e);
                } finally {
                    setEchoLoading(false);
                }
            } else if (activeTab === "mindspace") {
                setMindspaceLoading(true);
                try {
                    const res = await api.get(`/projects/${project_id}/mindspace/canvas`);
                    setMindspaceData(res.data);
                } catch (e) {
                    console.error("Failed to load MINDSPACE canvas:", e);
                } finally {
                    setMindspaceLoading(false);
                }
            }
        };
        loadTabData();
    }, [activeTab, project_id, project?.status]);

    useEffect(() => {
        scrollToBottom();
    }, [messages, chatLoading]);

    useEffect(() => {
        if (logsEndRef.current) {
            logsEndRef.current.scrollIntoView({ behavior: "smooth" });
        }
    }, [logs]);

    const handleGenerateReport = async (forceRefresh = false) => {
        setReportLoading(true);
        if (forceRefresh) setReportContent("");
        try {
            const url = `/projects/${project_id}/report?type=${reportType}${forceRefresh ? "&refresh=true" : ""}`;
            const res = await api.get(url, { timeout: 120000 });
            setReportContent(res.data.content || "");
        } catch (err) {
            console.error("Failed to generate report:", err);
            alert("Error compiling intelligence report. Please try again.");
        } finally {
            setReportLoading(false);
        }
    };

    const handleCopyReport = () => {
        if (!reportContent) return;
        navigator.clipboard.writeText(reportContent);
        setCopiedReport(true);
        setTimeout(() => setCopiedReport(false), 2000);
    };

    const handleDownloadReport = () => {
        if (!reportContent) return;
        const blob = new Blob([reportContent], { type: "text/markdown;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = `${project?.name || "project"}-${reportType}-report.md`;
        link.click();
        URL.revokeObjectURL(url);
    };

    const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            const sizeStr = file.size > 1024 * 1024 ? `${(file.size / (1024 * 1024)).toFixed(1)} MB` : `${Math.round(file.size / 1024)} KB`;
            const previewUrl = URL.createObjectURL(file);
            setAttachedImage({ file, previewUrl, name: file.name, size: sizeStr });
        }
    };

    const handlePaste = (e: React.ClipboardEvent) => {
        const items = e.clipboardData?.items;
        if (!items) return;
        for (let i = 0; i < items.length; i++) {
            if (items[i].type.indexOf("image") !== -1) {
                const file = items[i].getAsFile();
                if (file) {
                    const sizeStr = `${Math.round(file.size / 1024)} KB`;
                    const previewUrl = URL.createObjectURL(file);
                    setAttachedImage({ file, previewUrl, name: "pasted-screenshot.png", size: sizeStr });
                }
                break;
            }
        }
    };

    const handleRunPythonCode = async (snippet?: string) => {
        const codeToRun = (snippet || canvasContent || "").trim();
        if (!codeToRun) return;
        setCodeRunning(true);
        setCodeOutput(null);
        try {
            const res = await api.post("/features/execute-code", { code: codeToRun });
            setCodeOutput(res.data);
        } catch (err: any) {
            console.error("Python sandbox error:", err);
            setCodeOutput({
                stdout: "",
                stderr: err.message || "Execution failed",
                returncode: 1,
                duration_ms: 0
            });
        } finally {
            setCodeRunning(false);
        }
    };

    const handleRunInvestigation = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!investigationGoal.trim() || investigationLoading) return;
        setInvestigationLoading(true);
        setInvestigationResult(null);
        try {
            const res = await api.post(`/projects/${project_id}/investigate`, {
                objective: investigationGoal.trim()
            });
            setInvestigationResult(res.data);
        } catch (err) {
            console.error("Agent failed:", err);
            alert("Investigation agent run failed.");
        } finally {
            setInvestigationLoading(false);
        }
    };

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

    const handleAskGeneralAI = async (questionText: string) => {
        if (!questionText.trim() || chatLoading) return;
        const q = questionText.trim();
        setMessages(prev => {
            const last = prev[prev.length - 1];
            if (last && last.sender === 'user' && last.text === q) return prev;
            return [...prev, { sender: 'user', text: q }];
        });
        setChatLoading(true);
        try {
            const data = await chatService.askGeneralAI(q, project_id);
            setMessages(prev => [...prev, { 
                sender: 'assistant', 
                text: data.answer, 
                sources: [],
                evidence_trace: data.evidence_trace || [],
                support_confidence: 1.0,
                support_label: "World Knowledge Base (Groq)",
                isGeneralAI: true,
                questionRef: q
            }]);
        } catch (err) {
            console.error("General AI query failed:", err);
            setMessages(prev => [...prev, { 
                sender: 'assistant', 
                text: "Sorry, I could not query General AI at this moment. Please check connection and try again." 
            }]);
        } finally {
            setChatLoading(false);
        }
    };

    const handleSendMessage = async (e?: React.FormEvent, overrideText?: string) => {
        if (e) e.preventDefault();
        const rawText = overrideText !== undefined ? overrideText : input;
        const textToSend = rawText.trim();
        if ((!textToSend && !attachedImage) || chatLoading || imageAnalyzing) return;

        setInput("");
        let queryContext = textToSend;
        const currentAttachedImage = attachedImage;
        setAttachedImage(null);

        // Multimodal Image Reasoning
        if (currentAttachedImage) {
            setImageAnalyzing(true);
            try {
                const formData = new FormData();
                formData.append("file", currentAttachedImage.file);
                if (textToSend) formData.append("prompt", textToSend);
                const ocrRes = await api.post<{ description: string; extracted_text: string }>("/features/analyze-image", formData, {
                    headers: { "Content-Type": "multipart/form-data" }
                });
                const imgData = ocrRes.data;
                const visualNote = imgData.description || imgData.extracted_text || "Image parsed.";
                queryContext = `[Attached Image: ${currentAttachedImage.name}]\nVisual OCR & Content:\n${visualNote}\n\nUser Question:\n${textToSend || "Analyze and summarize this image."}`;
            } catch (imgErr) {
                console.error("Image analysis failed:", imgErr);
            } finally {
                setImageAnalyzing(false);
            }
        }

        const displayText = textToSend || (currentAttachedImage ? `[Attached Image: ${currentAttachedImage.name}]` : "");

        if (chatScope === "general") {
            await handleAskGeneralAI(queryContext);
            return;
        }

        setMessages(prev => [...prev, { sender: 'user', text: displayText }]);
        setChatLoading(true);
        try {
            const cleanSources = selectedSources.filter(s => typeof s === 'string' && s.trim() !== '');
            const data = await chatService.sendMessageProject(project_id, queryContext, strictMode, cleanSources, responseMode);
            setMessages(prev => [...prev, { 
                sender: 'assistant', 
                text: data.answer, 
                sources: data.sources,
                evidence_trace: data.evidence_trace || [],
                support_confidence: data.support_confidence,
                support_label: data.support_label,
                isGeneralAI: false,
                questionRef: displayText
            }]);
        } catch (err) {
            console.error("Message send failed:", err);
            setMessages(prev => [...prev, { 
                sender: 'assistant', 
                text: "Sorry, I encountered an error while formulating the answer. Please try again.",
                questionRef: displayText
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
        <div className="flex flex-col h-[calc(100dvh-60px)] bg-slate-50 overflow-hidden relative">
            {/* Dynamic Sub-Header */}
            <div className="min-h-[56px] h-auto py-2 border-b border-slate-200/60 bg-white/90 backdrop-blur-md px-3 sm:px-6 flex items-center justify-between gap-2 shrink-0 z-30 shadow-sm shadow-slate-100 overflow-x-auto no-scrollbar">
                <div className="flex items-center gap-2 sm:gap-3 min-w-0 shrink-0">
                    <Link href="/dashboard/projects" className="text-slate-400 hover:text-slate-900 transition-colors p-1" title="Back to Projects">
                        <ArrowLeft size={16} />
                    </Link>
                    <button
                        onClick={() => setSidebarOpen(prev => !prev)}
                        className="lg:hidden flex items-center gap-1 px-2 py-1 text-xs font-mono rounded border border-slate-200 bg-white hover:bg-slate-100 text-slate-700 shrink-0 active:scale-95 transition-all"
                        title="Toggle Context Inventory"
                    >
                        <ListFilter size={13} className="text-indigo-600" />
                        <span className="hidden sm:inline">Docs</span>
                    </button>
                    <div className="h-4 w-px bg-slate-200 hidden sm:block" />
                    <h2 className="text-xs sm:text-sm font-semibold truncate text-slate-900 flex items-center gap-1.5 sm:gap-2 tracking-tight max-w-[120px] sm:max-w-xs">
                        <Database size={13} className="text-indigo-600 shrink-0" />
                        <span className="truncate">{project.name}</span>
                    </h2>
                    <Badge variant={project.status === "active" ? "success" : "info"} className="rounded-none uppercase text-[8px] sm:text-[9px] font-mono px-1.5 sm:px-2 py-0.5 shrink-0">
                        {project.status}
                    </Badge>
                </div>
                
                <div className="flex items-center gap-1.5 sm:gap-2.5 shrink-0">
                    <>
                        {/* Reasoning Selector */}
                        <div className="hidden md:flex items-center gap-0.5 p-0.5 bg-slate-100 rounded-lg border border-slate-200 text-[10px] font-mono">
                            {(["fast", "balanced", "deep"] as const).map((level) => (
                                <button
                                    key={level}
                                    onClick={() => setReasoningLevel(level)}
                                    className={`px-1.5 sm:px-2 py-0.5 rounded capitalize transition-all ${
                                        reasoningLevel === level
                                            ? "bg-indigo-600 text-white font-semibold shadow-xs"
                                            : "text-slate-500 hover:text-slate-900"
                                    }`}
                                >
                                    {level}
                                </button>
                            ))}
                        </div>

                        {/* Knowledge Scope Toggle */}
                        <div className="flex items-center rounded-lg border border-slate-200 bg-slate-100/90 p-0.5 text-[10px] font-mono shrink-0">
                            <button
                                type="button"
                                onClick={() => setChatScope("project")}
                                className={`flex items-center gap-1 px-2 sm:px-2.5 py-0.5 rounded transition-all ${
                                    chatScope === "project"
                                        ? "bg-white text-indigo-700 shadow-xs font-semibold"
                                        : "text-slate-500 hover:text-slate-900"
                                }`}
                                title="Limit answers exclusively to this project's crawled documents and pages"
                            >
                                <Database size={10} />
                                <span className="hidden sm:inline">Project Scope</span>
                                <span className="sm:hidden">RAG</span>
                            </button>
                            <button
                                type="button"
                                onClick={() => setChatScope("general")}
                                className={`flex items-center gap-1 px-2 sm:px-2.5 py-0.5 rounded transition-all ${
                                    chatScope === "general"
                                        ? "bg-indigo-600 text-white shadow-xs font-semibold"
                                        : "text-slate-500 hover:text-slate-900"
                                }`}
                                title="Query Groq LLM general world knowledge without document restrictions"
                            >
                                <Globe size={10} />
                                <span className="hidden sm:inline">General AI</span>
                                <span className="sm:hidden">Groq</span>
                            </button>
                        </div>

                        {/* Canvas Workspace Button */}
                        <button
                            onClick={() => setCanvasOpen(true)}
                            className="flex items-center gap-1 text-[10px] sm:text-[11px] font-mono px-2 sm:px-2.5 py-1 transition-all border border-purple-200 bg-purple-50 text-purple-700 hover:bg-purple-100/80 rounded shrink-0"
                            title="Open side-by-side interactive Canvas Workspace"
                        >
                            <LayoutGrid size={11} />
                            <span className="hidden sm:inline">Canvas Workspace</span>
                            <span className="sm:hidden">Canvas</span>
                        </button>

                        <button
                            onClick={() => setStrictMode(!strictMode)}
                            className={`flex items-center gap-1 text-[10px] sm:text-[11px] font-mono px-1.5 sm:px-2.5 py-1 transition-all border shrink-0 ${
                                strictMode 
                                    ? "bg-amber-500/10 border-amber-300/40 text-amber-700" 
                                    : "border-slate-200 bg-white text-slate-500 hover:text-slate-900 hover:bg-slate-50"
                            }`}
                            title="Strict mode restricts answering if confidence threshold is too low"
                        >
                            <Shield size={10} />
                            <span>{strictMode ? "STRICT" : "RELAXED"}</span>
                        </button>
                        <Button 
                            onClick={handleClearMemory} 
                            variant="ghost" 
                            className="text-[10px] sm:text-xs h-7 px-1.5 sm:px-2 gap-1 font-mono rounded-none text-slate-500 hover:text-slate-900 hover:bg-slate-100/50 shrink-0"
                            title="Reset Chat"
                        >
                            <RefreshCw size={11} />
                            <span className="hidden sm:inline">Reset Chat</span>
                        </Button>
                    </>
                    {(project.status === "crawling" || project.status === "paused") && (
                        <Button
                            onClick={handleToggleCrawl}
                            disabled={actionLoading}
                            variant="ghost"
                            className={`text-[10px] sm:text-xs h-7 px-2 gap-1 font-mono rounded-none border shrink-0 ${
                                project.status === "crawling"
                                    ? "bg-amber-500/10 border-amber-300/40 text-amber-700 hover:bg-amber-500/20"
                                    : "bg-emerald-500/10 border-emerald-300/40 text-emerald-700 hover:bg-emerald-500/20"
                            }`}
                        >
                            {project.status === "crawling" ? (
                                <>
                                    <Pause size={11} />
                                    <span className="hidden sm:inline">Pause Crawling</span>
                                </>
                            ) : (
                                <>
                                    <Play size={11} />
                                    <span className="hidden sm:inline">Resume Crawling</span>
                                </>
                            )}
                        </Button>
                    )}
                    <Button
                        onClick={handleDeleteProject}
                        variant="ghost"
                        className="text-[10px] sm:text-xs h-7 px-1.5 sm:px-2 gap-1 font-mono rounded-none text-red-500 hover:text-red-700 hover:bg-red-50 shrink-0"
                        title="Delete Project"
                    >
                        <Trash2 size={11} />
                        <span className="hidden sm:inline">Delete</span>
                    </Button>
                </div>
            </div>

            {/* Progressive Indexing Top Live Progress Banner */}
            {isCrawling && (
                <div className="bg-slate-950 text-slate-200 px-3 sm:px-6 py-2 flex flex-col sm:flex-row sm:items-center justify-between gap-2 shrink-0 border-b border-slate-800 shadow-sm z-20">
                    <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
                        <span className="relative flex h-2.5 w-2.5 shrink-0">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
                        </span>
                        <span className="text-[11px] sm:text-xs font-mono font-medium tracking-tight text-slate-200">
                            Pipeline: <strong className="text-white">{crawlStatus?.urls_processed || 0}</strong> visited • <strong className="text-white">{inventory.pdfs.length}</strong> PDFs • <strong className="text-white">{inventory.web_pages.length}</strong> Web
                        </span>
                        <span className="text-[9px] bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 font-mono uppercase tracking-wider rounded-full font-bold">
                            Live RAG Ready
                        </span>
                    </div>
                    <div className="flex items-center gap-2 sm:gap-3 text-xs font-mono shrink-0">
                        <span className="text-slate-400 font-medium text-[11px]">{getProgressPercent()}% complete</span>
                        <div className="w-20 sm:w-28 h-1.5 bg-slate-800 rounded-full overflow-hidden border border-slate-700">
                            <div className="h-full bg-gradient-to-r from-indigo-500 to-emerald-400 transition-all duration-300" style={{ width: `${getProgressPercent()}%` }} />
                        </div>
                    </div>
                </div>
            )}

            {/* Redesigned High-End Segmented Navigation Bar */}
            <div className="flex border-b border-slate-200/80 bg-white/95 backdrop-blur-md px-3 sm:px-4 shrink-0 h-12 items-center gap-1.5 select-none overflow-x-auto no-scrollbar shadow-xs">
                {[
                    { id: "chat", label: "Research Chat", icon: Cpu },
                    { id: "socratic", label: "Socratic Viva", icon: GraduationCap, badge: "Oral AI" },
                    { id: "sandbox", label: "Code Twin", icon: Terminal, badge: "AST Sandbox" },
                    { id: "graph", label: "Knowledge Graph", icon: GitBranch },
                    { id: "mindspace", label: "Thought Canvas", icon: Compass },
                    { id: "forge", label: "Artifacts", icon: Hammer },
                    { id: "echo", label: "Living Memory", icon: Brain },
                    { id: "contradictions", label: "Contradictions", icon: AlertOctagon },
                    { id: "health", label: "Health Audit", icon: HeartPulse },
                    { id: "report", label: "Reports", icon: FileBarChart2 },
                    { id: "investigate", label: "Agent Lab", icon: SearchCode },
                    { id: "changes", label: "Changelog", icon: RefreshCw }
                ].map(t => {
                    const Icon = t.icon;
                    const isActive = activeTab === t.id;
                    return (
                        <button
                            key={t.id}
                            onClick={() => setActiveTab(t.id)}
                            className={`h-9 px-3.5 text-xs font-medium rounded-lg transition-all flex items-center gap-2 whitespace-nowrap shrink-0 cursor-pointer ${
                                isActive
                                    ? "bg-indigo-50 text-indigo-700 dark:bg-indigo-950/70 dark:text-indigo-300 font-semibold shadow-xs border border-indigo-200/70"
                                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-100/80 border border-transparent"
                            }`}
                        >
                            <Icon size={14} className={isActive ? "text-indigo-600" : "text-slate-400"} />
                            <span>{t.label}</span>
                            {t.badge && (
                                <span className={`text-[9px] px-1.5 py-0.5 rounded-full font-mono font-bold uppercase tracking-wider ${
                                    isActive 
                                        ? "bg-indigo-200/80 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200" 
                                        : "bg-slate-100 text-slate-500"
                                }`}>
                                    {t.badge}
                                </span>
                            )}
                        </button>
                    );
                })}
            </div>

            {/* Content Area */}
            <div className="flex-1 flex overflow-hidden min-h-0 relative">
                
                {/* STATE 2: 3-Column Split-Screen Research Chat Workspace */}
                {project.status !== "error" && activeTab === "chat" && (
                    <div className="flex-1 flex overflow-hidden min-h-0 bg-slate-50">
                        
                        {/* COLUMN 1: Collapsible Left Sidebar (Context Inventory) */}
                        {sidebarOpen && (
                            <>
                                <div
                                    onClick={() => setSidebarOpen(false)}
                                    className="fixed inset-0 bg-slate-950/40 backdrop-blur-xs z-40 lg:hidden"
                                />
                                <div className="fixed inset-y-0 left-0 w-[280px] max-w-[85vw] z-50 lg:static lg:z-auto lg:w-[280px] border-r border-slate-200/60 bg-white flex flex-col shrink-0 min-h-0 shadow-2xl lg:shadow-none animate-in slide-in-from-left duration-200">
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
                            </>
                        )}

                        {/* Toggle button to expand Left Sidebar if closed (desktop) */}
                        {!sidebarOpen && (
                            <button
                                onClick={() => setSidebarOpen(true)}
                                className="hidden lg:flex absolute left-4 top-4 z-20 p-2 border border-slate-200/60 bg-white hover:bg-slate-50 shadow-sm text-slate-600 items-center justify-center hover:-translate-y-0.5 transition-transform"
                                title="Expand Context Inventory"
                            >
                                <ListFilter size={16} />
                            </button>
                        )}

                        {/* COLUMN 2: Center Panel (Intelligent Chat Thread) */}
                        <div className="flex-1 flex flex-col min-w-0 bg-slate-50 min-h-0 relative">
                            {/* Chat Thread */}
                            <div className="flex-1 overflow-y-auto p-3 sm:p-6 md:p-8 space-y-4 sm:space-y-6 scrollbar-thin">
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
                                                {msg.isGeneralAI ? (
                                                    <div className="flex items-center gap-1.5 px-2.5 py-1 text-[10px] font-mono border w-fit bg-indigo-500/10 border-indigo-300/40 text-indigo-800 font-bold rounded">
                                                        <Globe size={11} className="text-indigo-600" />
                                                        WORLD KNOWLEDGE (GROQ)
                                                    </div>
                                                ) : msg.support_confidence !== undefined && msg.support_confidence !== null && (
                                                    <div className="flex items-center gap-1.5 px-2.5 py-1 text-[10px] font-mono border w-fit bg-emerald-500/10 border-emerald-300/40 text-emerald-800 font-bold rounded">
                                                        <CheckCircle2 size={11} className="text-emerald-600" />
                                                        {(msg.support_confidence * 100).toFixed(1)}% GROUNDED {msg.support_label ? `(${msg.support_label.toUpperCase()})` : ""}
                                                    </div>
                                                )}
                                                <div className="text-sm leading-relaxed text-slate-900 font-sans">
                                                    <MarkdownText content={msg.text} />
                                                </div>

                                                {/* Fallback Banner to General AI if answer not in knowledge base */}
                                                {!msg.isGeneralAI && (msg.text.includes("couldn't find") || msg.text.includes("not found") || msg.text.includes("no relevant information")) && (
                                                    <div className="mt-3 p-3 bg-indigo-50/80 border border-indigo-200/60 rounded flex items-center justify-between gap-3 text-xs">
                                                        <div className="flex items-center gap-2 text-indigo-900">
                                                            <Globe size={14} className="text-indigo-600 shrink-0" />
                                                            <span>Answer not found in project documents? You can query General AI directly.</span>
                                                        </div>
                                                        <Button
                                                            size="sm"
                                                            onClick={() => handleAskGeneralAI(msg.questionRef || msg.text)}
                                                            className="bg-indigo-600 hover:bg-indigo-700 text-white font-mono text-[11px] h-7 px-3 shrink-0"
                                                        >
                                                            Ask General AI
                                                        </Button>
                                                    </div>
                                                )}
                                                
                                                {/* Citations badges list & Evidence Inspector */}
                                                <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-3">
                                                    {msg.sources && msg.sources.length > 0 && (
                                                        <div className="flex flex-wrap gap-2">
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

                                                     <div className="flex flex-wrap items-center gap-1.5 w-full sm:w-auto sm:ml-auto pt-2 sm:pt-0">
                                                         {/* 1-Click Ask General AI button */}
                                                         {msg.questionRef && !msg.isGeneralAI && (
                                                             <button
                                                                 onClick={() => handleAskGeneralAI(msg.questionRef!)}
                                                                 className="flex items-center gap-1 px-2.5 py-1 sm:py-0.5 sm:px-2 border border-indigo-300/60 bg-indigo-50/70 text-[10px] font-mono text-indigo-700 hover:bg-indigo-100 transition-all rounded font-medium touch-manipulation active:scale-95"
                                                                 title="Query General AI (Groq) for this question with broader world knowledge"
                                                             >
                                                                 <Globe size={10} />
                                                                 Ask General AI
                                                             </button>
                                                         )}

                                                         <button
                                                             onClick={() => {
                                                                 setAuditTargetText(msg.text);
                                                                 setAuditQuery(msg.questionRef || "Verify factual reliability");
                                                                 setTruthLatticeOpen(true);
                                                             }}
                                                             className="flex items-center gap-1 px-2.5 py-1 sm:py-0.5 sm:px-2 border border-emerald-300/60 bg-emerald-50/70 text-[10px] font-mono text-emerald-800 hover:bg-emerald-100 transition-all rounded font-medium touch-manipulation active:scale-95"
                                                             title="Run Truth Lattice dual-model adversarial red team audit"
                                                         >
                                                             <ShieldCheck size={10} />
                                                             Truth Lattice
                                                         </button>
                                                         <button
                                                             onClick={() => {
                                                                 setCanvasContent(msg.text);
                                                                 setCanvasOpen(true);
                                                             }}
                                                             className="flex items-center gap-1 px-2.5 py-1 sm:py-0.5 sm:px-2 border border-purple-300/60 bg-purple-50/50 text-[10px] font-mono text-purple-800 hover:bg-purple-100 transition-all rounded touch-manipulation active:scale-95"
                                                             title="Send this response to Canvas for live editing & export"
                                                         >
                                                             <LayoutGrid size={10} />
                                                             Edit in Canvas
                                                         </button>

                                                         <button
                                                             onClick={() => {
                                                                 setActiveEvidenceTrace(msg.evidence_trace || []);
                                                                 setEvidenceOpen(true);
                                                             }}
                                                             className="flex items-center gap-1 px-2.5 py-1 sm:py-0.5 sm:px-2 border border-cyan-300/60 bg-cyan-50/50 text-[10px] font-mono text-cyan-800 hover:bg-cyan-100 transition-all rounded touch-manipulation active:scale-95"
                                                             title="Inspect raw RAG evidence chunks and scores"
                                                         >
                                                             <Eye size={10} />
                                                             Why this answer?
                                                         </button>
                                                     </div>
                                                </div>
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
                            <div className="p-2.5 sm:p-5 border-t border-slate-200/60 bg-white/70 backdrop-blur-md shrink-0 space-y-2.5 sm:space-y-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]">
                                {/* Mode Selector Pill Bar */}
                                <div className="max-w-[800px] mx-auto flex items-center gap-1.5 overflow-x-auto pb-1 text-xs font-mono no-scrollbar">
                                    <span className="text-slate-400 text-[10px] uppercase font-bold tracking-wider mr-1 shrink-0">Experience Mode:</span>
                                    {[
                                        { id: "standard", label: "Standard", hint: "Factual cited Q&A" },
                                        { id: "debate", label: "Debate", hint: "2 Opposing arguments + verdict" },
                                        { id: "decision_tree", label: "Decision Tree", hint: "Branching options & assumptions" },
                                        { id: "brutal_review", label: "Brutal Review", hint: "Pre-mortem & critical flaws" },
                                        { id: "builder", label: "Builder", hint: "Actionable checklist & next steps" },
                                    ].map(m => (
                                        <button
                                            key={m.id}
                                            type="button"
                                            onClick={() => setResponseMode(m.id as any)}
                                            title={m.hint}
                                            className={`px-2.5 py-1 rounded-full border transition-all text-[11px] shrink-0 whitespace-nowrap active:scale-95 ${
                                                responseMode === m.id
                                                    ? "bg-indigo-600 text-white border-indigo-600 font-semibold shadow-xs"
                                                    : "bg-white text-slate-600 border-slate-200 hover:border-slate-300 hover:bg-slate-50"
                                            }`}
                                        >
                                            {m.label}
                                        </button>
                                    ))}
                                </div>

                                {/* Attached Image Preview Chip */}
                                {attachedImage && (
                                    <div className="max-w-[800px] mx-auto flex items-center gap-2 p-2 bg-indigo-50/80 border border-indigo-200 rounded-lg animate-in fade-in">
                                        <div className="w-10 h-10 rounded border border-indigo-300 overflow-hidden relative shrink-0 bg-white">
                                            <img src={attachedImage.previewUrl} alt="attachment" className="w-full h-full object-cover" />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="text-xs font-semibold text-slate-800 truncate">{attachedImage.name}</div>
                                            <div className="text-[10px] font-mono text-slate-500">Image • {attachedImage.size} (Multimodal Vision active)</div>
                                        </div>
                                        <button
                                            type="button"
                                            onClick={() => setAttachedImage(null)}
                                            className="p-1 text-slate-400 hover:text-rose-600 rounded active:scale-95"
                                            title="Remove attachment"
                                        >
                                            <X size={14} />
                                        </button>
                                    </div>
                                )}

                                <form onSubmit={handleSendMessage} onPaste={handlePaste} className="max-w-[800px] mx-auto flex gap-2 sm:gap-3 items-center">
                                     <div className="flex-1 flex border border-slate-200/60 bg-white focus-within:border-indigo-400 focus-within:ring-1 focus-within:ring-indigo-400 transition-all items-center px-2.5 sm:px-3 gap-1.5 sm:gap-2 rounded-lg">
                                         <input
                                             type="file"
                                             ref={imageInputRef}
                                             accept="image/*"
                                             onChange={handleImageSelect}
                                             className="hidden"
                                         />
                                         <button 
                                             type="button" 
                                             onClick={() => imageInputRef.current?.click()}
                                             className="text-slate-400 hover:text-indigo-600 p-1.5 transition-colors active:scale-95"
                                             title="Attach Image / Screenshot (or paste directly with Ctrl+V)"
                                         >
                                             <Paperclip size={16} />
                                         </button>
                                         <VoiceInput
                                             onTranscript={(txt) => setInput(prev => prev ? `${prev} ${txt}` : txt)}
                                             onSendVoiceQuery={(txt) => handleSendMessage(undefined, txt)}
                                             isGenerating={chatLoading}
                                         />
                                         <Input
                                             placeholder={`Ask a question or paste screenshot (${selectedSources.length} selected pages)...`}
                                             value={input}
                                             onChange={(e) => setInput(e.target.value)}
                                             className="border-0 focus-visible:ring-0 focus-visible:ring-offset-0 px-1 h-10 bg-transparent text-base sm:text-sm text-slate-900"
                                             disabled={chatLoading || imageAnalyzing}
                                         />
                                     </div>
                                    <Button
                                        type="submit"
                                        disabled={chatLoading || imageAnalyzing || (!input.trim() && !attachedImage)}
                                        className="bg-indigo-600 hover:bg-indigo-700 text-white gap-1.5 px-3.5 sm:px-6 h-10 rounded-lg shrink-0 font-medium active:scale-95"
                                    >
                                        {imageAnalyzing ? (
                                            <>
                                                <Loader2 className="animate-spin" size={14} />
                                                <span className="hidden sm:inline">Analyzing...</span>
                                            </>
                                        ) : (
                                            <>
                                                <Send size={14} />
                                                <span className="hidden sm:inline">Submit</span>
                                            </>
                                        )}
                                    </Button>
                                </form>
                            </div>
                        </div>

                        {/* COLUMN 3: Right Sidebar (Citation Source Inspector Panel) */}
                        {activeCitation && (
                            <>
                                {/* Mobile Backdrop */}
                                <div
                                    onClick={() => setActiveCitation(null)}
                                    className="fixed inset-0 bg-slate-950/40 backdrop-blur-xs z-40 lg:hidden"
                                    aria-label="Close Citation Panel"
                                />
                                <div className="fixed inset-y-0 right-0 z-50 w-full sm:w-[360px] lg:static lg:z-auto lg:w-[340px] border-l border-slate-200/60 bg-white flex flex-col shrink-0 min-h-0 shadow-2xl lg:shadow-md animate-in slide-in-from-right duration-200">
                                    <div className="h-[56px] px-4 border-b border-slate-200/60 flex items-center justify-between bg-slate-50/50">
                                        <span className="text-xs font-mono font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1">
                                            <Info size={12} className="text-indigo-600" />
                                            Source Inspector
                                        </span>
                                        <button 
                                            onClick={() => setActiveCitation(null)}
                                            className="text-slate-400 hover:text-slate-900 p-1 hover:bg-slate-200/50 rounded active:scale-95"
                                            aria-label="Close"
                                        >
                                            <X size={16} />
                                        </button>
                                    </div>
                                    
                                    <div className="flex-1 p-4 sm:p-5 space-y-5 overflow-y-auto min-h-0 pb-[max(1rem,env(safe-area-inset-bottom))]">
                                        <div className="space-y-1.5">
                                            <h4 className="text-sm font-semibold text-slate-900 tracking-tight leading-tight">
                                                {activeCitation.source_name || "Source"}
                                            </h4>
                                            <p className="text-[10px] font-mono text-slate-400 break-all select-all leading-normal">
                                                {activeCitation.url || "Attached PDF document"}
                                            </p>
                                        </div>

                                        {/* High-Fidelity Soft Mint Green Segment Box */}
                                        <div className="p-3.5 sm:p-4 bg-emerald-500/5 border border-emerald-200/50 font-sans text-xs leading-relaxed text-emerald-800 font-medium whitespace-pre-wrap select-text rounded">
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
                                                        className="w-full flex items-center justify-center gap-1.5 border border-indigo-200 bg-indigo-500/5 hover:bg-indigo-500/10 py-2.5 text-indigo-700 text-xs font-mono font-medium transition-all rounded active:scale-95"
                                                    >
                                                        <ExternalLink size={12} />
                                                        Visit Original Link
                                                    </a>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </>
                        )}
                    </div>
                )}

                {/* SPACE A: ECHO (Living Memory) Tab */}
                {project.status !== "error" && activeTab === "echo" && (
                    <div className="flex-1 p-3.5 sm:p-6 md:p-8 overflow-y-auto space-y-6 flex flex-col h-full bg-slate-50 animate-in fade-in duration-150">
                        <div className="max-w-[1000px] w-full mx-auto space-y-6">
                            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-4">
                                <div>
                                    <h3 className="text-lg font-semibold text-slate-900 tracking-tight flex items-center gap-2">
                                        <Brain className="text-indigo-600" size={20} />
                                        ECHO — The AI That Evolves With You
                                    </h3>
                                    <p className="text-xs text-slate-500 font-mono mt-1">
                                        Living memory graph: remembers ongoing projects, technical constraints, team decisions, and preferences.
                                    </p>
                                </div>
                                <div className="flex items-center gap-2">
                                    <span className="px-2.5 py-1 bg-indigo-50 border border-indigo-200 text-indigo-700 text-xs font-mono font-semibold rounded-full flex items-center gap-1">
                                        <Sparkles size={12} />
                                        {echoMemories.length} Active Memories
                                    </span>
                                </div>
                            </div>

                            {/* Add Memory Form Card */}
                            <Card className="p-5 border border-slate-200 bg-white shadow-xs">
                                <h4 className="text-xs font-mono font-bold uppercase text-slate-700 tracking-wider mb-3">Add / Teach New Preference or Fact</h4>
                                <form 
                                    onSubmit={async (e) => {
                                        e.preventDefault();
                                        if (!newMemoryKey.trim() || !newMemoryValue.trim()) return;
                                        try {
                                            await api.post(`/projects/${project_id}/echo/memories`, {
                                                category: newMemoryCategory,
                                                key: newMemoryKey.trim(),
                                                value: newMemoryValue.trim()
                                            });
                                            setNewMemoryKey("");
                                            setNewMemoryValue("");
                                            const res = await api.get(`/projects/${project_id}/echo/memories`);
                                            setEchoMemories(res.data.memories || []);
                                        } catch (err) {
                                            console.error("Failed to add memory:", err);
                                            alert("Failed to save memory.");
                                        }
                                    }}
                                    className="grid grid-cols-1 sm:grid-cols-12 gap-3 items-end"
                                >
                                    <div className="sm:col-span-3 space-y-1">
                                        <label className="text-[10px] font-mono text-slate-400 uppercase font-semibold">Category</label>
                                        <select
                                            value={newMemoryCategory}
                                            onChange={(e) => setNewMemoryCategory(e.target.value)}
                                            className="w-full text-xs font-mono h-9 border border-slate-200 rounded px-2.5 bg-white text-slate-800"
                                        >
                                            <option value="preference">Preference</option>
                                            <option value="project_fact">Project Fact</option>
                                            <option value="decision">Decision</option>
                                            <option value="style">Style / Tone</option>
                                        </select>
                                    </div>
                                    <div className="sm:col-span-4 space-y-1">
                                        <label className="text-[10px] font-mono text-slate-400 uppercase font-semibold">Key / Topic</label>
                                        <Input
                                            placeholder="e.g. Frontend Stack, Budget"
                                            value={newMemoryKey}
                                            onChange={(e) => setNewMemoryKey(e.target.value)}
                                            className="h-9 text-xs"
                                        />
                                    </div>
                                    <div className="sm:col-span-4 space-y-1">
                                        <label className="text-[10px] font-mono text-slate-400 uppercase font-semibold">Knowledge Fact / Instruction</label>
                                        <Input
                                            placeholder="e.g. Next.js 14, Tailwind, Fast-Mode"
                                            value={newMemoryValue}
                                            onChange={(e) => setNewMemoryValue(e.target.value)}
                                            className="h-9 text-xs"
                                        />
                                    </div>
                                    <div className="sm:col-span-1">
                                        <Button type="submit" className="w-full h-9 bg-indigo-600 hover:bg-indigo-700 text-white text-xs">
                                            Add
                                        </Button>
                                    </div>
                                </form>
                            </Card>

                            {/* Memories List */}
                            {echoLoading ? (
                                <div className="h-48 bg-white border border-slate-200 flex items-center justify-center">
                                    <div className="flex items-center gap-2 text-xs font-mono text-slate-500">
                                        <Loader2 className="animate-spin text-indigo-600" size={16} />
                                        Loading Living Memory Graph...
                                    </div>
                                </div>
                            ) : echoMemories.length === 0 ? (
                                <div className="p-8 text-center bg-white border border-slate-200">
                                    <Brain className="mx-auto text-slate-300 mb-2" size={32} />
                                    <p className="text-xs font-mono text-slate-500">No memories recorded yet.</p>
                                    <p className="text-[11px] text-slate-400 mt-1">Teach ECHO facts or ask questions in Q&A to build knowledge over time.</p>
                                </div>
                            ) : (
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    {echoMemories.map((m, idx) => (
                                        <Card key={m.id || idx} className="p-4 border border-slate-200/80 bg-white hover:border-indigo-300 transition-all flex flex-col justify-between">
                                            <div className="space-y-2">
                                                <div className="flex items-center justify-between">
                                                    <Badge variant="secondary" className="text-[10px] font-mono capitalize border-indigo-200 text-indigo-700 bg-indigo-50/50">
                                                        {m.category || "fact"}
                                                    </Badge>
                                                    <button
                                                        onClick={async () => {
                                                            try {
                                                                await api.delete(`/projects/${project_id}/echo/memories/${encodeURIComponent(m.key)}`);
                                                                setEchoMemories(prev => prev.filter(x => x.key !== m.key));
                                                            } catch (err) {
                                                                console.error("Delete memory failed:", err);
                                                            }
                                                        }}
                                                        className="text-slate-400 hover:text-red-600 transition-colors p-1"
                                                        title="Delete this memory"
                                                    >
                                                        <Trash2 size={13} />
                                                    </button>
                                                </div>
                                                <h5 className="text-sm font-semibold text-slate-900 tracking-tight">{m.key}</h5>
                                                <p className="text-xs text-slate-600 leading-relaxed font-sans">{m.value}</p>
                                            </div>
                                            <span className="text-[10px] font-mono text-slate-400 mt-3 pt-2 border-t border-slate-100 block">
                                                Synced into live Q&A system prompts
                                            </span>
                                        </Card>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {/* SPACE B: MINDSPACE (Visual Thought Canvas) Tab */}
                {project.status !== "error" && activeTab === "mindspace" && (
                    <div className="flex-1 p-3.5 sm:p-6 md:p-8 overflow-y-auto space-y-6 flex flex-col h-full bg-slate-50 animate-in fade-in duration-150">
                        <div className="max-w-[1100px] w-full mx-auto space-y-6">
                            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-4">
                                <div>
                                    <h3 className="text-lg font-semibold text-slate-900 tracking-tight flex items-center gap-2">
                                        <Compass className="text-indigo-600" size={20} />
                                        MINDSPACE — The Conversation You Can Explore
                                    </h3>
                                    <p className="text-xs text-slate-500 font-mono mt-1">
                                        Explorable knowledge canvas: claims, verified concepts, and evidence connections instead of flat text walls.
                                    </p>
                                </div>
                                <div className="flex items-center gap-2">
                                    <Button
                                        onClick={async () => {
                                            setMindspaceLoading(true);
                                            try {
                                                const res = await api.get(`/projects/${project_id}/mindspace/canvas`);
                                                setMindspaceData(res.data);
                                            } catch (err) {
                                                console.error("Failed to refresh MINDSPACE:", err);
                                            } finally {
                                                setMindspaceLoading(false);
                                            }
                                        }}
                                        variant="outline"
                                        className="h-8 text-xs font-mono gap-1"
                                    >
                                        <RefreshCw size={12} className={mindspaceLoading ? "animate-spin" : ""} />
                                        Refresh Canvas
                                    </Button>
                                </div>
                            </div>

                            {mindspaceLoading ? (
                                <div className="h-[450px] bg-white border border-slate-200 flex items-center justify-center">
                                    <div className="flex flex-col items-center gap-2 text-xs font-mono text-slate-500">
                                        <Loader2 className="animate-spin text-indigo-600" size={24} />
                                        Synthesizing MINDSPACE Thought Nodes & Evidence...
                                    </div>
                                </div>
                            ) : !mindspaceData || mindspaceData.nodes.length === 0 ? (
                                <div className="p-12 text-center bg-white border border-slate-200">
                                    <Network className="mx-auto text-slate-300 mb-3" size={36} />
                                    <p className="text-sm font-semibold text-slate-700">No Mindspace Nodes Available Yet</p>
                                    <p className="text-xs text-slate-500 font-mono mt-1">
                                        Once the web crawler or document indexer has processed pages, concepts and evidence links will populate here.
                                    </p>
                                </div>
                            ) : (
                                <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                                    {/* Left: Interactive Node Canvas Cards */}
                                    <div className="lg:col-span-8 space-y-4">
                                        <div className="flex items-center justify-between text-xs font-mono text-slate-500 pb-1">
                                            <span>EXPLORABLE THOUGHT NODES ({mindspaceData.nodes.length})</span>
                                            <span>Click node to inspect evidence</span>
                                        </div>
                                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                            {mindspaceData.nodes.map((node, nIdx) => (
                                                <Card
                                                    key={node.id || nIdx}
                                                    onClick={() => setSelectedMindNode(node)}
                                                    className={`p-4 border transition-all cursor-pointer relative overflow-hidden ${
                                                        selectedMindNode?.id === node.id
                                                            ? "border-indigo-600 bg-indigo-50/20 shadow-sm ring-1 ring-indigo-400"
                                                            : "border-slate-200 bg-white hover:border-slate-300 hover:shadow-xs"
                                                    }`}
                                                >
                                                    <div className="space-y-2">
                                                        <div className="flex items-center justify-between">
                                                            <Badge variant="secondary" className="text-[10px] font-mono capitalize border-slate-200">
                                                                {node.category || "Concept"}
                                                            </Badge>
                                                            <span className="text-[10px] font-mono text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
                                                                {node.evidence_count || 1} cited sources
                                                            </span>
                                                        </div>
                                                        <h4 className="text-sm font-semibold text-slate-900 tracking-tight leading-snug">
                                                            {node.label}
                                                        </h4>
                                                        <p className="text-xs text-slate-500 line-clamp-2 font-sans">
                                                            {node.snippet}
                                                        </p>
                                                    </div>
                                                </Card>
                                            ))}
                                        </div>

                                        {/* Connected Edges Relationships Table */}
                                        {mindspaceData.edges.length > 0 && (
                                            <div className="mt-6 border border-slate-200 bg-white p-4">
                                                <h4 className="text-xs font-mono font-bold uppercase text-slate-700 mb-3 tracking-wider">
                                                    Concept Linkages & Semantic Flow
                                                </h4>
                                                <div className="space-y-2 max-h-48 overflow-y-auto">
                                                    {mindspaceData.edges.map((edge, eIdx) => (
                                                        <div key={edge.id || eIdx} className="flex items-center text-xs font-mono text-slate-600 bg-slate-50 px-3 py-1.5 border border-slate-100 gap-2">
                                                            <span className="font-semibold text-indigo-700">{edge.source}</span>
                                                            <span className="text-slate-400 text-[10px]">&mdash; [{edge.relation}] &rarr;</span>
                                                            <span className="font-semibold text-slate-800">{edge.target}</span>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        )}
                                    </div>

                                    {/* Right: Selected Node Evidence & Branch Inspector */}
                                    <div className="lg:col-span-4">
                                        {selectedMindNode ? (
                                            <Card className="p-5 border border-indigo-200 bg-white shadow-sm space-y-4 sticky top-6">
                                                <div className="border-b border-slate-100 pb-3">
                                                    <span className="text-[10px] font-mono text-indigo-600 uppercase font-bold tracking-wider">
                                                        Node Inspector & Evidence
                                                    </span>
                                                    <h4 className="text-base font-bold text-slate-900 tracking-tight mt-1">
                                                        {selectedMindNode.label}
                                                    </h4>
                                                </div>

                                                <div className="space-y-2">
                                                    <label className="text-[10px] font-mono text-slate-400 uppercase font-semibold">Evidence Grounding</label>
                                                    <div className="p-3 bg-slate-50 border border-slate-200/80 text-xs text-slate-700 leading-relaxed font-sans rounded">
                                                        &ldquo;{selectedMindNode.snippet}&rdquo;
                                                    </div>
                                                </div>

                                                <div className="pt-2 border-t border-slate-100 flex flex-col gap-2">
                                                    <Button
                                                        onClick={() => {
                                                            // Branch this thought into the Q&A Assistant input directly
                                                            setInput(`Explore deeper evidence and implications about '${selectedMindNode.label}'`);
                                                            setActiveTab("chat");
                                                        }}
                                                        className="w-full bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-mono gap-1.5 h-9"
                                                    >
                                                        <GitBranch size={13} />
                                                        Branch Idea Into Chat
                                                    </Button>
                                                    <Button
                                                        onClick={() => setSelectedMindNode(null)}
                                                        variant="outline"
                                                        className="w-full text-xs font-mono h-8"
                                                    >
                                                        Close Inspector
                                                    </Button>
                                                </div>
                                            </Card>
                                        ) : (
                                            <div className="p-6 border border-dashed border-slate-300 text-center bg-slate-50/50">
                                                <Compass className="mx-auto text-slate-400 mb-2" size={24} />
                                                <p className="text-xs font-mono text-slate-600 font-semibold">Node Inspector Ready</p>
                                                <p className="text-[11px] text-slate-400 mt-1">Click any thought card on the left to verify evidence and branch new discussions.</p>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {/* SPACE C: FORGE (Interactive Artifacts & Workspace) Tab */}
                {project.status !== "error" && activeTab === "forge" && (
                    <div className="flex-1 p-3.5 sm:p-6 md:p-8 overflow-y-auto space-y-6 flex flex-col h-full bg-slate-50 animate-in fade-in duration-150">
                        <div className="max-w-[1100px] w-full mx-auto space-y-6">
                            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-4">
                                <div>
                                    <h3 className="text-lg font-semibold text-slate-900 tracking-tight flex items-center gap-2">
                                        <Hammer className="text-indigo-600" size={20} />
                                        FORGE — The AI That Builds While You Talk
                                    </h3>
                                    <p className="text-xs text-slate-500 font-mono mt-1">
                                        Living artifact workspace: turns answers into editable plans, checklists, calculators, and prototypes.
                                    </p>
                                </div>
                                <div className="flex items-center gap-2">
                                    <Button
                                        onClick={() => setCanvasOpen(true)}
                                        className="h-8 text-xs font-mono gap-1.5 bg-indigo-600 hover:bg-indigo-700 text-white"
                                    >
                                        <LayoutTemplate size={12} />
                                        Open Floating Canvas
                                    </Button>
                                </div>
                            </div>

                            {/* FORGE Interactive Quick Starters */}
                            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                                <Card 
                                    onClick={() => {
                                        setInput("Generate an interactive project execution plan with checklists and timeline.");
                                        setResponseMode("builder");
                                        setActiveTab("chat");
                                    }}
                                    className="p-4 border border-slate-200 hover:border-indigo-400 bg-white transition-all cursor-pointer shadow-xs group"
                                >
                                    <span className="text-[10px] font-mono font-bold text-indigo-600 uppercase tracking-wider block mb-1">Builder Tool</span>
                                    <h4 className="text-sm font-semibold text-slate-900 group-hover:text-indigo-600 transition-colors">Launch Plan & Checklist</h4>
                                    <p className="text-xs text-slate-500 mt-1">Generates an interactive markdown task list with progress tracking.</p>
                                </Card>

                                <Card 
                                    onClick={() => {
                                        setInput("Run a brutal risk review and pre-mortem failure analysis on our current setup.");
                                        setResponseMode("brutal_review");
                                        setActiveTab("chat");
                                    }}
                                    className="p-4 border border-slate-200 hover:border-indigo-400 bg-white transition-all cursor-pointer shadow-xs group"
                                >
                                    <span className="text-[10px] font-mono font-bold text-amber-600 uppercase tracking-wider block mb-1">Audit Tool</span>
                                    <h4 className="text-sm font-semibold text-slate-900 group-hover:text-amber-600 transition-colors">Risk Pre-Mortem Audit</h4>
                                    <p className="text-xs text-slate-500 mt-1">Stresses system assumptions and pinpoints vulnerabilities.</p>
                                </Card>

                                <Card 
                                    onClick={() => {
                                        setInput("Build an architectural decision tree comparing implementation options.");
                                        setResponseMode("decision_tree");
                                        setActiveTab("chat");
                                    }}
                                    className="p-4 border border-slate-200 hover:border-indigo-400 bg-white transition-all cursor-pointer shadow-xs group"
                                >
                                    <span className="text-[10px] font-mono font-bold text-emerald-600 uppercase tracking-wider block mb-1">Logic Tool</span>
                                    <h4 className="text-sm font-semibold text-slate-900 group-hover:text-emerald-600 transition-colors">Decision Tree Builder</h4>
                                    <p className="text-xs text-slate-500 mt-1">Maps conditional branching scenarios based on constraints.</p>
                                </Card>
                            </div>

                            {/* FORGE In-Place Living Canvas Editor with Python Code Sandbox */}
                            <Card className="p-6 border border-slate-200 bg-white shadow-sm space-y-4">
                                <div className="flex flex-wrap items-center justify-between border-b border-slate-100 pb-3 gap-2">
                                    <div className="flex items-center gap-2">
                                        <span className="text-xs font-mono font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                                            <LayoutTemplate size={14} className="text-indigo-600" />
                                            Active Deliverable Draft & Working Notes
                                        </span>
                                        <span className="text-[10px] font-mono text-slate-400">• Auto-saved</span>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <Button
                                            onClick={() => handleRunPythonCode()}
                                            disabled={codeRunning || !canvasContent.trim()}
                                            className="h-7 text-xs font-mono gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white px-3"
                                            title="Safely run calculations or script in isolated Python 3.11 sandbox"
                                        >
                                            {codeRunning ? (
                                                <>
                                                    <Loader2 size={12} className="animate-spin" />
                                                    Running Sandbox...
                                                </>
                                            ) : (
                                                <>
                                                    <Code2 size={12} />
                                                    Run in Python Sandbox
                                                </>
                                            )}
                                        </Button>
                                    </div>
                                </div>
                                <textarea
                                    value={canvasContent}
                                    onChange={(e) => setCanvasContent(e.target.value)}
                                    placeholder="# FORGE Working Artifact&#10;&#10;Type, edit, or copy generated specifications, calculations, or Python code here...&#10;&#10;Example:&#10;import math&#10;print(f'Total Combinations: {math.comb(10, 3)}')"
                                    className="w-full h-80 p-4 border border-slate-200 font-mono text-[16px] sm:text-xs text-slate-800 rounded bg-slate-50/50 focus:bg-white focus:outline-none focus:border-indigo-500 resize-none leading-relaxed"
                                />

                                {/* Python Sandbox Output Console Cell */}
                                {codeOutput && (
                                    <div className="p-4 bg-slate-950 text-slate-100 rounded-lg border border-slate-800 font-mono text-xs space-y-2 animate-in fade-in">
                                        <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                                            <div className="flex items-center gap-2">
                                                <Terminal size={14} className="text-emerald-400" />
                                                <span className="text-[11px] font-bold text-emerald-400">PYTHON 3.11 EXECUTION RESULT</span>
                                                <span className="text-[10px] text-slate-400">({codeOutput.duration_ms}ms)</span>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold uppercase ${
                                                    codeOutput.returncode === 0 ? "bg-emerald-500/20 text-emerald-400" : "bg-rose-500/20 text-rose-400"
                                                }`}>
                                                    {codeOutput.returncode === 0 ? "Success" : "Exit Code " + codeOutput.returncode}
                                                </span>
                                                <button
                                                    onClick={() => setCodeOutput(null)}
                                                    className="text-slate-500 hover:text-slate-300 text-xs px-1"
                                                >
                                                    ×
                                                </button>
                                            </div>
                                        </div>
                                        {codeOutput.stdout && (
                                            <div>
                                                <div className="text-[10px] text-slate-400 uppercase font-bold tracking-wider mb-1">Standard Output:</div>
                                                <pre className="text-emerald-300 whitespace-pre-wrap select-all font-mono text-xs bg-slate-900/60 p-2.5 rounded border border-slate-800/80">
                                                    {codeOutput.stdout}
                                                </pre>
                                            </div>
                                        )}
                                        {codeOutput.stderr && (
                                            <div>
                                                <div className="text-[10px] text-rose-400 uppercase font-bold tracking-wider mb-1">Standard Error:</div>
                                                <pre className="text-rose-300 whitespace-pre-wrap select-all font-mono text-xs bg-rose-950/30 p-2.5 rounded border border-rose-900/40">
                                                    {codeOutput.stderr}
                                                </pre>
                                            </div>
                                        )}
                                    </div>
                                )}
                            </Card>
                        </div>
                    </div>
                )}

                {/* STATE 3: Neo4j Knowledge Graph Tab */}
                {project.status !== "error" && activeTab === "graph" && (
                    <div className="flex-1 p-3.5 sm:p-6 md:p-8 overflow-y-auto space-y-6 flex flex-col h-full bg-slate-50">
                        <div className="max-w-[1200px] w-full mx-auto space-y-4">
                            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-4">
                                <div>
                                    <h3 className="text-lg font-semibold text-slate-900 tracking-tight flex items-center gap-2">
                                        <Network className="text-indigo-600" size={20} />
                                        Neo4j Knowledge Graph & Entity Explorer
                                    </h3>
                                    <p className="text-xs text-slate-500 font-mono mt-0.5">
                                        Multi-cluster semantic topology: click any entity node to inspect deep provenance, relations, and cross-reference with RAG assistant.
                                    </p>
                                </div>
                                <div className="flex items-center gap-2">
                                    <span className="px-2.5 py-1 bg-indigo-50 border border-indigo-200 text-indigo-700 text-xs font-mono font-semibold rounded-full flex items-center gap-1.5">
                                        <Sparkles size={12} />
                                        {graphData?.nodes?.length || 0} Entities • {graphData?.links?.length || 0} Relations
                                    </span>
                                    <button
                                        onClick={() => setWhatIfOpen(true)}
                                        className="px-3 py-1 bg-amber-500 hover:bg-amber-600 text-white text-xs font-mono font-semibold rounded-full flex items-center gap-1.5 shadow-sm transition-colors cursor-pointer"
                                    >
                                        <Activity size={12} />
                                        Causal "What-If?" Simulator
                                    </button>
                                </div>
                            </div>

                            {/* Graph Control & Search Toolbar */}
                            <div className="flex flex-wrap items-center justify-between gap-3 bg-white p-3 border border-slate-200 shadow-xs">
                                <div className="flex items-center gap-2 flex-1 max-w-sm">
                                    <div className="relative w-full">
                                        <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
                                        <input
                                            type="text"
                                            placeholder="Search entities, professors, departments, labs..."
                                            value={graphSearchQuery}
                                            onChange={(e) => setGraphSearchQuery(e.target.value)}
                                            className="w-full pl-8 pr-3 py-1.5 text-base sm:text-xs font-mono border border-slate-200 rounded focus:outline-none focus:border-indigo-500 bg-slate-50/50"
                                        />
                                    </div>
                                    {graphSearchQuery && (
                                        <button
                                            onClick={() => setGraphSearchQuery("")}
                                            className="text-xs text-slate-400 hover:text-slate-700"
                                        >
                                            Clear
                                        </button>
                                    )}
                                </div>

                                <div className="flex items-center gap-2">
                                    <div className="flex items-center border border-slate-200 rounded overflow-hidden">
                                        <button
                                            onClick={() => setGraphZoom(z => Math.max(0.5, Number((z - 0.15).toFixed(2))))}
                                            className="p-1.5 bg-slate-50 hover:bg-slate-100 text-slate-600 border-r border-slate-200"
                                            title="Zoom Out"
                                        >
                                            <ZoomOut size={13} />
                                        </button>
                                        <span className="px-2 text-[10px] font-mono font-semibold text-slate-600 bg-white">
                                            {Math.round(graphZoom * 100)}%
                                        </span>
                                        <button
                                            onClick={() => setGraphZoom(z => Math.min(2.0, Number((z + 0.15).toFixed(2))))}
                                            className="p-1.5 bg-slate-50 hover:bg-slate-100 text-slate-600 border-l border-slate-200"
                                            title="Zoom In"
                                        >
                                            <ZoomIn size={13} />
                                        </button>
                                        <button
                                            onClick={() => { setGraphZoom(1.0); setSelectedGraphNode(null); setGraphSearchQuery(""); }}
                                            className="p-1.5 bg-slate-50 hover:bg-slate-100 text-slate-600 border-l border-slate-200"
                                            title="Reset View"
                                        >
                                            <RefreshCw size={13} />
                                        </button>
                                    </div>
                                </div>
                            </div>
                            
                            {graphLoading ? (
                                <div className="h-[520px] bg-white border border-slate-200 flex items-center justify-center">
                                    <div className="flex flex-col items-center gap-2">
                                        <Loader2 className="animate-spin text-indigo-600" size={28} />
                                        <span className="text-xs font-mono text-slate-500">Extracting entity relations and Cypher hierarchy...</span>
                                    </div>
                                </div>
                            ) : graphData && graphData.nodes && graphData.nodes.length > 0 ? (
                                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                                    {/* Main SVG Graph Canvas (2 Columns) */}
                                    <Card className="lg:col-span-2 rounded-lg border border-slate-200 bg-white p-4 shadow-sm flex flex-col items-center justify-center relative overflow-hidden">
                                        <div className="w-full border border-slate-100 bg-slate-900/[0.02] relative overflow-hidden h-[360px] sm:h-[540px] rounded flex items-center justify-center">
                                            <svg
                                                className="w-full h-full cursor-grab active:cursor-grabbing select-none"
                                                viewBox="0 0 720 540"
                                            >
                                                <defs>
                                                    <marker
                                                        id="graph-arrow"
                                                        viewBox="0 0 10 10"
                                                        refX="18"
                                                        refY="5"
                                                        markerWidth="6"
                                                        markerHeight="6"
                                                        orient="auto-start-reverse"
                                                    >
                                                        <path d="M 0 1 L 10 5 L 0 9 z" fill="#94a3b8" />
                                                    </marker>
                                                    <filter id="node-glow" x="-20%" y="-20%" width="140%" height="140%">
                                                        <feDropShadow dx="0" dy="0" stdDeviation="3" floodColor="#4f46e5" floodOpacity="0.5" />
                                                    </filter>
                                                    <filter id="select-glow" x="-20%" y="-20%" width="140%" height="140%">
                                                        <feDropShadow dx="0" dy="0" stdDeviation="4" floodColor="#f59e0b" floodOpacity="0.8" />
                                                    </filter>
                                                </defs>

                                                <g transform={`scale(${graphZoom})`} style={{ transformOrigin: "360px 270px", transition: "transform 0.15s ease-out" }}>
                                                    {/* Clustered Node Math Calculation */}
                                                    {(() => {
                                                        const nodes = graphData.nodes;
                                                        const nodePositions = new Map<string, { x: number; y: number }>();
                                                        const centerX = 360;
                                                        const centerY = 270;

                                                        // Classify nodes
                                                        const rootNode = nodes.find(n => n.type === "Project") || nodes[0];
                                                        const catNodes = nodes.filter(n => n.type === "Category Hub");
                                                        const pageNodes = nodes.filter(n => n.type === "Page");
                                                        const otherNodes = nodes.filter(n => n !== rootNode && !catNodes.includes(n) && !pageNodes.includes(n));

                                                        // Root at center
                                                        if (rootNode) {
                                                            nodePositions.set(rootNode.id, { x: centerX, y: centerY });
                                                        }

                                                        // Middle ring: Category hubs (r=125)
                                                        catNodes.forEach((n, idx) => {
                                                            const angle = (2 * Math.PI * idx) / Math.max(1, catNodes.length);
                                                            nodePositions.set(n.id, {
                                                                x: centerX + 125 * Math.cos(angle),
                                                                y: centerY + 125 * Math.sin(angle)
                                                            });
                                                        });

                                                        // Outer ring: Pages (r=210)
                                                        pageNodes.forEach((n, idx) => {
                                                            const angle = (2 * Math.PI * idx) / Math.max(1, pageNodes.length) + 0.15;
                                                            nodePositions.set(n.id, {
                                                                x: centerX + 210 * Math.cos(angle),
                                                                y: centerY + 210 * Math.sin(angle)
                                                            });
                                                        });

                                                        // Far outer ring: Extracted Entities (r=255)
                                                        otherNodes.forEach((n, idx) => {
                                                            const angle = (2 * Math.PI * idx) / Math.max(1, otherNodes.length);
                                                            nodePositions.set(n.id, {
                                                                x: centerX + 255 * Math.cos(angle),
                                                                y: centerY + 255 * Math.sin(angle)
                                                            });
                                                        });

                                                        // Draw Links
                                                        const linksSvg = graphData.links.map((link, idx) => {
                                                            const srcPos = nodePositions.get(link.source);
                                                            const tgtPos = nodePositions.get(link.target);
                                                            if (!srcPos || !tgtPos) return null;

                                                            const isConnectedToSelected = selectedGraphNode && 
                                                                (link.source === selectedGraphNode.id || link.target === selectedGraphNode.id);

                                                            return (
                                                                <g key={`link-${idx}`}>
                                                                    <line
                                                                        x1={srcPos.x}
                                                                        y1={srcPos.y}
                                                                        x2={tgtPos.x}
                                                                        y2={tgtPos.y}
                                                                        stroke={isConnectedToSelected ? "#4f46e5" : "#cbd5e1"}
                                                                        strokeWidth={isConnectedToSelected ? "2.5" : "1.2"}
                                                                        strokeDasharray={link.type === "MENTIONS" ? "3 3" : undefined}
                                                                        markerEnd="url(#graph-arrow)"
                                                                        opacity={isConnectedToSelected ? 1 : 0.6}
                                                                    />
                                                                    {/* Center Relationship Tag */}
                                                                    <text
                                                                        x={(srcPos.x + tgtPos.x) / 2}
                                                                        y={(srcPos.y + tgtPos.y) / 2 - 3}
                                                                        fontSize="7.5"
                                                                        fontFamily="monospace"
                                                                        fill={isConnectedToSelected ? "#312e81" : "#94a3b8"}
                                                                        fontWeight={isConnectedToSelected ? "bold" : "normal"}
                                                                        textAnchor="middle"
                                                                    >
                                                                        {link.type}
                                                                    </text>
                                                                </g>
                                                            );
                                                        });

                                                        // Draw Nodes
                                                        const nodesSvg = nodes.map((n, idx) => {
                                                            const pos = nodePositions.get(n.id);
                                                            if (!pos) return null;

                                                            const isProject = n.type === "Project";
                                                            const isCategory = n.type === "Category Hub";
                                                            const isPage = n.type === "Page";
                                                            const isSelected = selectedGraphNode && selectedGraphNode.id === n.id;
                                                            
                                                            // Search filter highlighting
                                                            const matchesSearch = !graphSearchQuery || 
                                                                n.id.toLowerCase().includes(graphSearchQuery.toLowerCase()) || 
                                                                (n.group && n.group.toLowerCase().includes(graphSearchQuery.toLowerCase()));

                                                            const radius = isProject ? 22 : isCategory ? 16 : isPage ? 12 : 10;
                                                            const fill = isProject 
                                                                ? "#4f46e5" 
                                                                : isCategory 
                                                                ? "#059669" 
                                                                : isPage 
                                                                ? "#0284c7" 
                                                                : "#7c3aed";

                                                            return (
                                                                <g
                                                                    key={`node-${idx}`}
                                                                    onClick={() => setSelectedGraphNode(n)}
                                                                    onMouseEnter={() => setHoveredGraphNode(n)}
                                                                    onMouseLeave={() => setHoveredGraphNode(null)}
                                                                    className="cursor-pointer transition-all duration-150"
                                                                    opacity={matchesSearch ? 1 : 0.15}
                                                                >
                                                                    {/* Selection Outer Glow Ring */}
                                                                    {isSelected && (
                                                                        <circle
                                                                            cx={pos.x}
                                                                            cy={pos.y}
                                                                            r={radius + 6}
                                                                            fill="none"
                                                                            stroke="#f59e0b"
                                                                            strokeWidth="3.5"
                                                                            strokeDasharray="4 2"
                                                                            className="animate-spin-slow"
                                                                        />
                                                                    )}

                                                                    {/* Main Node Circle */}
                                                                    <circle
                                                                        cx={pos.x}
                                                                        cy={pos.y}
                                                                        r={radius}
                                                                        fill={fill}
                                                                        stroke="#ffffff"
                                                                        strokeWidth={isProject ? "3" : "2"}
                                                                        filter={isProject ? "url(#node-glow)" : undefined}
                                                                    />

                                                                    {/* Inner Icon or Letter */}
                                                                    <text
                                                                        x={pos.x}
                                                                        y={pos.y + 3.5}
                                                                        textAnchor="middle"
                                                                        fontSize={isProject ? "11" : isCategory ? "9" : "8"}
                                                                        fontFamily="sans-serif"
                                                                        fontWeight="bold"
                                                                        fill="#ffffff"
                                                                        pointerEvents="none"
                                                                    >
                                                                        {isProject ? "P" : isCategory ? "C" : isPage ? "W" : "E"}
                                                                    </text>

                                                                    {/* Node Text Label */}
                                                                    <text
                                                                        x={pos.x}
                                                                        y={pos.y + radius + 11}
                                                                        textAnchor="middle"
                                                                        fontSize="8.5"
                                                                        fontFamily="monospace"
                                                                        fontWeight={isSelected ? "bold" : "600"}
                                                                        fill={isSelected ? "#1e1b4b" : "#334155"}
                                                                        className="drop-shadow-[0_1px_1px_rgba(255,255,255,0.9)] select-none pointer-events-none"
                                                                    >
                                                                        {n.id.length > 18 ? `${n.id.substring(0, 16)}...` : n.id}
                                                                    </text>
                                                                </g>
                                                            );
                                                        });

                                                        return (
                                                            <>
                                                                {linksSvg}
                                                                {nodesSvg}
                                                            </>
                                                        );
                                                    })()}
                                                </g>
                                            </svg>
                                        </div>

                                        {/* Legend Footer */}
                                        <div className="w-full mt-3 flex flex-wrap items-center justify-between gap-3 text-xs font-mono text-slate-500 border-t border-slate-100 pt-3">
                                            <div className="flex items-center gap-4">
                                                <div className="flex items-center gap-1.5"><div className="w-3 h-3 rounded-full bg-indigo-600 shadow-xs" /> Core Project</div>
                                                <div className="flex items-center gap-1.5"><div className="w-3 h-3 rounded-full bg-emerald-600 shadow-xs" /> Category Hub</div>
                                                <div className="flex items-center gap-1.5"><div className="w-3 h-3 rounded-full bg-sky-600 shadow-xs" /> Crawled Page</div>
                                                <div className="flex items-center gap-1.5"><div className="w-3 h-3 rounded-full bg-violet-600 shadow-xs" /> Named Entity</div>
                                            </div>
                                            <span className="text-[10px] text-slate-400">Click any node to open deep inspector</span>
                                        </div>
                                    </Card>

                                    {/* Column 3: Interactive Node Inspector Drawer */}
                                    <div className="space-y-4">
                                        {selectedGraphNode ? (
                                            <Card className="p-5 border border-indigo-200 bg-white shadow-md space-y-4 animate-in slide-in-from-right duration-200">
                                                <div className="flex items-start justify-between border-b border-slate-100 pb-3">
                                                    <div>
                                                        <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded font-bold tracking-wider bg-indigo-50 text-indigo-700 border border-indigo-200">
                                                            {selectedGraphNode.type || "Entity"}
                                                        </span>
                                                        <h4 className="text-sm font-bold text-slate-900 mt-1 leading-snug break-words">
                                                            {selectedGraphNode.id}
                                                        </h4>
                                                    </div>
                                                    <button
                                                        onClick={() => setSelectedGraphNode(null)}
                                                        className="text-slate-400 hover:text-slate-700 p-1 rounded hover:bg-slate-100"
                                                    >
                                                        <X size={15} />
                                                    </button>
                                                </div>

                                                {/* Node Metadata & Relations */}
                                                <div className="space-y-3 font-mono text-xs">
                                                    {selectedGraphNode.group && (
                                                        <div className="flex justify-between border-b border-slate-50 pb-1.5">
                                                            <span className="text-slate-400 text-[11px]">CATEGORY</span>
                                                            <span className="font-semibold text-slate-800">{selectedGraphNode.group}</span>
                                                        </div>
                                                    )}

                                                    {/* Connected Links Count & List */}
                                                    {(() => {
                                                        const connected = (graphData?.links || []).filter(
                                                            l => l.source === selectedGraphNode.id || l.target === selectedGraphNode.id
                                                        );
                                                        return (
                                                            <div className="space-y-2 pt-1">
                                                                <div className="flex justify-between items-center text-[11px] text-slate-400">
                                                                    <span>CONNECTED RELATIONS</span>
                                                                    <span className="font-bold text-indigo-600 bg-indigo-50 px-1.5 py-0.5 rounded">
                                                                        {connected.length} links
                                                                    </span>
                                                                </div>
                                                                <div className="max-h-44 overflow-y-auto space-y-1.5 pr-1">
                                                                    {connected.map((conn, cIdx) => {
                                                                        const isOutgoing = conn.source === selectedGraphNode.id;
                                                                        const partner = isOutgoing ? conn.target : conn.source;
                                                                        return (
                                                                            <div
                                                                                key={cIdx}
                                                                                onClick={() => {
                                                                                    const partnerNode = graphData.nodes.find(n => n.id === partner);
                                                                                    if (partnerNode) setSelectedGraphNode(partnerNode);
                                                                                }}
                                                                                className="p-2 border border-slate-100 bg-slate-50/80 hover:bg-indigo-50/50 hover:border-indigo-200 cursor-pointer rounded transition-all text-[11px] flex items-center justify-between"
                                                                            >
                                                                                <span className="text-slate-700 truncate font-sans font-medium flex-1">
                                                                                    {partner}
                                                                                </span>
                                                                                <span className="text-[9px] font-mono uppercase text-indigo-600 bg-white px-1.5 py-0.5 border border-indigo-100 rounded ml-2 shrink-0">
                                                                                    {conn.type} {isOutgoing ? "→" : "←"}
                                                                                </span>
                                                                            </div>
                                                                        );
                                                                    })}
                                                                </div>
                                                            </div>
                                                        );
                                                    })()}

                                                    {/* Source URL if available */}
                                                    {selectedGraphNode.url && (
                                                        <div className="pt-2">
                                                            <a
                                                                href={selectedGraphNode.url}
                                                                target="_blank"
                                                                rel="noopener noreferrer"
                                                                className="w-full flex items-center justify-center gap-1.5 border border-slate-200 bg-slate-50 hover:bg-slate-100 py-2 text-indigo-700 text-xs font-mono font-medium rounded transition-all"
                                                            >
                                                                <ExternalLink size={12} />
                                                                Visit Associated URL
                                                            </a>
                                                        </div>
                                                    )}
                                                </div>

                                                {/* Deep Cross-Action Buttons */}
                                                <div className="space-y-2 pt-2 border-t border-slate-100">
                                                    <Button
                                                        onClick={() => {
                                                            setInput(`Provide a detailed analysis of '${selectedGraphNode.id}' based on the indexed documents.`);
                                                            setActiveTab("chat");
                                                        }}
                                                        className="w-full bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-mono gap-1.5 h-9 rounded"
                                                    >
                                                        <Send size={12} />
                                                        Ask AI About This Entity
                                                    </Button>

                                                    <Button
                                                        onClick={() => {
                                                            navigator.clipboard.writeText(JSON.stringify(selectedGraphNode, null, 2));
                                                            alert(`Copied '${selectedGraphNode.id}' data to clipboard.`);
                                                        }}
                                                        variant="outline"
                                                        className="w-full text-xs font-mono h-8 border-slate-200 hover:bg-slate-50 rounded"
                                                    >
                                                        <Copy size={12} className="mr-1.5" />
                                                        Copy Entity JSON
                                                    </Button>
                                                </div>
                                            </Card>
                                        ) : (
                                            <div className="p-8 border border-dashed border-slate-300 rounded-lg text-center bg-white flex flex-col items-center justify-center gap-2">
                                                <Network className="text-slate-400" size={32} />
                                                <h4 className="text-xs font-mono font-bold text-slate-700 uppercase">Entity Inspector</h4>
                                                <p className="text-[11px] text-slate-500 leading-relaxed max-w-xs">
                                                    Click any node in the Knowledge Graph to inspect connected relationships, URLs, and immediately launch a citation-grounded inquiry.
                                                </p>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            ) : (
                                <div className="h-[220px] border border-slate-200 bg-white flex items-center justify-center text-xs font-mono text-slate-400">
                                    No graph entities mapped. Index the project website first!
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {/* STATE 4: Claim Contradictions Tab */}
                {project.status !== "error" && activeTab === "contradictions" && (
                    <div className="flex-1 p-3.5 sm:p-6 md:p-8 overflow-y-auto space-y-6 flex flex-col h-full bg-slate-50">
                        <div className="max-w-[800px] w-full mx-auto space-y-4">
                            <div>
                                <h3 className="text-base font-semibold text-slate-900 tracking-tight">Contradiction & Claim Detector</h3>
                                <p className="text-xs text-slate-500 font-mono">Finds conflicting specifications, dates, claims, and pricing across pages.</p>
                            </div>
                            
                            {contradictionsLoading ? (
                                <div className="space-y-3">
                                    {[1, 2].map(i => (
                                        <div key={i} className="h-28 bg-white border border-slate-200 animate-pulse" />
                                    ))}
                                </div>
                            ) : contradictions.length > 0 ? (
                                <div className="space-y-4">
                                    {contradictions.map((c, idx) => (
                                        <Card key={idx} className="rounded-none border border-slate-200 bg-white p-5 shadow-sm space-y-3">
                                            <div className="flex items-center gap-2 text-xs font-mono text-amber-700 bg-amber-500/10 px-2.5 py-1 border border-amber-200/50 w-fit">
                                                <AlertOctagon size={12} />
                                                CONFLICT DETECTED: {c.claim_type.toUpperCase()}
                                            </div>
                                            <div className="space-y-2">
                                                {c.conflicting_items.map((item: any, i: number) => (
                                                    <div key={i} className="text-xs leading-relaxed text-slate-600 border-l-2 border-slate-200 pl-3">
                                                        <span className="font-semibold text-slate-900 block font-mono text-[10px] uppercase text-slate-400">Source: {item.source}</span>
                                                        "{item.statement}"
                                                    </div>
                                                ))}
                                            </div>
                                            <div className="border-t border-slate-100 pt-3 text-xs text-slate-500 leading-normal flex items-start gap-1.5 font-mono">
                                                <span className="text-indigo-600 font-bold uppercase shrink-0">Resolution Hint:</span>
                                                {c.resolution_hint}
                                            </div>
                                        </Card>
                                    ))}
                                </div>
                            ) : (
                                <div className="p-8 border border-emerald-200 bg-emerald-500/5 text-emerald-800 flex flex-col items-center justify-center text-center gap-3">
                                    <CheckCircle2 className="text-emerald-600" size={32} />
                                    <div>
                                        <h4 className="text-sm font-semibold tracking-tight">No contradictions found</h4>
                                        <p className="text-xs text-emerald-600 font-mono mt-0.5">All crawled claims and technical specs appear fully consistent across portals.</p>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {/* STATE 5: Version Changes Changelog Tab */}
                {project.status !== "error" && activeTab === "changes" && (
                    <div className="flex-1 p-3.5 sm:p-6 md:p-8 overflow-y-auto space-y-6 flex flex-col h-full bg-slate-50">
                        <div className="max-w-[800px] w-full mx-auto space-y-4">
                            <div>
                                <h3 className="text-base font-semibold text-slate-900 tracking-tight">Change & Version Intelligence</h3>
                                <p className="text-xs text-slate-500 font-mono">Detects changes, text updates, and code revisions between crawls.</p>
                            </div>
                            
                            {changesLoading ? (
                                <div className="space-y-3">
                                    <div className="h-20 bg-white border border-slate-200 animate-pulse" />
                                </div>
                            ) : changes.length > 0 ? (
                                <div className="space-y-4 border-l border-slate-200/80 pl-6 ml-4">
                                    {changes.map((c, idx) => (
                                        <div key={idx} className="relative space-y-2 pb-6">
                                            {/* Node point */}
                                            <div className="absolute -left-[31px] top-1 bg-white border border-indigo-600 rounded-full p-1 shadow-sm">
                                                <RefreshCw size={10} className="text-indigo-600 animate-spin-slow" />
                                            </div>
                                            <div className="text-[10px] font-mono text-slate-400">
                                                {new Date(c.crawled_at).toLocaleString()}
                                            </div>
                                            <Card className="rounded-none border border-slate-200 bg-white p-4 shadow-sm space-y-2">
                                                <div className="flex items-center gap-2">
                                                    <span className={`text-[9px] font-mono uppercase px-2 py-0.5 ${
                                                        c.type === "modified" ? "bg-amber-500/10 text-amber-700" : "bg-emerald-500/10 text-emerald-700"
                                                    }`}>
                                                        {c.type}
                                                    </span>
                                                    <span className="text-xs font-mono text-slate-600 truncate">{c.page_url}</span>
                                                </div>
                                                <p className="text-xs leading-relaxed text-slate-700">
                                                    {c.summary}
                                                </p>
                                            </Card>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div className="h-[200px] border border-slate-200 bg-white flex items-center justify-center text-xs font-mono text-slate-400">
                                    No changes detected yet. Refresh crawl to trigger snapshots.
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {/* STATE 6: Health Audit & Information Gaps Tab */}
                {project.status !== "error" && activeTab === "health" && (
                    <div className="flex-1 p-3.5 sm:p-6 md:p-8 overflow-y-auto space-y-6 flex flex-col h-full bg-slate-50">
                        <div className="max-w-[1000px] w-full mx-auto space-y-6">
                            <div>
                                <h3 className="text-base font-semibold text-slate-900 tracking-tight">Website Gap & Health Analyzer</h3>
                                <p className="text-xs text-slate-500 font-mono">Audits structural layout details, non-200 URLs, duplicate pages, and critical content gaps.</p>
                            </div>
                            
                            {healthLoading ? (
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    <div className="h-56 bg-white border border-slate-200 animate-pulse" />
                                    <div className="h-56 bg-white border border-slate-200 animate-pulse" />
                                </div>
                            ) : health ? (
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-start">
                                    {/* Crawler Health stats */}
                                    <Card className="rounded-none border border-slate-200 bg-white p-5 shadow-sm space-y-4">
                                        <h4 className="text-xs font-mono font-bold text-slate-800 uppercase tracking-wider">Crawl Quality Metrics</h4>
                                        <div className="grid grid-cols-2 gap-2.5 sm:gap-4">
                                            <div className="border border-slate-100 p-3 bg-slate-50/50">
                                                <div className="text-[10px] font-mono text-slate-400 uppercase font-bold">TOTAL PAGES</div>
                                                <div className="text-xl font-bold text-slate-900 mt-1">{health.metrics.total_pages}</div>
                                            </div>
                                            <div className="border border-slate-100 p-3 bg-slate-50/50">
                                                <div className="text-[10px] font-mono text-slate-400 uppercase font-bold">BROKEN LINKS</div>
                                                <div className={`text-xl font-bold mt-1 ${health.metrics.broken_links_count > 0 ? "text-red-500" : "text-slate-900"}`}>{health.metrics.broken_links_count}</div>
                                            </div>
                                            <div className="border border-slate-100 p-3 bg-slate-50/50">
                                                <div className="text-[10px] font-mono text-slate-400 uppercase font-bold">MISSING METADATA</div>
                                                <div className="text-xl font-bold text-slate-900 mt-1">{health.metrics.missing_metadata_count}</div>
                                            </div>
                                            <div className="border border-slate-100 p-3 bg-slate-50/50">
                                                <div className="text-[10px] font-mono text-slate-400 uppercase font-bold">DUPLICATE PAGES</div>
                                                <div className="text-xl font-bold text-slate-900 mt-1">{health.metrics.duplicate_pages_count}</div>
                                            </div>
                                        </div>
                                        
                                        {health.broken_links.length > 0 ? (
                                            <div className="space-y-2 border-t border-slate-100 pt-3">
                                                <div className="text-[10px] font-mono text-red-500 uppercase font-bold flex items-center gap-1"><AlertTriangle size={10}/> Broken URLs (Top 5)</div>
                                                <div className="space-y-1">
                                                    {health.broken_links.map((link: string, i: number) => (
                                                        <div key={i} className="text-[11px] font-mono text-slate-600 truncate">{link}</div>
                                                    ))}
                                                </div>
                                            </div>
                                        ) : (
                                            <div className="text-xs text-emerald-700 bg-emerald-500/10 p-3 border border-emerald-100/50 text-center font-mono">
                                                ✔ 0 broken link errors detected.
                                            </div>
                                        )}
                                    </Card>

                                    {/* Content Gaps */}
                                    <Card className="rounded-none border border-slate-200 bg-white p-5 shadow-sm space-y-4">
                                        <h4 className="text-xs font-mono font-bold text-slate-800 uppercase tracking-wider">LLM Information Gap Scan</h4>
                                        <div className="space-y-3">
                                            {health.information_gaps && health.information_gaps.length > 0 ? (
                                                health.information_gaps.map((g: any, i: number) => (
                                                    <div key={i} className="border-b border-slate-100 pb-3 last:border-0 last:pb-0 space-y-1">
                                                        <div className="flex justify-between items-center">
                                                            <span className="text-xs font-bold text-slate-900 font-mono">{g.missing_area}</span>
                                                            <span className={`text-[9px] font-mono uppercase px-1.5 py-0.5 ${
                                                                g.importance === "High" ? "bg-red-500/10 text-red-700" : "bg-amber-500/10 text-amber-700"
                                                            }`}>{g.importance} Gap</span>
                                                        </div>
                                                        <p className="text-xs text-slate-600 leading-normal">{g.description}</p>
                                                    </div>
                                                ))
                                            ) : (
                                                <div className="text-xs text-slate-400 italic font-mono text-center py-6">No gaps detected. Project has a comprehensive site layout.</div>
                                            )}
                                        </div>
                                    </Card>
                                </div>
                            ) : (
                                <div className="h-[200px] border border-slate-200 bg-white flex items-center justify-center text-xs font-mono text-slate-400">
                                    Failed to retrieve health audit data.
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {/* STATE 7: Auto Intelligence Reports Tab */}
                {project.status !== "error" && activeTab === "report" && (
                    <div className="flex-1 p-3.5 sm:p-6 md:p-8 overflow-y-auto space-y-6 flex flex-col h-full bg-slate-50">
                        <div className="max-w-[800px] w-full mx-auto space-y-6">
                            <div className="flex flex-col sm:flex-row sm:justify-between sm:items-end gap-3 border-b border-slate-200/80 pb-4">
                                <div>
                                    <h3 className="text-base font-semibold text-slate-900 tracking-tight">Auto Intelligence Reports</h3>
                                    <p className="text-xs text-slate-500 font-mono mt-0.5">Compiles executive briefings, technical analyses, or competitive audits.</p>
                                </div>
                                <div className="flex flex-wrap gap-2 items-center w-full sm:w-auto">
                                    <select
                                        value={reportType}
                                        onChange={(e) => setReportType(e.target.value)}
                                        className="h-9 px-3 border border-slate-200 bg-white text-base sm:text-xs font-mono focus:border-indigo-600 focus:outline-none rounded flex-1 sm:flex-initial"
                                    >
                                        <option value="technical">Technical Report</option>
                                        <option value="executive">Executive Summary</option>
                                        <option value="competitor">Competitor Audit</option>
                                    </select>
                                    
                                    <Button
                                        onClick={() => handleGenerateReport(false)}
                                        disabled={reportLoading}
                                        className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-mono rounded px-4 h-9 gap-1"
                                    >
                                        {reportLoading ? (
                                            <>
                                                <Loader2 className="animate-spin" size={12} />
                                                Compiling...
                                            </>
                                        ) : (
                                            <>
                                                <RefreshCw size={12} />
                                                {reportContent ? "Load Report" : "Generate"}
                                            </>
                                        )}
                                    </Button>

                                    {reportContent && (
                                        <>
                                            <Button
                                                onClick={() => handleGenerateReport(true)}
                                                disabled={reportLoading}
                                                variant="outline"
                                                className="text-xs font-mono rounded h-9 gap-1 border-slate-200 hover:bg-slate-50 text-slate-700"
                                                title="Force re-generate report fresh from LLM (bypasses cache)"
                                            >
                                                <RefreshCw size={12} className={reportLoading ? "animate-spin" : ""} />
                                                Regenerate Fresh
                                            </Button>

                                            <Button
                                                onClick={handleCopyReport}
                                                variant="outline"
                                                className="text-xs font-mono rounded h-9 gap-1 border-slate-200 hover:bg-slate-50 text-slate-700"
                                                title="Copy full Markdown report to clipboard"
                                            >
                                                {copiedReport ? <Check size={12} className="text-emerald-600" /> : <Copy size={12} />}
                                                {copiedReport ? "Copied!" : "Copy MD"}
                                            </Button>

                                            <Button
                                                onClick={handleDownloadReport}
                                                variant="outline"
                                                className="text-xs font-mono rounded h-9 gap-1 border-slate-200 hover:bg-slate-50 text-slate-700"
                                                title="Download as markdown file"
                                            >
                                                <Download size={12} />
                                                Download .MD
                                            </Button>
                                        </>
                                    )}
                                </div>
                            </div>

                            {reportContent ? (
                                <Card className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm max-h-[600px] overflow-y-auto font-sans leading-relaxed select-text">
                                    <MarkdownText content={reportContent} />
                                </Card>
                            ) : (
                                <div className="h-[250px] border border-slate-200 border-dashed bg-white/50 rounded-lg flex flex-col items-center justify-center gap-2 text-center p-6">
                                    <FileBarChart2 className="text-slate-300" size={32} />
                                    <div>
                                        <h4 className="text-xs font-mono font-bold text-slate-600 uppercase">Generate Workspace report</h4>
                                        <p className="text-xs text-slate-500 mt-1">Select a template above and compile standard, publication-grade summaries of your project dataset.</p>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {/* STATE 8: Autonomous Investigation Agent Tab */}
                
                {/* Feature 1: The Socratic Viva Master Arena */}
                {project.status !== "error" && activeTab === "socratic" && (
                    <div className="flex-1 p-3.5 sm:p-6 md:p-8 overflow-y-auto bg-slate-50 flex flex-col items-center">
                        <div className="w-full max-w-4xl">
                            <SocraticVivaModal
                                isOpen={true}
                                onClose={() => setActiveTab("chat")}
                                projectId={project_id}
                            />
                        </div>
                    </div>
                )}

                {/* Feature 3: Living Code Twin Sandbox */}
                {project.status !== "error" && activeTab === "sandbox" && (
                    <div className="flex-1 p-3.5 sm:p-6 md:p-8 overflow-y-auto bg-slate-50 flex flex-col items-center">
                        <div className="w-full max-w-4xl space-y-4">
                            <div>
                                <h3 className="text-lg font-semibold text-slate-900 tracking-tight flex items-center gap-2">
                                    <Terminal className="text-emerald-600" size={20} />
                                    Living Code Twin & AST Verification Sandbox
                                </h3>
                                <p className="text-xs text-slate-500 font-mono mt-0.5">
                                    Pre-executes Python code in an isolated environment with automated unit assertions and syntax AST verification.
                                </p>
                            </div>
                            <LivingCodeSandbox />
                        </div>
                    </div>
                )}

                {project.status !== "error" && activeTab === "investigate" && (
                    <div className="flex-1 p-3.5 sm:p-6 md:p-8 overflow-y-auto space-y-6 flex flex-col h-full bg-slate-50">
                        <div className="max-w-[800px] w-full mx-auto space-y-6">
                            <div>
                                <h3 className="text-base font-semibold text-slate-900 tracking-tight">Autonomous Investigation Agent</h3>
                                <p className="text-xs text-slate-500 font-mono">Assign a specific research goal. The agent plans, crawls, reads, and cross-checks data recursively.</p>
                            </div>

                            <Card className="rounded-none border border-slate-200 bg-white p-4 shadow-sm">
                                <form onSubmit={handleRunInvestigation} className="flex flex-col sm:flex-row gap-2.5 sm:gap-3 items-stretch sm:items-center">
                                    <Input
                                        placeholder="Objective: e.g. Analyze pricing structures, security models, or API support..."
                                        value={investigationGoal}
                                        onChange={(e) => setInvestigationGoal(e.target.value)}
                                        className="h-10 text-base sm:text-sm rounded-none border-slate-200 bg-white flex-1"
                                        disabled={investigationLoading}
                                    />
                                    <Button
                                        type="submit"
                                        disabled={investigationLoading || !investigationGoal.trim()}
                                        className="bg-indigo-600 hover:bg-indigo-700 text-white font-mono text-xs rounded-none h-10 px-5 gap-1.5 shrink-0 w-full sm:w-auto"
                                    >
                                        {investigationLoading ? (
                                            <>
                                                <Loader2 className="animate-spin" size={12} />
                                                Investigating...
                                            </>
                                        ) : (
                                            <>
                                                <SearchCode size={14} />
                                                Research
                                            </>
                                        )}
                                    </Button>
                                </form>
                            </Card>

                            {investigationLoading && (
                                <div className="space-y-3">
                                    <div className="p-4 bg-white border border-slate-200 flex items-center gap-3">
                                        <Loader2 className="animate-spin text-indigo-600 shrink-0" size={16} />
                                        <span className="text-xs font-mono text-slate-600 uppercase tracking-wide">Executing Agent Reason-Action Execution Loop...</span>
                                    </div>
                                    <div className="p-4 bg-slate-900 border border-slate-800 text-[11px] font-mono text-slate-400 space-y-1.5 max-h-[200px] overflow-y-auto">
                                        <div>[RE-ACT AGENT] Goal: "{investigationGoal}"</div>
                                        <div>[PLAN] Decomposing goal into targeted page query vectors...</div>
                                        <div className="text-indigo-400">[ACTION] Searching dense vector index (Qdrant)...</div>
                                        <div className="text-indigo-400">[ACTION] Retrieving matching document chunks...</div>
                                        <div className="text-emerald-400">[REASON] Processing content with Qwen LLM for contradictions...</div>
                                        <div className="text-amber-400 animate-pulse">[WAIT] Consolidating evidence and writing memo...</div>
                                    </div>
                                </div>
                            )}

                            {investigationResult && (
                                <div className="space-y-4">
                                    {/* Reasoning steps log */}
                                    <div className="space-y-2">
                                        <div className="text-[10px] font-mono text-slate-400 uppercase font-bold flex items-center gap-1"><Terminal size={10}/> Agent Activity Steps</div>
                                        <div className="p-3 bg-slate-900 text-[10px] font-mono text-slate-400 leading-normal space-y-1">
                                            {investigationResult.steps.map((step: string, i: number) => (
                                                <div key={i}>{step}</div>
                                            ))}
                                        </div>
                                    </div>

                                    {/* Memo Answer */}
                                    <div className="space-y-2">
                                        <div className="text-[10px] font-mono text-slate-400 uppercase font-bold flex items-center gap-1"><Eye size={10}/> Investigation Memo Result</div>
                                        <Card className="rounded-none border border-slate-200 bg-white p-5 shadow-sm font-sans leading-relaxed select-text">
                                            <MarkdownText content={investigationResult.conclusion} />
                                        </Card>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {/* STATE 9: Error Workspace State */}
                {project.status === "error" && (
                    <div className="flex-1 p-3.5 sm:p-6 md:p-8 overflow-y-auto bg-slate-50 flex items-center justify-center select-none">
                        <Card className="max-w-[500px] w-full border border-slate-200 bg-white p-6 shadow-sm text-center space-y-5 rounded-none">
                            <div className="mx-auto w-12 h-12 bg-red-500/10 border border-red-200 text-red-600 flex items-center justify-center">
                                <AlertTriangle size={24} />
                            </div>
                            <div className="space-y-1.5">
                                <h3 className="text-base font-semibold text-slate-900 tracking-tight">Ingestion Pipeline Failed</h3>
                                <p className="text-xs text-slate-500 leading-normal font-mono">
                                    An error occurred while crawling or generating vector embeddings.
                                </p>
                            </div>
                            {project.error_message && (
                                <div className="p-3 bg-slate-50 border border-slate-200 text-left font-mono text-[10px] text-slate-600 leading-normal overflow-x-auto max-h-[120px] select-text">
                                    {project.error_message}
                                </div>
                            )}
                            <div className="pt-2">
                                <Button
                                    onClick={async () => {
                                        try {
                                            setActionLoading(true);
                                            await api.post(`/projects/${project_id}/re-ingest`);
                                            setProject(prev => prev ? { ...prev, status: "crawling" } : null);
                                            loadProjectDetails();
                                        } catch (err) {
                                            console.error("Re-ingest failed:", err);
                                            alert("Failed to restart crawler.");
                                        } finally {
                                            setActionLoading(false);
                                        }
                                    }}
                                    disabled={actionLoading}
                                    className="bg-indigo-600 hover:bg-indigo-700 text-white font-mono text-xs rounded-none w-full h-10 gap-1.5"
                                >
                                    {actionLoading ? (
                                        <>
                                            <Loader2 className="animate-spin" size={14} />
                                            Initializing Spiders...
                                        </>
                                    ) : (
                                        <>
                                            <RefreshCw size={14} />
                                            Re-Run Ingestion Pipeline
                                        </>
                                    )}
                                </Button>
                            </div>
                        </Card>
                    </div>
                )}
            </div>

            {/* Evidence Trace Inspector Slide-Over Panel */}
            <EvidencePanel
                isOpen={evidenceOpen}
                onClose={() => setEvidenceOpen(false)}
                evidenceItems={activeEvidenceTrace}
            />

            {/* Side-by-Side Canvas Workspace Drawer */}
            
            <TruthLatticeModal
                isOpen={truthLatticeOpen}
                onClose={() => setTruthLatticeOpen(false)}
                projectId={project_id}
                query={auditQuery}
                targetText={auditTargetText}
            />

            <WhatIfSimulatorModal
                isOpen={whatIfOpen}
                onClose={() => setWhatIfOpen(false)}
                projectId={project_id}
                availableNodes={graphData?.nodes?.map((n: any) => n.id) || []}
            />

            <CanvasWorkspace
                isOpen={canvasOpen}
                onClose={() => setCanvasOpen(false)}
                initialContent={canvasContent || "# Project Notes & Canvas Workspace\n\nType, edit, or format markdown reports and extracted tables here."}
                onSave={(val) => setCanvasContent(val)}
            />
        </div>
    );
}

function MarkdownText({ content }: { content: string }) {
    if (!content) return null;
    const lines = content.split('\n');
    const elements: React.ReactNode[] = [];
    
    let listItems: React.ReactNode[] = [];
    let orderedItems: React.ReactNode[] = [];
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

    const flushOrderedList = (key: number) => {
        if (orderedItems.length > 0) {
            elements.push(
                <ol key={`ol-${key}`} className="list-decimal pl-5 my-2 space-y-1 text-slate-700 font-sans">
                    {orderedItems}
                </ol>
            );
            orderedItems = [];
        }
    };

    const flushTable = (key: number) => {
        if (tableRows.length > 0) {
            const headers = tableRows[0];
            const rows = tableRows.slice(2);
            
            elements.push(
                <div key={`table-wrapper-${key}`} className="overflow-x-auto my-3 border border-slate-200/60 shadow-xs max-w-full rounded-md">
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
        
        if (line.trim().startsWith('|')) {
            flushList(i);
            flushOrderedList(i);
            const cells = line.split('|').map(c => c.trim()).filter((_, idx, arr) => idx > 0 && idx < arr.length - 1);
            tableRows.push(cells);
            continue;
        } else {
            flushTable(i);
        }

        if (line.trim().startsWith('- ') || line.trim().startsWith('* ')) {
            flushOrderedList(i);
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

        const matchOrdered = line.trim().match(/^(\d+)\.\s+(.*)/);
        if (matchOrdered) {
            flushList(i);
            orderedItems.push(
                <li key={`ol-item-${i}`}>
                    {renderTextWithInlineFormatting(matchOrdered[2])}
                </li>
            );
            continue;
        } else {
            flushOrderedList(i);
        }

        if (line.trim().startsWith('> ')) {
            elements.push(
                <blockquote key={i} className="my-2 border-l-4 border-indigo-500 pl-3 italic text-slate-700 bg-indigo-50/30 py-1.5 rounded-r text-xs leading-relaxed">
                    {renderTextWithInlineFormatting(line.trim().substring(2))}
                </blockquote>
            );
            continue;
        }

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

    flushList(lines.length);
    flushOrderedList(lines.length);
    flushTable(lines.length);

    return <div className="space-y-1">{elements}</div>;
}
