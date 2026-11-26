"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import type { FormEvent, KeyboardEvent, ReactNode } from "react";
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

function renderInline(text: string): ReactNode[] {
    return text.split(/(\*\*.+?\*\*|`[^`]+`)/g).map((part, index) => {
        if (part.startsWith("**") && part.endsWith("**")) {
            return <strong key={index}>{part.slice(2, -2)}</strong>;
        }
        if (part.startsWith("`") && part.endsWith("`")) {
            return <code key={index} className="rounded bg-surface-high px-1 py-0.5">{part.slice(1, -1)}</code>;
        }
        return <span key={index}>{part}</span>;
    });
}

function isBlockStart(line: string): boolean {
    return /^#{1,3}\s|^\s*[-*]\s+|^\s*\d+[.)]\s+|^>\s?/.test(line) ||
        /^\|.+\|$/.test(line);
}

function parseTableRow(line: string): string[] {
    return line.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((cell) => cell.trim());
}

function FormattedAnswer({ text }: { text: string }) {
    const lines = text.split(/\r?\n/);
    const blocks: ReactNode[] = [];
    let index = 0;

    while (index < lines.length) {
        const line = lines[index].trim();
        if (!line) {
            index += 1;
            continue;
        }

        const heading = /^(#{1,3})\s+(.+)$/.exec(line);
        if (heading) {
            const Heading = heading[1].length === 1 ? "h2" : "h3";
            blocks.push(
                <Heading key={index} className="font-display text-base font-semibold">
                    {renderInline(heading[2])}
                </Heading>
            );
            index += 1;
            continue;
        }

        const bullet = /^\s*[-*]\s+(.+)$/.exec(lines[index]);
        const numbered = /^\s*\d+[.)]\s+(.+)$/.exec(lines[index]);
        if (bullet || numbered) {
            const ordered = Boolean(numbered);
            const items: string[] = [];
            while (index < lines.length) {
                const match = ordered
                    ? /^\s*\d+[.)]\s+(.+)$/.exec(lines[index])
                    : /^\s*[-*]\s+(.+)$/.exec(lines[index]);
                if (!match) break;
                items.push(match[1]);
                index += 1;
            }
            const List = ordered ? "ol" : "ul";
            blocks.push(
                <List key={index} className={ordered ? "list-decimal space-y-1 pl-5" : "list-disc space-y-1 pl-5"}>
                    {items.map((item, itemIndex) => <li key={itemIndex}>{renderInline(item)}</li>)}
                </List>
            );
            continue;
        }

        if (line.startsWith(">")) {
            blocks.push(
                <blockquote key={index} className="border-l-2 border-accent pl-3 text-text-muted">
                    {renderInline(line.replace(/^>\s?/, ""))}
                </blockquote>
            );
            index += 1;
            continue;
        }

        if (
            /^\|.+\|$/.test(line) &&
            index + 1 < lines.length &&
            /^\|?\s*:?-{3,}/.test(lines[index + 1].trim())
        ) {
            const headers = parseTableRow(line);
            index += 2;
            const rows: string[][] = [];
            while (index < lines.length && /^\|.+\|$/.test(lines[index].trim())) {
                rows.push(parseTableRow(lines[index]));
                index += 1;
            }
            blocks.push(
                <div key={index} className="overflow-x-auto">
                    <table className="w-full border-collapse text-left text-sm">
                        <thead>
                            <tr>
                                {headers.map((header, cellIndex) => (
                                    <th key={cellIndex} className="border-b border-border px-3 py-2 font-semibold">
                                        {renderInline(header)}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {rows.map((row, rowIndex) => (
                                <tr key={rowIndex}>
                                    {headers.map((_, cellIndex) => (
                                        <td key={cellIndex} className="border-b border-border/60 px-3 py-2">
                                            {renderInline(row[cellIndex] ?? "")}
                                        </td>
                                    ))}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            );
            continue;
        }

        const paragraph = [line];
        index += 1;
        while (index < lines.length && lines[index].trim() && !isBlockStart(lines[index].trim())) {
            paragraph.push(lines[index].trim());
            index += 1;
        }
        blocks.push(<p key={index}>{renderInline(paragraph.join(" "))}</p>);
    }

    return <div className="space-y-3 leading-6">{blocks}</div>;
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

            {sourceError && <p className="mb-3 text-sm text-blue-600" role="status">{sourceError}</p>}

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
                                {message.role === "assistant"
                                    ? <FormattedAnswer text={message.content} />
                                    : <div className="whitespace-pre-wrap leading-6">{message.content}</div>}
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
                    {error && <p className="mb-2 text-sm text-blue-500" role="alert">{error}</p>}
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