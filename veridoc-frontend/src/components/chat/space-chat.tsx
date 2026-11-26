"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import type { FormEvent, KeyboardEvent } from "react";
import { ArrowUp, BookOpen, FileText, Globe, Loader2, MessageSquareText, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { chatService, ChatHistoryItem, SourceCitation } from "@/services/chat.service";
import { documentService, DocumentOut } from "@/services/document.service";
import { projectService, ProjectOut } from "@/services/project.service";

interface SpaceMessage {
    role: "user" | "assistant";
    content: string;
    sources?: SourceCitation[];
}

function sourceHref(source: SourceCitation): string | undefined {
    if (!source.source_id) return undefined;
    return source.source_type === "project"
        ? `/dashboard/projects/${source.source_id}`
        : `/dashboard/chat/${source.source_id}`;
}

export function SpaceChat() {
    const [messages, setMessages] = useState<SpaceMessage[]>([]);
    const [input, setInput] = useState("");
    const [documents, setDocuments] = useState<DocumentOut[]>([]);
    const [projects, setProjects] = useState<ProjectOut[]>([]);
    const [loadingSources, setLoadingSources] = useState(true);
    const [sourceError, setSourceError] = useState("");
    const [sending, setSending] = useState(false);
    const [strictMode, setStrictMode] = useState(false);
    const [error, setError] = useState("");
    const messagesEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        let mounted = true;
        const loadSpace = async () => {
            const [documentResult, projectResult, historyResult] = await Promise.allSettled([
                documentService.list(),
                projectService.list(),
                chatService.getHistory("space"),
            ]);
            if (!mounted) return;

            if (documentResult.status === "fulfilled") {
                setDocuments(documentResult.value.documents);
            } else {
                setSourceError("Could not load your saved documents.");
            }
            if (projectResult.status === "fulfilled") {
                setProjects(projectResult.value.projects);
            } else {
                setSourceError("Could not load your knowledge projects.");
            }
            if (historyResult.status === "fulfilled") {
                setMessages(historyResult.value.flatMap((item: ChatHistoryItem) => [
                    { role: "user" as const, content: item.question },
                    { role: "assistant" as const, content: item.answer, sources: item.sources },
                ]));
            }
            setLoadingSources(false);
        };
        void loadSpace();
        return () => {
            mounted = false;
        };
    }, []);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, sending]);

    const readyDocuments = documents.filter((document) => document.status === "ready");
    const activeProjects = projects.filter((project) => project.status === "active");
    const sourceCount = readyDocuments.length + activeProjects.length;

    const sendQuestion = async (event?: FormEvent) => {
        event?.preventDefault();
        const question = input.trim();
        if (!question || sending || sourceCount === 0) return;

        setInput("");
        setError("");
        setMessages((current) => [...current, { role: "user", content: question }]);
        setSending(true);
        try {
            const response = await chatService.askSpace(question, strictMode);
            setMessages((current) => [
                ...current,
                { role: "assistant", content: response.answer, sources: response.sources },
            ]);
        } catch (requestError) {
            const response = requestError && typeof requestError === "object" && "response" in requestError
                ? (requestError as { response?: { data?: { detail?: unknown } } }).response
                : undefined;
            const detail = response?.data?.detail;
            setError(typeof detail === "string" ? detail : "Your space couldn’t answer just now. Please try again.");
        } finally {
            setSending(false);
        }
    };

    const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            void sendQuestion();
        }
    };

    return (
        <div className="mx-auto flex min-h-[calc(100vh-60px)] w-full max-w-5xl flex-col p-4 sm:p-6 md:p-8">
            <header className="mb-5 flex flex-col gap-4 border-b border-border/70 pb-5 sm:flex-row sm:items-center sm:justify-between">
                <div>
                    <p className="mb-1 flex items-center gap-2 font-mono text-xs uppercase tracking-[0.16em] text-accent">
                        <Sparkles size={14} /> Your knowledge, together
                    </p>
                    <h1 className="font-display text-2xl sm:text-3xl">Ask Your Space</h1>
                    <p className="mt-1 text-sm text-text-muted">
                        Ask one question across your ready documents and active knowledge projects.
                    </p>
                </div>
                <Link href="/dashboard/capture">
                    <Button variant="ghost" className="gap-2">
                        <Sparkles size={15} /> Capture a source
                    </Button>
                </Link>
            </header>

            <div className="mb-4 flex flex-wrap items-center gap-3 text-xs text-text-muted" aria-live="polite">
                <span className="inline-flex items-center gap-1.5">
                    <FileText size={14} /> {loadingSources ? "Loading sources..." : `${readyDocuments.length} ready documents`}
                </span>
                <span className="inline-flex items-center gap-1.5">
                    <Globe size={14} /> {loadingSources ? "" : `${activeProjects.length} active projects`}
                </span>
                <span className="inline-flex items-center gap-1.5">
                    <BookOpen size={14} /> Answers include source links
                </span>
            </div>

            {sourceError && <p className="mb-3 text-sm text-amber-600" role="status">{sourceError}</p>}

            <Card className="flex min-h-[50vh] flex-1 flex-col overflow-hidden border-border/70 bg-surface-high/10">
                <div className="flex-1 space-y-5 overflow-y-auto p-4 sm:p-6" aria-live="polite">
                    {messages.length === 0 && (
                        <div className="flex min-h-[35vh] flex-col items-center justify-center px-4 text-center">
                            <span className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-accent/10 text-accent">
                                <MessageSquareText size={25} />
                            </span>
                            <h2 className="font-display text-xl">One question. All your sources.</h2>
                            {loadingSources ? (
                                <Loader2 className="mt-4 animate-spin text-accent" size={20} />
                            ) : sourceCount > 0 ? (
                                <p className="mt-2 max-w-md text-sm text-text-muted">
                                    Try: “What are the common themes across my notes?” or ask about a detail you saved.
                                </p>
                            ) : (
                                <p className="mt-2 max-w-md text-sm text-text-muted">
                                    Capture a PDF, note, image, audio clip, or link first. Once it’s ready, ask questions across your sources here.
                                </p>
                            )}
                        </div>
                    )}

                    {messages.map((message, index) => (
                        <div key={`${message.role}-${index}`} className={message.role === "user" ? "flex justify-end" : "flex justify-start"}>
                            <div className={message.role === "user"
                                ? "max-w-[90%] rounded-2xl rounded-br-sm bg-accent px-4 py-3 text-sm text-white sm:max-w-[80%]"
                                : "max-w-[95%] space-y-3 rounded-2xl rounded-bl-sm border border-border bg-background px-4 py-3 text-sm text-text-primary sm:max-w-[85%]"}
                            >
                                <div className="whitespace-pre-wrap leading-6">{message.content}</div>
                                {message.role === "assistant" && Boolean(message.sources?.length) && (
                                    <div className="border-t border-border/70 pt-3">
                                        <p className="mb-2 text-[10px] font-mono uppercase tracking-wider text-text-muted">Sources</p>
                                        <div className="flex flex-wrap gap-2">
                                            {message.sources?.map((source) => {
                                                const href = sourceHref(source);
                                                const label = `${source.source_name || "Saved source"}${source.page > 1 ? ` · p. ${source.page}` : ""}`;
                                                return href ? (
                                                    <Link
                                                        key={source.chunk_id}
                                                        href={href}
                                                        className="max-w-full truncate rounded-md border border-border px-2.5 py-1.5 text-xs text-accent hover:border-accent/60"
                                                        title={source.snippet}
                                                    >
                                                        {label}
                                                    </Link>
                                                ) : (
                                                    <span
                                                        key={source.chunk_id}
                                                        className="max-w-full truncate rounded-md border border-border px-2.5 py-1.5 text-xs text-text-muted"
                                                        title={source.snippet}
                                                    >
                                                        {label}
                                                    </span>
                                                );
                                            })}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}

                    {sending && (
                        <div className="flex items-center gap-2 text-sm text-text-muted" role="status">
                            <Loader2 size={16} className="animate-spin text-accent" />
                            Searching your sources and checking the evidence...
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>

                <form onSubmit={(event) => void sendQuestion(event)} className="border-t border-border/70 bg-background/70 p-3 sm:p-4">
                    {error && <p className="mb-2 text-sm text-red-500" role="alert">{error}</p>}
                    <div className="flex items-end gap-2">
                        <textarea
                            value={input}
                            onChange={(event) => setInput(event.target.value)}
                            onKeyDown={handleKeyDown}
                            disabled={sourceCount === 0 || sending}
                            rows={2}
                            maxLength={1000}
                            placeholder={sourceCount > 0 ? "Ask across your saved sources..." : "Capture a source to start asking"}
                            className="min-h-12 flex-1 resize-y rounded-xl border border-border bg-background px-4 py-3 text-sm outline-none transition focus:border-accent disabled:cursor-not-allowed disabled:opacity-60"
                        />
                        <Button type="submit" disabled={!input.trim() || sourceCount === 0 || sending} size="icon" aria-label="Ask your space">
                            {sending ? <Loader2 className="animate-spin" size={17} /> : <ArrowUp size={18} />}
                        </Button>
                    </div>
                    <label className="mt-3 flex items-center gap-2 text-xs text-text-muted">
                        <input
                            type="checkbox"
                            checked={strictMode}
                            onChange={(event) => setStrictMode(event.target.checked)}
                            className="accent-accent"
                        />
                        Strict evidence mode — only answer when sources support it
                    </label>
                </form>
            </Card>
        </div>
    );
}