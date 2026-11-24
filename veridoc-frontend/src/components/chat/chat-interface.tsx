"use client";

import React, { useState, useRef, useEffect } from "react";
import {
    Send, User, Bot, RotateCcw, AlertTriangle, LayoutGrid, Eye, Globe, Sparkles, BookOpen,
    Copy, Check, Volume2, VolumeX, Pencil, ChevronDown, ChevronUp, Square, FileText,
    ClipboardList, ShieldAlert, Pill, Search
} from "lucide-react";
import axios from "axios";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Citation } from "@/components/ui/citation";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { chatService, ChatHistoryItem } from "@/services/chat.service";
import { featuresService } from "@/services/features.service";
import { VoiceInput } from "@/components/chat/VoiceInput";
import { EvidencePanel } from "@/components/chat/EvidencePanel";
import { CanvasWorkspace } from "@/components/canvas/CanvasWorkspace";

const PROMPT_SUGGESTIONS = [
    {
        icon: ClipboardList,
        iconColor: "text-blue-600 bg-blue-50/80 border-blue-200/80",
        title: "Summarize Protocol & Objectives",
        prompt: "Provide an executive summary of this document, highlighting primary objectives, methodology, and key clinical findings."
    },
    {
        icon: ShieldAlert,
        iconColor: "text-amber-600 bg-amber-50/80 border-amber-200/80",
        title: "Audit Safety & Contraindications",
        prompt: "What are the reported adverse reactions, contraindications, and critical safety parameters highlighted in this document?"
    },
    {
        icon: Pill,
        iconColor: "text-emerald-600 bg-emerald-50/80 border-emerald-200/80",
        title: "Dosage & Patient Eligibility",
        prompt: "Detail the dosage regimens, administration schedules, inclusion criteria, and exclusion criteria specified in this document."
    },
    {
        icon: Search,
        iconColor: "text-purple-600 bg-purple-50/80 border-purple-200/80",
        title: "Explain Clinical Terminology",
        prompt: "Identify and explain the key clinical, pharmacological, and regulatory terms mentioned in this document in clear language."
    }
];

interface Message {
    id: string;
    role: "user" | "assistant";
    content: string;
    citations?: any[];
    isGrounded?: boolean;
    verificationLabel?: string;
    verificationConfidence?: number;
    evidence_trace?: any[];
    questionRef?: string;
    isGeneralAI?: boolean;
    inferenceMode?: string;
}

function formatErrorDetail(detail: unknown): string | undefined {
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
        const parts = detail.map(formatErrorDetail).filter(Boolean);
        return parts.length ? parts.join(", ") : undefined;
    }
    if (detail && typeof detail === "object") {
        const errorObject = detail as Record<string, unknown>;
        const message = errorObject.msg ?? errorObject.message ?? errorObject.detail;
        if (typeof message === "string") return message;
        try {
            return JSON.stringify(detail);
        } catch {
            return String(detail);
        }
    }
    return undefined;
}

interface ChatInterfaceProps {
    docId: string;
    onCitationClick: (page: number) => void;
    onToggleDocs?: () => void;
    onToggleInsights?: () => void;
}

export function ChatInterface({
    docId,
    onCitationClick,
    onToggleDocs,
    onToggleInsights
}: ChatInterfaceProps) {
    const [input, setInput] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [strictMode, setStrictMode] = useState(true);
    const [chatMode, setChatMode] = useState<"document" | "general">("document");
    const [reasoningLevel, setReasoningLevel] = useState<"fast" | "balanced" | "deep">("balanced");
    const [messages, setMessages] = useState<Message[]>([]);
    
    // Drawers State
    const [evidenceOpen, setEvidenceOpen] = useState(false);
    const [activeEvidenceTrace, setActiveEvidenceTrace] = useState<any[]>([]);
    const [activeQuestion, setActiveQuestion] = useState<string>("");
    const [canvasOpen, setCanvasOpen] = useState(false);
    const [canvasContent, setCanvasContent] = useState("");

    // Claude UX Enhancements State
    const [copiedId, setCopiedId] = useState<string | null>(null);
    const [speakingId, setSpeakingId] = useState<string | null>(null);
    const [expandedThoughtId, setExpandedThoughtId] = useState<string | null>(null);
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const stopStreamingRef = useRef<boolean>(false);

    useEffect(() => {
        return () => {
            if (typeof window !== "undefined" && "speechSynthesis" in window) {
                window.speechSynthesis.cancel();
            }
        };
    }, []);

    const handleCopy = async (id: string, text: string) => {
        try {
            await navigator.clipboard.writeText(text);
            setCopiedId(id);
            setTimeout(() => setCopiedId(null), 2000);
        } catch (e) {
            console.error("Failed to copy", e);
        }
    };

    const handleToggleSpeech = (id: string, text: string) => {
        if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
        if (speakingId === id) {
            window.speechSynthesis.cancel();
            setSpeakingId(null);
            return;
        }
        window.speechSynthesis.cancel();
        const cleanText = text.replace(/[*#_`\[\]()|>-]/g, " ").replace(/\s+/g, " ").trim();
        const utterance = new SpeechSynthesisUtterance(cleanText);
        utterance.rate = 1.0;
        utterance.onend = () => setSpeakingId(null);
        utterance.onerror = () => setSpeakingId(null);
        window.speechSynthesis.speak(utterance);
        setSpeakingId(id);
    };

    const handleEditUserMessage = (content: string) => {
        setInput(content);
        if (textareaRef.current) {
            textareaRef.current.style.height = "auto";
            setTimeout(() => {
                if (textareaRef.current) {
                    textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
                    textareaRef.current.focus();
                }
            }, 0);
        }
    };

    const handleSelectPrompt = (promptText: string) => {
        setInput(promptText);
        if (textareaRef.current) {
            textareaRef.current.style.height = "auto";
            setTimeout(() => {
                if (textareaRef.current) {
                    textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
                    textareaRef.current.focus();
                }
            }, 0);
        }
    };

    const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        setInput(e.target.value);
        if (textareaRef.current) {
            textareaRef.current.style.height = "auto";
            textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const handleStopStreaming = () => {
        stopStreamingRef.current = true;
        setIsLoading(false);
    };
    
    const scrollRef = useRef<HTMLDivElement>(null);

    // Load history on mount
    useEffect(() => {
        if (!docId) return;

        const loadHistory = async () => {
            try {
                const history = await chatService.getHistory(docId);
                const formatted: Message[] = history.flatMap((item, i) => [
                    { id: `q-${i}`, role: "user", content: item.question },
                    {
                        id: `a-${i}`,
                        role: "assistant",
                        content: item.answer,
                        citations: item.sources.map(s => s.page),
                        isGrounded: true,
                        questionRef: item.question
                    }
                ]);

                if (formatted.length === 0) {
                    setMessages([{
                        id: "intro",
                        role: "assistant",
                        content: "I'm ready to answer questions about this document.",
                        isGrounded: true
                    }]);
                } else {
                    setMessages(formatted);
                }
            } catch (e) {
                console.error("Failed to load history", e);
            }
        };
        loadHistory();
    }, [docId]);

    const simulateStreaming = async (fullText: string, aiMsgId: string) => {
        if (!fullText) return;
        stopStreamingRef.current = false;
        const words = fullText.split(" ");
        let currentText = "";
        const chunkSize = words.length > 150 ? 3 : 1;
        for (let i = 0; i < words.length; i += chunkSize) {
            if (stopStreamingRef.current) break;
            const chunk = words.slice(i, i + chunkSize).join(" ");
            currentText += (i === 0 ? "" : " ") + chunk;
            setMessages(prev => prev.map(m =>
                m.id === aiMsgId ? { ...m, content: currentText } : m
            ));
            await new Promise(resolve => setTimeout(resolve, 20));
        }
        if (!stopStreamingRef.current) {
            setMessages(prev => prev.map(m =>
                m.id === aiMsgId ? { ...m, content: fullText } : m
            ));
        }
    };

    const handleAskGeneralAI = async (question: string) => {
        if (!question.trim() || isLoading) return;

        setIsLoading(true);
        const aiMsgId = (Date.now() + 1).toString();
        const placeholderAiMsg: Message = {
            id: aiMsgId,
            role: "assistant",
            content: "",
            isGrounded: true,
            isGeneralAI: true,
            questionRef: question
        };
        setMessages(prev => [...prev, placeholderAiMsg]);

        try {
            const response = await chatService.askGeneralAI(question, docId);
            setIsLoading(false);

            setMessages(prev => prev.map(m =>
                m.id === aiMsgId ? {
                    ...m,
                    isGrounded: true,
                    isGeneralAI: true,
                    questionRef: question,
                    verificationLabel: "World Knowledge Base (Groq)",
                    verificationConfidence: 1.0,
                    evidence_trace: response.evidence_trace || []
                } : m
            ));

            await simulateStreaming(response.answer, aiMsgId);
        } catch (err) {
            console.error("[General AI Error]", err);
            setIsLoading(false);
            setMessages(prev => prev.map(m =>
                m.id === aiMsgId ? {
                    ...m,
                    content: "Unable to query General AI at this moment. Please try again.",
                    isGrounded: false
                } : m
            ));
        }
    };

    const executeDocumentQuery = async (queryText: string) => {
        setIsLoading(true);

        const aiMsgId = (Date.now() + 1).toString();
        const placeholderAiMsg: Message = {
            id: aiMsgId,
            role: "assistant",
            content: "",
            isGrounded: true,
            questionRef: queryText
        };
        setMessages(prev => [...prev, placeholderAiMsg]);

        try {
            const response = await chatService.sendMessage(docId, queryText, strictMode);
            setIsLoading(false);

            setMessages(prev => prev.map(m =>
                m.id === aiMsgId ? {
                    ...m,
                    citations: response.sources.map(s => s.page),
                    isGrounded: response.grounded,
                    verificationLabel: response.support_label,
                    verificationConfidence: response.support_confidence,
                    evidence_trace: response.evidence_trace || [],
                    questionRef: queryText,
                    inferenceMode: (response as any).inference_mode
                } : m
            ));

            await simulateStreaming(response.answer, aiMsgId);
        } catch (err) {
            console.error("[CHAT ERROR]", err);
            setIsLoading(false);
            let errorText = "Sorry, I encountered an error answering that.";
            if (axios.isAxiosError(err)) {
                const status = err.response?.status;
                const detail = formatErrorDetail(err.response?.data?.detail);
                if (detail) {
                    errorText = `Error${status ? ` (${status})` : ""}: ${detail}`;
                }
            }
            setMessages(prev => prev.map(m =>
                m.id === aiMsgId ? { ...m, content: errorText, isGrounded: false, questionRef: queryText } : m
            ));
        }
    };

    const handleSend = async () => {
        if (!input.trim() || isLoading) return;

        const currentInput = input.trim();
        const userMsg: Message = { id: Date.now().toString(), role: "user", content: currentInput };
        setMessages(prev => [...prev, userMsg]);
        setInput("");
        if (textareaRef.current) {
            textareaRef.current.style.height = "auto";
        }

        if (chatMode === "general") {
            await handleAskGeneralAI(currentInput);
        } else {
            await executeDocumentQuery(currentInput);
        }
    };

    const handleDirectVoiceSend = async (voiceText: string) => {
        if (!voiceText.trim() || isLoading) return;

        const currentInput = voiceText.trim();
        const userMsg: Message = { id: Date.now().toString(), role: "user", content: currentInput };
        setMessages(prev => [...prev, userMsg]);
        setInput("");
        if (textareaRef.current) {
            textareaRef.current.style.height = "auto";
        }

        if (chatMode === "general") {
            await handleAskGeneralAI(currentInput);
        } else {
            await executeDocumentQuery(currentInput);
        }
    };

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages, isLoading]);

    const handleClearMemory = async () => {
        if (confirm("Are you sure you want to clear the chat history for this document?")) {
            await chatService.clearMemory(docId);
            setMessages([{
                id: "intro",
                role: "assistant",
                content: "Memory cleared. Start a fresh conversation.",
                isGrounded: true
            }]);
        }
    };

    const handleSimplify = async (id: string, text: string) => {
        try {
            const rewritten = await featuresService.rewriteSimple(text, "simple");
            setMessages(prev => prev.map(m =>
                m.id === id ? { ...m, content: rewritten.rewritten_text || m.content } : m
            ));
        } catch (e) {
            console.error("Failed to simplify answer", e);
        }
    };

    return (
        <div className="flex flex-col h-full relative">
            {/* Top Bar */}
            <div className="h-13 sm:h-14 border-b border-border flex items-center justify-between px-2.5 sm:px-6 bg-surface/70 backdrop-blur-md gap-1.5 sm:gap-2 overflow-x-auto no-scrollbar shrink-0 z-10">
                <div className="flex items-center gap-2 sm:gap-3 shrink-0">
                    {onToggleDocs && (
                        <button
                            onClick={onToggleDocs}
                            className="lg:hidden flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-mono font-medium rounded-lg border border-border bg-surface hover:bg-slate-100 text-text-secondary active:scale-95 transition-all shadow-2xs"
                            title="Open Document Index"
                        >
                            <BookOpen size={13} className="text-accent" />
                            <span className="hidden sm:inline">Docs</span>
                        </button>
                    )}
                    <div className="h-2 w-2 rounded-full bg-accent animate-pulse" />
                    <span className="font-mono text-[11px] sm:text-xs text-text-secondary uppercase truncate max-w-[80px] sm:max-w-none">Session</span>
                </div>

                <div className="flex items-center gap-1 sm:gap-2 shrink-0">
                    {/* Mobile Insights Button */}
                    {onToggleInsights && (
                        <button
                            onClick={onToggleInsights}
                            className="xl:hidden flex items-center gap-1 px-2.5 py-1.5 text-xs font-mono rounded-lg border border-indigo-200 bg-indigo-50/70 text-indigo-700 hover:bg-indigo-100 active:scale-95 transition-all shrink-0"
                            title="Open Document Intelligence"
                        >
                            <Sparkles size={12} />
                            <span className="hidden sm:inline">Insights</span>
                        </button>
                    )}

                    {/* Reasoning Selector */}
                    <div className="hidden sm:flex items-center gap-0.5 p-0.5 bg-slate-100 rounded-lg border border-slate-200 text-[10px] font-mono shrink-0">
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

                    {/* Canvas Workspace Button */}
                    <button
                        onClick={() => setCanvasOpen(true)}
                        className="flex items-center gap-1 text-[11px] font-mono px-2.5 py-1.5 transition-all border border-purple-200 bg-purple-50 text-purple-700 hover:bg-purple-100/80 rounded-lg shrink-0 active:scale-95"
                        title="Open side-by-side interactive Canvas Workspace"
                    >
                        <LayoutGrid size={12} />
                        <span className="hidden sm:inline">Canvas Workspace</span>
                        <span className="sm:hidden">Canvas</span>
                    </button>

                    <Button
                        variant="ghost"
                        size="sm"
                        className={`h-8 px-2 sm:px-2.5 text-[11px] font-mono rounded-lg ${strictMode ? 'text-accent bg-accent/5 border border-accent/20' : 'text-text-muted'} hover:text-text-primary shrink-0 active:scale-95`}
                        onClick={() => setStrictMode((v) => !v)}
                        title="Toggle strict grounding verification"
                    >
                        {strictMode ? "STRICT" : "RELAXED"}
                    </Button>

                    <Button 
                        variant="ghost" 
                        size="sm" 
                        className="h-8 px-2 sm:px-2 text-[11px] font-mono rounded-lg text-text-muted hover:text-text-primary shrink-0 active:scale-95" 
                        onClick={handleClearMemory} 
                        title="Clear Memory"
                    >
                        <RotateCcw size={12} className="sm:mr-1" />
                        <span className="hidden sm:inline">Clear</span>
                    </Button>
                </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-3 sm:p-6 space-y-4 sm:space-y-6" ref={scrollRef}>
                {messages.map((msg) => (
                    <motion.div
                        key={msg.id}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className={cn(
                            "flex gap-2.5 sm:gap-4 max-w-3xl mx-auto w-full group",
                            msg.role === "user" ? "flex-row-reverse" : "flex-row"
                        )}
                    >
                        <div className={cn(
                            "h-7 w-7 sm:h-8 sm:w-8 rounded-sm flex items-center justify-center shrink-0 border",
                            msg.role === "user" ? "bg-surface-high border-border" : "bg-accent/10 border-accent/20"
                        )}>
                            {msg.role === "user" ? <User size={14} className="sm:size-4" /> : <Bot size={14} className="text-accent sm:size-4" />}
                        </div>

                        <div className={cn(
                            "flex flex-col gap-1.5 sm:gap-2 min-w-0 max-w-[88%] sm:max-w-none",
                            msg.role === "user" ? "items-end" : "items-start"
                        )}>
                            <div className="flex items-center gap-2">
                                <span className="text-xs font-mono text-text-muted uppercase">
                                    {msg.role === "user" ? "You" : (msg.isGeneralAI ? "Global AI Assistant" : "Document Assistant")}
                                </span>
                                {msg.role === "user" && (
                                    <button
                                        type="button"
                                        onClick={() => handleEditUserMessage(msg.content)}
                                        className="opacity-0 group-hover:opacity-100 transition-opacity p-0.5 text-text-muted hover:text-text-primary rounded"
                                        title="Edit this question"
                                    >
                                        <Pencil size={11} />
                                    </button>
                                )}
                                {msg.role === "assistant" && (
                                    <>
                                        {msg.isGeneralAI ? (
                                            <span className="text-[10px] bg-indigo-50 text-indigo-700 px-1.5 py-0.5 rounded border border-indigo-200 flex items-center gap-1 font-mono font-medium">
                                                <Globe size={10} /> GLOBAL WORLD KNOWLEDGE
                                            </span>
                                        ) : msg.isGrounded ? (
                                            <span className="text-[10px] bg-accent/10 text-accent px-1.5 py-0.5 rounded border border-accent/20 font-mono">GROUNDED</span>
                                        ) : (
                                            <span className="text-[10px] bg-red-500/10 text-red-500 px-1.5 py-0.5 rounded border border-red-500/20 flex items-center gap-1 font-mono">
                                                <AlertTriangle size={8} /> UNVERIFIED
                                            </span>
                                        )}
                                    </>
                                )}
                                <span className="text-[10px] text-text-muted">Just now</span>
                            </div>

                            <div className={cn(
                                "rounded-lg p-4 text-sm leading-relaxed w-full",
                                msg.role === "user"
                                    ? "bg-surface text-text-primary border border-border"
                                    : "bg-transparent text-text-primary pl-0 pt-0"
                            )}>
                                {msg.role === "user" ? (
                                    msg.content
                                ) : (
                                    <MarkdownText content={msg.content} />
                                )}

                                {/* "Not Found in Document" Banner with 1-Click General AI Action */}
                                {msg.role === "assistant" && !msg.isGeneralAI && (msg.content.toLowerCase().includes("could not find this information") || msg.content.toLowerCase().includes("not found")) && msg.questionRef && !isLoading && (
                                    <div className="mt-3 p-3.5 rounded-xl bg-gradient-to-r from-indigo-50/90 via-purple-50/70 to-slate-50 border border-indigo-200 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                                        <div className="space-y-0.5">
                                            <div className="flex items-center gap-1.5 text-xs font-semibold text-indigo-950">
                                                <Globe size={14} className="text-indigo-600" />
                                                <span>Not In Uploaded Document</span>
                                            </div>
                                            <p className="text-[11px] text-slate-600 leading-normal">
                                                Would you like General AI to explain <strong className="text-slate-900 font-semibold">"{msg.questionRef}"</strong> using open world knowledge?
                                            </p>
                                        </div>
                                        <button
                                            onClick={() => handleAskGeneralAI(msg.questionRef!)}
                                            className="px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium shadow-xs flex items-center gap-1.5 shrink-0 transition-all active:scale-95"
                                        >
                                            <Sparkles size={12} />
                                            Ask General AI Directly
                                        </button>
                                    </div>
                                )}

                                {/* Claude-Style Collapsible Thinking / Verification Drawer */}
                                {msg.role === "assistant" && msg.content && !isLoading && (
                                    <div className="w-full mt-3 border border-border/80 rounded-xl overflow-hidden bg-slate-50/60 shadow-2xs">
                                        <button
                                            type="button"
                                            onClick={() => setExpandedThoughtId(prev => prev === msg.id ? null : msg.id)}
                                            className="w-full flex items-center justify-between px-3 py-2 text-[11px] font-mono text-text-secondary hover:bg-slate-100/70 transition-colors"
                                        >
                                            <div className="flex items-center gap-1.5">
                                                <Sparkles size={11} className="text-accent" />
                                                <span className="font-semibold text-slate-800">Reasoning & Grounding Trace</span>
                                                {msg.verificationConfidence !== undefined && (
                                                    <span className="text-[10px] text-indigo-700 bg-indigo-50 px-1.5 py-0.2 rounded border border-indigo-200 ml-1">
                                                        {((msg.verificationConfidence || 0) * 100).toFixed(0)}% verified
                                                    </span>
                                                )}
                                            </div>
                                            {expandedThoughtId === msg.id ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                                        </button>
                                        {expandedThoughtId === msg.id && (
                                            <div className="p-3 border-t border-border/50 text-[11px] font-mono space-y-2 bg-white">
                                                <div className="flex items-center justify-between">
                                                    <span className="text-text-muted">Inference Pipeline:</span>
                                                    <span className="text-slate-900 font-medium">
                                                        {msg.inferenceMode || (msg.isGeneralAI ? "Groq LLaMA 3.3 70B (Open Knowledge)" : "Dense Vector RAG + Cohere Rerank")}
                                                    </span>
                                                </div>
                                                <div className="flex items-center justify-between">
                                                    <span className="text-text-muted">Grounding Status:</span>
                                                    <span className={msg.isGrounded ? "text-emerald-700 font-medium" : "text-amber-700 font-medium"}>
                                                        {msg.verificationLabel || (msg.isGrounded ? "Verified Grounded Against Source" : "Unverified / Outside Scope")}
                                                    </span>
                                                </div>
                                                {msg.evidence_trace && msg.evidence_trace.length > 0 && (
                                                    <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
                                                        <span className="text-text-muted">Retrieved Chunks:</span>
                                                        <button
                                                            type="button"
                                                            onClick={() => {
                                                                setActiveEvidenceTrace(msg.evidence_trace || []);
                                                                setActiveQuestion(msg.questionRef || msg.content);
                                                                setEvidenceOpen(true);
                                                            }}
                                                            className="text-accent hover:underline text-[11px] font-semibold flex items-center gap-1 active:scale-95 transition-all"
                                                        >
                                                            <Eye size={11} /> View {msg.evidence_trace.length} Evidence Chunks
                                                        </button>
                                                    </div>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                )}

                                {/* Claude-Style Response Actions Toolbar */}
                                {msg.role === "assistant" && msg.content && !isLoading && (
                                    <div className="mt-2.5 flex items-center gap-1.5 flex-wrap">
                                        {/* 1-Click Copy */}
                                        <button
                                            type="button"
                                            onClick={() => handleCopy(msg.id, msg.content)}
                                            className="flex items-center gap-1 px-2 py-1 border border-border/80 hover:bg-slate-100 text-[10px] font-mono text-text-secondary rounded-md transition-colors active:scale-95 shadow-2xs"
                                            title="Copy message to clipboard"
                                        >
                                            {copiedId === msg.id ? (
                                                <>
                                                    <Check size={11} className="text-emerald-600" />
                                                    <span className="text-emerald-700 font-medium">Copied!</span>
                                                </>
                                            ) : (
                                                <>
                                                    <Copy size={11} />
                                                    <span>Copy</span>
                                                </>
                                            )}
                                        </button>

                                        {/* Audio Readout (TTS) */}
                                        <button
                                            type="button"
                                            onClick={() => handleToggleSpeech(msg.id, msg.content)}
                                            className={cn(
                                                "flex items-center gap-1 px-2 py-1 border text-[10px] font-mono rounded-md transition-colors active:scale-95 shadow-2xs",
                                                speakingId === msg.id
                                                    ? "border-rose-300 bg-rose-50 text-rose-700 font-semibold animate-pulse"
                                                    : "border-border/80 hover:bg-slate-100 text-text-secondary"
                                            )}
                                            title={speakingId === msg.id ? "Stop voice readout" : "Listen to audio readout"}
                                        >
                                            {speakingId === msg.id ? (
                                                <>
                                                    <VolumeX size={11} className="text-rose-600" />
                                                    <span>Stop Audio</span>
                                                </>
                                            ) : (
                                                <>
                                                    <Volume2 size={11} />
                                                    <span>Read Aloud</span>
                                                </>
                                            )}
                                        </button>

                                        {/* Simplify language */}
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            className="h-6 px-2 text-[10px] font-mono rounded-md border border-border/60 hover:bg-slate-100"
                                            onClick={() => handleSimplify(msg.id, msg.content)}
                                        >
                                            Simplify
                                        </Button>

                                        {/* Edit in Canvas */}
                                        <button
                                            onClick={() => {
                                                setCanvasContent(msg.content);
                                                setCanvasOpen(true);
                                            }}
                                            className="flex items-center gap-1 px-2 py-1 border border-purple-300/60 bg-purple-50/50 text-[10px] font-mono text-purple-800 hover:bg-purple-100 transition-colors rounded-md active:scale-95 shadow-2xs"
                                            title="Send this response to Canvas for live editing & export"
                                        >
                                            <LayoutGrid size={10} />
                                            Edit in Canvas
                                        </button>

                                        {/* Ask General AI */}
                                        <button
                                            onClick={() => handleAskGeneralAI(msg.questionRef || msg.content)}
                                            className="flex items-center gap-1 px-2 py-1 border border-indigo-300/60 bg-indigo-50/60 text-[10px] font-mono text-indigo-800 hover:bg-indigo-100 transition-colors rounded-md active:scale-95 shadow-2xs"
                                            title="Ask General AI directly on this topic"
                                        >
                                            <Globe size={10} />
                                            Ask General AI
                                        </button>
                                    </div>
                                )}

                                {/* Inline Citations */}
                                {msg.citations && msg.citations.length > 0 && (
                                    <div className="mt-3 flex flex-wrap gap-2 pt-3 border-t border-border/50">
                                        <span className="text-xs font-mono text-text-muted mr-1 flex items-center">SOURCES:</span>
                                        {msg.citations.map((p, i) => (
                                            <Citation key={i} page={p} onClick={() => onCitationClick(p)} />
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                    </motion.div>
                ))}

                {isLoading && (
                    <div className="flex gap-4 max-w-3xl mx-auto">
                        <div className="h-8 w-8 rounded-sm bg-accent/10 border border-accent/20 flex items-center justify-center shrink-0">
                            <Bot size={16} className="text-accent" />
                        </div>
                        <div className="flex flex-col gap-2">
                            <div className="flex items-center gap-2">
                                <span className="text-xs font-mono text-text-muted uppercase">Document Assistant</span>
                                <span className="text-[10px] text-text-muted">Thinking & Synthesizing...</span>
                            </div>
                            <div className="flex items-center gap-2 h-8">
                                <motion.div animate={{ opacity: [0.4, 1, 0.4] }} transition={{ repeat: Infinity, duration: 1.5 }} className="w-2 h-2 bg-accent rounded-full" />
                                <motion.div animate={{ opacity: [0.4, 1, 0.4] }} transition={{ repeat: Infinity, duration: 1.5, delay: 0.2 }} className="w-2 h-2 bg-accent rounded-full" />
                                <motion.div animate={{ opacity: [0.4, 1, 0.4] }} transition={{ repeat: Infinity, duration: 1.5, delay: 0.4 }} className="w-2 h-2 bg-accent rounded-full" />
                            </div>
                            <div className="text-xs font-mono text-accent">Searching document vectors & reranking evidence...</div>
                        </div>
                    </div>
                )}
            </div>

            {/* Input Area */}
            <div className="p-2.5 sm:p-5 bg-background max-w-4xl mx-auto w-full pb-[max(0.75rem,env(safe-area-inset-bottom))] border-t border-border/50 sm:border-0 shrink-0">
                {/* Claude-Style Prompt Starter Chips (when conversation is new or empty) */}
                {messages.length <= 1 && !isLoading && (
                    <div className="mb-3 animate-in fade-in duration-300">
                        <div className="flex items-center gap-1.5 mb-2 text-[11px] font-mono text-text-muted">
                            <Sparkles size={12} className="text-accent" />
                            <span>Quick review prompts:</span>
                        </div>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                            {PROMPT_SUGGESTIONS.map((item, idx) => {
                                const IconComponent = item.icon;
                                return (
                                    <button
                                        key={idx}
                                        type="button"
                                        onClick={() => handleSelectPrompt(item.prompt)}
                                        className="p-2.5 rounded-xl border border-border/80 bg-surface hover:bg-slate-50 hover:border-accent/40 hover:shadow-xs transition-all text-left flex items-start gap-2.5 group active:scale-[0.99]"
                                    >
                                        <span className={cn("p-1.5 rounded-lg border flex items-center justify-center shrink-0 transition-all group-hover:scale-105", item.iconColor)}>
                                            <IconComponent size={14} />
                                        </span>
                                        <div className="min-w-0">
                                            <div className="text-xs font-semibold text-text-primary group-hover:text-accent transition-colors truncate">
                                                {item.title}
                                            </div>
                                            <div className="text-[11px] text-text-muted truncate">
                                                {item.prompt}
                                            </div>
                                        </div>
                                    </button>
                                );
                            })}
                        </div>
                    </div>
                )}

                {/* Claude-Style Multi-Line Auto-Growing Input Card */}
                <div className="flex flex-col bg-surface border border-border focus-within:border-accent/70 focus-within:ring-2 focus-within:ring-accent/15 rounded-2xl shadow-xs transition-all duration-200">
                    {/* Multiline Textarea */}
                    <div className="relative w-full">
                        <textarea
                            ref={textareaRef}
                            value={input}
                            onChange={handleTextareaChange}
                            onKeyDown={handleKeyDown}
                            placeholder={chatMode === "general" ? "Ask any open general question... (Shift+Enter for newline)" : "Ask anything about this document... (Shift+Enter for newline)"}
                            rows={1}
                            className="w-full bg-transparent border-0 px-3.5 pt-3 pb-2 text-[13px] sm:text-[14px] leading-relaxed text-text-primary placeholder:text-text-muted focus:outline-none resize-none min-h-[48px] max-h-44 overflow-y-auto block"
                        />
                    </div>

                    {/* Dedicated Bottom Actions Toolbar */}
                    <div className="flex items-center justify-between px-2.5 py-1.5 sm:px-3 sm:py-2 bg-slate-50/70 border-t border-border/50 gap-2 flex-wrap sm:flex-nowrap">
                        {/* Left: Scope Selector & Voice Controls */}
                        <div className="flex items-center gap-1.5 flex-wrap">
                            {/* Knowledge Scope Selector */}
                            <div className="flex items-center gap-0.5 p-0.5 bg-slate-200/60 rounded-lg border border-slate-200/80">
                                <button
                                    type="button"
                                    onClick={() => setChatMode("document")}
                                    className={cn(
                                        "px-2 py-1 text-[11px] font-medium rounded-md flex items-center gap-1 transition-all active:scale-95",
                                        chatMode === "document"
                                            ? "bg-white text-slate-900 shadow-xs border border-slate-200"
                                            : "text-slate-600 hover:text-slate-900"
                                    )}
                                    title="Restrict queries to document context and evidence"
                                >
                                    <BookOpen size={11} className={chatMode === "document" ? "text-accent" : ""} />
                                    <span>Doc Scope</span>
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setChatMode("general")}
                                    className={cn(
                                        "px-2 py-1 text-[11px] font-medium rounded-md flex items-center gap-1 transition-all active:scale-95",
                                        chatMode === "general"
                                            ? "bg-indigo-600 text-white shadow-xs font-medium"
                                            : "text-slate-600 hover:text-indigo-600"
                                    )}
                                    title="Query Groq Cloud LLM for broad world knowledge"
                                >
                                    <Globe size={11} />
                                    <span>General AI</span>
                                </button>
                            </div>

                            {/* Voice Dictation with persistent Auto-Send */}
                            <VoiceInput
                                onTranscript={(txt) => setInput(prev => prev ? `${prev} ${txt}` : txt)}
                                onSendVoiceQuery={(txt) => handleDirectVoiceSend(txt)}
                                isGenerating={isLoading}
                            />
                        </div>

                        {/* Right: Character count and Send / Stop button */}
                        <div className="flex items-center gap-2 ml-auto shrink-0">
                            <span className="text-[10px] font-mono text-text-muted">{input.length} / 1000</span>

                            {isLoading ? (
                                <Button
                                    size="sm"
                                    variant="danger"
                                    onClick={handleStopStreaming}
                                    className="h-8 px-3 text-xs rounded-xl flex items-center gap-1.5 shadow-xs animate-pulse"
                                    title="Stop generation"
                                >
                                    <Square size={11} className="fill-current" />
                                    <span>Stop</span>
                                </Button>
                            ) : (
                                <Button
                                    size="sm"
                                    variant="primary"
                                    onClick={() => handleSend()}
                                    disabled={!input.trim()}
                                    className="h-8 px-3 sm:px-3.5 text-xs rounded-xl flex items-center gap-1.5 shadow-xs active:scale-95 transition-all"
                                >
                                    <Send size={12} />
                                    <span className="hidden sm:inline">Send</span>
                                </Button>
                            )}
                        </div>
                    </div>
                </div>

                <div className="flex justify-between items-center mt-1.5 px-1 gap-2">
                    <div className="text-[9px] sm:text-[10px] font-mono text-text-muted truncate">
                        {chatMode === "general" ? "Prompting Groq Cloud LLM (Open World Knowledge)" : "Hybrid Dense Vector + Cohere Rerank • Grounded verification active"}
                    </div>
                    <div className="text-[9px] sm:text-[10px] font-mono text-text-muted hidden sm:block">
                        Press Enter to send, Shift+Enter for new line
                    </div>
                </div>
            </div>

            {/* Evidence Inspector Drawer */}
            <EvidencePanel
                isOpen={evidenceOpen}
                onClose={() => setEvidenceOpen(false)}
                evidenceItems={activeEvidenceTrace}
                question={activeQuestion}
                onAskGeneralAI={handleAskGeneralAI}
                onJumpToPage={onCitationClick}
            />

            {/* Canvas Workspace Drawer */}
            <CanvasWorkspace
                isOpen={canvasOpen}
                onClose={() => setCanvasOpen(false)}
                initialContent={canvasContent || "# Document Notes & Canvas Workspace\n\nType, edit, or format markdown reports and extracted tables here."}
                onSave={(val) => setCanvasContent(val)}
                onInsertToChat={(text) => {
                    setInput(text);
                    setCanvasOpen(false);
                }}
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
