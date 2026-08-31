"use client";

import React, { useState, useRef, useEffect } from "react";
import { Send, User, Bot, RotateCcw, AlertTriangle } from "lucide-react";
import axios from "axios";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Citation } from "@/components/ui/citation";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { chatService, ChatHistoryItem } from "@/services/chat.service";
import { featuresService } from "@/services/features.service";

interface Message {
    id: string;
    role: "user" | "assistant";
    content: string;
    citations?: any[];
    isGrounded?: boolean;
    verificationLabel?: string;
    verificationConfidence?: number;
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
    const scrollRef = useRef<HTMLDivElement>(null);
    const [messages, setMessages] = useState<Message[]>([]);

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
                        citations: item.sources.map(s => s.page), // Simplify for now
                        isGrounded: true
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
        const words = fullText.split(" ");
        let currentText = "";

        for (let i = 0; i < words.length; i++) {
            currentText += (i === 0 ? "" : " ") + words[i];
            setMessages(prev => prev.map(m =>
                m.id === aiMsgId ? { ...m, content: currentText } : m
            ));
            // Type faster for longer responses
            const delay = Math.max(10, 50 - words.length / 5);
            await new Promise(resolve => setTimeout(resolve, delay));
        }
    };

    const handleSend = async () => {
        if (!input.trim()) return;

        const userMsg: Message = { id: Date.now().toString(), role: "user", content: input };
        setMessages(prev => [...prev, userMsg]);
        setInput("");
        setIsLoading(true);

        // Add placeholder AI message for "streaming"
        const aiMsgId = (Date.now() + 1).toString();
        const placeholderAiMsg: Message = {
            id: aiMsgId,
            role: "assistant",
            content: "",
            isGrounded: true
        };
        setMessages(prev => [...prev, placeholderAiMsg]);

        try {
            const response = await chatService.sendMessage(docId, userMsg.content, strictMode);
            setIsLoading(false); // Stop thinking indicator before starting to type

            // Update AI message with metadata but keep content empty for streaming
            setMessages(prev => prev.map(m =>
                m.id === aiMsgId ? {
                    ...m,
                    citations: response.sources.map(s => s.page),
                    isGrounded: response.grounded,
                    verificationLabel: response.support_label,
                    verificationConfidence: response.support_confidence
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
                m.id === aiMsgId ? { ...m, content: errorText, isGrounded: false } : m
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
        <div className="flex flex-col h-full">
            {/* Top Bar */}
            <div className="h-14 border-b border-border flex items-center justify-between px-6 bg-surface/50 backdrop-blur">
                <div className="flex items-center gap-3">
                    <div className="h-2 w-2 rounded-full bg-accent animate-pulse" />
                    <span className="font-mono text-xs text-text-secondary uppercase">Active Session</span>
                </div>
                <div className="flex gap-2">
                    <Button
                        variant="ghost"
                        size="sm"
                        className={`h-8 text-xs ${strictMode ? 'text-accent' : 'text-text-muted'} hover:text-text-primary`}
                        onClick={() => setStrictMode((v) => !v)}
                    >
                        Trust Mode: {strictMode ? "ON" : "OFF"}
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
                                <span className="text-xs font-mono text-text-muted uppercase">{msg.role === "user" ? "You" : "DevFrames Synapse"}</span>
                                {msg.role === "assistant" && (
                                    msg.isGrounded ? (
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

                                {msg.role === "assistant" && msg.verificationLabel && (
                                    <div className="mt-2 text-[11px] text-text-muted">
                                        Evidence check: {msg.verificationLabel} ({((msg.verificationConfidence || 0) * 100).toFixed(1)}%)
                                    </div>
                                )}

                                {msg.role === "assistant" && msg.content && !isLoading && (
                                    <div className="mt-2">
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            className="h-7 px-2 text-[11px]"
                                            onClick={() => handleSimplify(msg.id, msg.content)}
                                        >
                                            Simplify language
                                        </Button>
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
                                <span className="text-xs font-mono text-text-muted uppercase">DevFrames Synapse</span>
                                <span className="text-[10px] text-text-muted">Thinking...</span>
                            </div>
                            <div className="flex items-center gap-2 h-8">
                                <motion.div animate={{ opacity: [0.4, 1, 0.4] }} transition={{ repeat: Infinity, duration: 1.5 }} className="w-2 h-2 bg-accent rounded-full" />
                                <motion.div animate={{ opacity: [0.4, 1, 0.4] }} transition={{ repeat: Infinity, duration: 1.5, delay: 0.2 }} className="w-2 h-2 bg-accent rounded-full" />
                                <motion.div animate={{ opacity: [0.4, 1, 0.4] }} transition={{ repeat: Infinity, duration: 1.5, delay: 0.4 }} className="w-2 h-2 bg-accent rounded-full" />
                            </div>
                            <div className="text-xs font-mono text-accent">Searching vectors...</div>
                        </div>
                    </div>
                )}
            </div>

            {/* Input Area */}
            <div className="p-6 bg-background max-w-5xl mx-auto w-full">
                <div className="relative">
                    <Input
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && handleSend()}
                        placeholder="Ask anything about this document..."
                        className="pr-24 h-14 bg-surface text-base"
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
                    <div className="flex gap-2 items-center">
                        <span className="h-1.5 w-1.5 rounded-full bg-accent" />
                        <span className="text-[10px] font-mono text-text-muted">HYBRID SEARCH</span>
                        <span className="h-1.5 w-1.5 rounded-full bg-accent ml-2" />
                        <span className="text-[10px] font-mono text-text-muted">RERANKING</span>
                    </div>
                    <div className="text-[10px] font-mono text-text-muted">{input.length} / 1000</div>
                </div>
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
