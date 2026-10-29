"use client";

import React, { useState, useRef, useEffect } from "react";
import { Send, User, Bot, RotateCcw, AlertTriangle, LayoutGrid, Eye, Globe, Sparkles, BookOpen } from "lucide-react";
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

export function ChatInterface({ docId, onCitationClick }: { docId: string, onCitationClick: (page: number) => void }) {
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
        const words = fullText.split(" ");
        let currentText = "";
        const chunkSize = words.length > 150 ? 3 : 1;
        for (let i = 0; i < words.length; i += chunkSize) {
            const chunk = words.slice(i, i + chunkSize).join(" ");
            currentText += (i === 0 ? "" : " ") + chunk;
            setMessages(prev => prev.map(m =>
                m.id === aiMsgId ? { ...m, content: currentText } : m
            ));
            await new Promise(resolve => setTimeout(resolve, 20));
        }
        setMessages(prev => prev.map(m =>
            m.id === aiMsgId ? { ...m, content: fullText } : m
        ));
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

    const handleSend = async () => {
        if (!input.trim() || isLoading) return;

        const currentInput = input.trim();
        const userMsg: Message = { id: Date.now().toString(), role: "user", content: currentInput };
        setMessages(prev => [...prev, userMsg]);
        setInput("");

        if (chatMode === "general") {
            await handleAskGeneralAI(currentInput);
            return;
        }

        setIsLoading(true);

        const aiMsgId = (Date.now() + 1).toString();
        const placeholderAiMsg: Message = {
            id: aiMsgId,
            role: "assistant",
            content: "",
            isGrounded: true,
            questionRef: currentInput
        };
        setMessages(prev => [...prev, placeholderAiMsg]);

        try {
            const response = await chatService.sendMessage(docId, userMsg.content, strictMode);
            setIsLoading(false);

            setMessages(prev => prev.map(m =>
                m.id === aiMsgId ? {
                    ...m,
                    citations: response.sources.map(s => s.page),
                    isGrounded: response.grounded,
                    verificationLabel: response.support_label,
                    verificationConfidence: response.support_confidence,
                    evidence_trace: response.evidence_trace || [],
                    questionRef: currentInput
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
                m.id === aiMsgId ? { ...m, content: errorText, isGrounded: false, questionRef: currentInput } : m
            ));
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
            <div className="h-14 border-b border-border flex items-center justify-between px-6 bg-surface/50 backdrop-blur">
                <div className="flex items-center gap-3">
                    <div className="h-2 w-2 rounded-full bg-accent animate-pulse" />
                    <span className="font-mono text-xs text-text-secondary uppercase">Active Session</span>
                </div>

                <div className="flex items-center gap-3">
                    {/* Reasoning Selector */}
                    <div className="hidden md:flex items-center gap-1 p-0.5 bg-slate-100 rounded-lg border border-slate-200 text-[10px] font-mono">
                        {(["fast", "balanced", "deep"] as const).map((level) => (
                            <button
                                key={level}
                                onClick={() => setReasoningLevel(level)}
                                className={`px-2 py-0.5 rounded capitalize transition-all ${
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
                        className="flex items-center gap-1.5 text-[11px] font-mono px-2.5 py-1 transition-all border border-purple-200 bg-purple-50 text-purple-700 hover:bg-purple-100/80 rounded"
                        title="Open side-by-side interactive Canvas Workspace"
                    >
                        <LayoutGrid size={12} />
                        Canvas Workspace
                    </button>

                    <Button
                        variant="ghost"
                        size="sm"
                        className={`h-8 text-xs ${strictMode ? 'text-accent' : 'text-text-muted'} hover:text-text-primary`}
                        onClick={() => setStrictMode((v) => !v)}
                    >
                        STRICT: {strictMode ? "ON" : "OFF"}
                    </Button>

                    <Button variant="ghost" size="sm" className="h-8 text-xs text-text-muted hover:text-text-primary" onClick={handleClearMemory}>
                        <RotateCcw size={14} className="mr-1" /> Clear Memory
                    </Button>
                </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-6 space-y-8" ref={scrollRef}>
                {messages.map((msg) => (
                    <motion.div
                        key={msg.id}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className={cn(
                            "flex gap-4 max-w-3xl mx-auto",
                            msg.role === "user" ? "flex-row-reverse" : "flex-row"
                        )}
                    >
                        <div className={cn(
                            "h-8 w-8 rounded-sm flex items-center justify-center shrink-0 border",
                            msg.role === "user" ? "bg-surface-high border-border" : "bg-accent/10 border-accent/20"
                        )}>
                            {msg.role === "user" ? <User size={16} /> : <Bot size={16} className="text-accent" />}
                        </div>

                        <div className={cn(
                            "flex flex-col gap-2 min-w-0",
                            msg.role === "user" ? "items-end" : "items-start"
                        )}>
                            <div className="flex items-center gap-2">
                                <span className="text-xs font-mono text-text-muted uppercase">
                                    {msg.role === "user" ? "You" : (msg.isGeneralAI ? "Global AI Assistant" : "Document Assistant")}
                                </span>
                                {msg.role === "assistant" && (
                                    msg.isGeneralAI ? (
                                        <span className="text-[10px] bg-indigo-50 text-indigo-700 px-1.5 py-0.5 rounded border border-indigo-200 flex items-center gap-1 font-mono font-medium">
                                            <Globe size={10} /> GLOBAL WORLD KNOWLEDGE
                                        </span>
                                    ) : msg.isGrounded ? (
                                        <span className="text-[10px] bg-accent/10 text-accent px-1.5 py-0.5 rounded border border-accent/20">GROUNDED</span>
                                    ) : (
                                        <span className="text-[10px] bg-red-500/10 text-red-500 px-1.5 py-0.5 rounded border border-red-500/20 flex items-center gap-1">
                                            <AlertTriangle size={8} /> UNVERIFIED
                                        </span>
                                    )
                                )}
                                <span className="text-[10px] text-text-muted">Just now</span>
                            </div>

                            <div className={cn(
                                "rounded-lg p-4 text-sm leading-relaxed",
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

                                {msg.role === "assistant" && msg.verificationLabel && (
                                    <div className="mt-2 text-[11px] text-text-muted">
                                        Evidence check: {msg.verificationLabel} ({((msg.verificationConfidence || 0) * 100).toFixed(1)}%)
                                    </div>
                                )}

                                {msg.role === "assistant" && msg.content && !isLoading && (
                                    <div className="mt-2 flex items-center gap-2 flex-wrap">
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            className="h-7 px-2 text-[11px]"
                                            onClick={() => handleSimplify(msg.id, msg.content)}
                                        >
                                            Simplify language
                                        </Button>

                                        <button
                                            onClick={() => {
                                                setCanvasContent(msg.content);
                                                setCanvasOpen(true);
                                            }}
                                            className="flex items-center gap-1 px-2 py-1 border border-purple-300/60 bg-purple-50/50 text-[10px] font-mono text-purple-800 hover:bg-purple-100 transition-colors rounded"
                                            title="Send this response to Canvas for live editing & export"
                                        >
                                            <LayoutGrid size={10} />
                                            Edit in Canvas
                                        </button>

                                        <button
                                            onClick={() => {
                                                setActiveEvidenceTrace(msg.evidence_trace || []);
                                                setActiveQuestion(msg.questionRef || msg.content);
                                                setEvidenceOpen(true);
                                            }}
                                            className="flex items-center gap-1 px-2 py-1 border border-cyan-300/60 bg-cyan-50/50 text-[10px] font-mono text-cyan-800 hover:bg-cyan-100 transition-colors rounded"
                                            title="Inspect raw RAG evidence chunks and scores"
                                        >
                                            <Eye size={10} />
                                            Why this answer?
                                        </button>

                                        <button
                                            onClick={() => handleAskGeneralAI(msg.questionRef || msg.content)}
                                            className="flex items-center gap-1 px-2 py-1 border border-indigo-300/60 bg-indigo-50/60 text-[10px] font-mono text-indigo-800 hover:bg-indigo-100 transition-colors rounded"
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
                                        <span className="text-xs font-mono text-text-muted mr-1">SOURCES:</span>
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
                                <span className="text-[10px] text-text-muted">Thinking...</span>
                            </div>
                            <div className="flex items-center gap-2 h-8">
                                <motion.div animate={{ opacity: [0.4, 1, 0.4] }} transition={{ repeat: Infinity, duration: 1.5 }} className="w-2 h-2 bg-accent rounded-full" />
                                <motion.div animate={{ opacity: [0.4, 1, 0.4] }} transition={{ repeat: Infinity, duration: 1.5, delay: 0.2 }} className="w-2 h-2 bg-accent rounded-full" />
                                <motion.div animate={{ opacity: [0.4, 1, 0.4] }} transition={{ repeat: Infinity, duration: 1.5, delay: 0.4 }} className="w-2 h-2 bg-accent rounded-full" />
                            </div>
                            <div className="text-xs font-mono text-accent">Searching document vectors...</div>
                        </div>
                    </div>
                )}
            </div>

            {/* Input Area */}
            <div className="p-6 bg-background max-w-5xl mx-auto w-full">
                {/* Knowledge Scope Selector */}
                <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-1 p-0.5 bg-slate-100 rounded-lg border border-slate-200">
                        <button
                            type="button"
                            onClick={() => setChatMode("document")}
                            className={cn(
                                "px-2.5 py-1 text-xs font-medium rounded-md flex items-center gap-1.5 transition-all",
                                chatMode === "document"
                                    ? "bg-white text-slate-900 shadow-xs border border-slate-200"
                                    : "text-slate-500 hover:text-slate-800"
                            )}
                        >
                            <BookOpen size={12} className={chatMode === "document" ? "text-accent" : ""} />
                            Document Scope (RAG)
                        </button>
                        <button
                            type="button"
                            onClick={() => setChatMode("general")}
                            className={cn(
                                "px-2.5 py-1 text-xs font-medium rounded-md flex items-center gap-1.5 transition-all",
                                chatMode === "general"
                                    ? "bg-indigo-600 text-white shadow-xs"
                                    : "text-slate-500 hover:text-indigo-600"
                            )}
                        >
                            <Globe size={12} />
                            General AI (World Knowledge)
                        </button>
                    </div>

                    {chatMode === "general" ? (
                        <span className="text-[11px] font-mono text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded border border-indigo-200">
                            🌐 Open LLM active — ask anything freely
                        </span>
                    ) : (
                        <div className="flex gap-2 items-center">
                            <span className="h-1.5 w-1.5 rounded-full bg-accent" />
                            <span className="text-[10px] font-mono text-text-muted">VECTOR RAG</span>
                            <span className="h-1.5 w-1.5 rounded-full bg-accent ml-1" />
                            <span className="text-[10px] font-mono text-text-muted">RERANKING</span>
                        </div>
                    )}
                </div>

                <div className="relative flex items-center bg-surface border border-border rounded-lg px-3 gap-2">
                    <VoiceInput
                        onTranscript={(txt) => setInput(prev => prev ? `${prev} ${txt}` : txt)}
                        isGenerating={isLoading}
                    />
                    <Input
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && handleSend()}
                        placeholder={chatMode === "general" ? "Ask any general question (e.g. Who is Swami Vivekananda?)..." : "Ask anything about this document..."}
                        className="pr-24 h-14 border-0 focus-visible:ring-0 focus-visible:ring-offset-0 bg-transparent text-base"
                    />
                    <div className="absolute right-2 top-1/2 -translate-y-1/2">
                        <Button
                            size="sm"
                            variant="primary"
                            onClick={handleSend}
                            disabled={!input.trim() || isLoading}
                        >
                            <Send size={16} className="mr-2" />
                            Send
                        </Button>
                    </div>
                </div>
                <div className="flex justify-between mt-2 px-1">
                    <div className="text-[10px] font-mono text-text-muted">
                        {chatMode === "general" ? "Prompting Groq Cloud LLM with full world knowledge" : "Prompting Document vector chunks & hybrid search"}
                    </div>
                    <div className="text-[10px] font-mono text-text-muted">{input.length} / 1000</div>
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
