"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
    AlertTriangle,
    AudioLines,
    Check,
    FileText,
    Globe,
    Image as ImageIcon,
    Loader2,
    Link2,
    Mic2,
    Sparkles,
    Upload,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { documentService, DocumentOut } from "@/services/document.service";
import { projectService } from "@/services/project.service";
import { captureSourceFile, waitForCapturedDocument } from "@/lib/source-capture";

type CaptureStatus = "idle" | "processing" | "ready" | "error";

function formatDetail(value: unknown): string | undefined {
    if (typeof value === "string") return value;
    if (Array.isArray(value)) {
        const parts = value.map(formatDetail).filter((part): part is string => Boolean(part));
        return parts.length ? parts.join(", ") : undefined;
    }
    if (value && typeof value === "object") {
        const detail = value as Record<string, unknown>;
        const message = formatDetail(detail.msg ?? detail.message ?? detail.detail);
        const location = Array.isArray(detail.loc)
            ? detail.loc.filter((part) => typeof part === "string").join(".")
            : "";
        return message && location ? `${location}: ${message}` : message;
    }
    return undefined;
}

function getErrorMessage(error: unknown): string {
    if (error && typeof error === "object" && "response" in error) {
        const response = (error as { response?: { data?: { detail?: unknown } } }).response;
        const detail = formatDetail(response?.data?.detail);
        if (detail) return detail;
    }
    if (error instanceof Error) return error.message;
    return "Capture failed. Please try again.";
}

function isYouTubeVideoUrl(url: URL): boolean {
    const host = url.hostname.toLowerCase().replace(/^www\./, "");
    if (host === "youtu.be") return url.pathname.split("/").filter(Boolean).length > 0;
    if (host !== "youtube.com" && host !== "m.youtube.com" && host !== "youtube-nocookie.com") return false;
    return Boolean(
        url.searchParams.get("v") ||
        /^\/(embed|shorts|live)\/[^/]+/.test(url.pathname)
    );
}

export function CaptureAnything() {
    const router = useRouter();
    const fileInputRef = useRef<HTMLInputElement>(null);
    const textInputRef = useRef<HTMLTextAreaElement>(null);
    const [url, setUrl] = useState("");
    const [text, setText] = useState("");
    const [status, setStatus] = useState<CaptureStatus>("idle");
    const [message, setMessage] = useState("");
    const [errorMessage, setErrorMessage] = useState("");
    const [capturedDocument, setCapturedDocument] = useState<DocumentOut | null>(null);
    const [dragActive, setDragActive] = useState(false);
    const [youtubeCaptureFailed, setYoutubeCaptureFailed] = useState(false);

    const startDocumentIndexing = async (document: DocumentOut) => {
        setCapturedDocument(document);
        setStatus("processing");
        const readyDocument = await waitForCapturedDocument(document.id, setMessage);
        setCapturedDocument(readyDocument);
        setStatus("ready");
    };

    const captureFile = async (file: File) => {
        setErrorMessage("");
        setStatus("processing");
        setMessage("Reading your source...");
        try {
            await startDocumentIndexing(await captureSourceFile(file, setMessage));
        } catch (error) {
            setStatus("error");
            setErrorMessage(getErrorMessage(error));
        }
    };

    const captureUrl = async () => {
        const enteredUrl = url.trim();
        let parsedUrl: URL;
        try {
            parsedUrl = new URL(enteredUrl);
            if (!["http:", "https:"].includes(parsedUrl.protocol)) throw new Error();
        } catch {
            throw new Error("Enter a valid webpage or YouTube URL starting with http:// or https://.");
        }

        if (isYouTubeVideoUrl(parsedUrl)) {
            setMessage("Retrieving available video captions...");
            let captured: DocumentOut;
            try {
                captured = await documentService.captureYouTube(enteredUrl);
            } catch (error) {
                setYoutubeCaptureFailed(true);
                throw error;
            }
            await startDocumentIndexing(captured);
            return;
        }

        setMessage("Adding this webpage to a searchable space...");
        const project = await projectService.create({
            name: parsedUrl.hostname.replace(/^www\./, ""),
            website_url: enteredUrl,
            max_pages: 50,
        });
        router.push(`/dashboard/projects/${project.id}`);
    };

    const submit = async () => {
        setErrorMessage("");
        setCapturedDocument(null);
        setStatus("processing");
        try {
            if (url.trim() && text.trim()) {
                const parsedUrl = new URL(url.trim());
                if (!isYouTubeVideoUrl(parsedUrl)) {
                    throw new Error("Capture one source at a time: use a link or pasted text.");
                }
                const videoId = parsedUrl.searchParams.get("v") ||
                    parsedUrl.pathname.split("/").filter(Boolean).pop() ||
                    "video";
                setMessage("Saving your pasted video transcript...");
                await startDocumentIndexing(
                    await documentService.captureText(
                        `YouTube transcript: ${videoId}`,
                        `${text.trim()}\n\nVideo link: ${url.trim()}`
                    )
                );
                return;
            }
            if (url.trim()) {
                await captureUrl();
                return;
            }
            if (!text.trim()) throw new Error("Paste a link or some text, or drop a supported file.");
            setMessage("Saving your text...");
            await startDocumentIndexing(await documentService.captureText("Pasted text", text));
        } catch (error) {
            setStatus("error");
            setErrorMessage(getErrorMessage(error));
        }
    };

    const reset = () => {
        setStatus("idle");
        setMessage("");
        setErrorMessage("");
        setCapturedDocument(null);
        setYoutubeCaptureFailed(false);
        setUrl("");
        setText("");
        if (fileInputRef.current) fileInputRef.current.value = "";
    };

    return (
        <div className="mx-auto w-full max-w-3xl">
            <Card className="overflow-hidden border-border/70 bg-surface-high/20 backdrop-blur-sm">
                <div className="border-b border-border/60 px-5 py-5 sm:px-8">
                    <div className="mb-2 flex items-center gap-2 text-accent">
                        <Sparkles size={18} />
                        <span className="font-mono text-xs uppercase tracking-[0.18em]">One place for everything</span>
                    </div>
                    <h2 className="font-display text-xl sm:text-2xl">Drop it in. Make it searchable.</h2>
                    <p className="mt-2 text-sm text-text-muted">
                        Add a PDF, image, audio clip, text, webpage, or YouTube video. We’ll prepare it for questions and search.
                    </p>
                </div>

                {status === "idle" && (
                    <div className="space-y-5 p-5 sm:p-8">
                        <button
                            type="button"
                            onClick={() => fileInputRef.current?.click()}
                            onDragOver={(event) => {
                                event.preventDefault();
                                setDragActive(true);
                            }}
                            onDragLeave={() => setDragActive(false)}
                            onDrop={(event) => {
                                event.preventDefault();
                                setDragActive(false);
                                const file = event.dataTransfer.files[0];
                                if (file) void captureFile(file);
                            }}
                            className={cn(
                                "flex min-h-44 w-full flex-col items-center justify-center rounded-lg border-2 border-dashed px-5 py-8 text-center transition-colors",
                                dragActive
                                    ? "border-accent bg-accent/10"
                                    : "border-border hover:border-accent/60 hover:bg-surface-high/40"
                            )}
                        >
                            <span className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-accent/10 text-accent">
                                <Upload size={23} />
                            </span>
                            <span className="font-medium">Drop a file here or browse</span>
                            <span className="mt-1 text-xs text-text-muted">PDF, image, audio/video, or common text files</span>
                        </button>
                        <input
                            ref={fileInputRef}
                            type="file"
                            className="hidden"
                            accept="application/pdf,image/*,audio/*,video/*,text/*,.txt,.md,.csv,.json,.html,.xml,.yaml,.yml,.log"
                            onChange={(event) => {
                                const file = event.target.files?.[0];
                                if (file) void captureFile(file);
                            }}
                        />

                        <div className="grid gap-4 sm:grid-cols-2">
                            <label className="block space-y-2">
                                <span className="flex items-center gap-2 text-sm font-medium">
                                    <Link2 size={15} className="text-accent" /> Paste a link
                                </span>
                                <input
                                    value={url}
                                    onChange={(event) => setUrl(event.target.value)}
                                    placeholder="Webpage or YouTube video URL"
                                    className="h-11 w-full rounded-md border border-border bg-background px-3 text-sm outline-none transition focus:border-accent"
                                />
                                <span className="block text-xs text-text-muted">YouTube links use available captions; uploaded videos are transcribed from their audio.</span>
                            </label>
                            <label className="block space-y-2">
                                <span className="flex items-center gap-2 text-sm font-medium">
                                    <FileText size={15} className="text-accent" />
                                    {youtubeCaptureFailed ? "Paste video captions" : "Or paste text"}
                                </span>
                                <textarea
                                    ref={textInputRef}
                                    value={text}
                                    onChange={(event) => setText(event.target.value)}
                                    placeholder={youtubeCaptureFailed
                                        ? "Paste the video's transcript here to make it searchable..."
                                        : "Notes, an email, an excerpt, or anything you want to find later..."}
                                    rows={3}
                                    className="w-full resize-y rounded-md border border-border bg-background px-3 py-2 text-sm outline-none transition focus:border-accent"
                                />
                            </label>
                        </div>

                        <div className="flex flex-col gap-3 border-t border-border/60 pt-4 sm:flex-row sm:items-center sm:justify-between">
                            <div className="flex flex-wrap gap-x-4 gap-y-2 text-xs text-text-muted">
                                <span className="inline-flex items-center gap-1"><FileText size={13} /> PDFs & text</span>
                                <span className="inline-flex items-center gap-1"><ImageIcon size={13} /> Images</span>
                                <span className="inline-flex items-center gap-1"><Mic2 size={13} /> Audio</span>
                                <span className="inline-flex items-center gap-1"><Globe size={13} /> Links</span>
                            </div>
                            <Button onClick={() => void submit()} className="gap-2">
                                <Sparkles size={16} /> Capture source
                            </Button>
                        </div>
                    </div>
                )}

                {status === "processing" && (
                    <div className="space-y-6 p-6 sm:p-10" role="status" aria-live="polite">
                        <div className="flex items-center gap-3">
                            <span className="flex h-10 w-10 items-center justify-center rounded-full bg-accent/10 text-accent">
                                <Loader2 className="animate-spin" size={19} />
                            </span>
                            <div>
                                <p className="font-medium">{message || "Preparing your source..."}</p>
                                <p className="mt-1 text-xs text-text-muted">This stays in progress until indexing finishes.</p>
                            </div>
                        </div>
                        <div className="space-y-3" aria-hidden="true">
                            <div className="h-3 w-2/3 animate-pulse rounded bg-surface-high" />
                            <div className="h-3 w-full animate-pulse rounded bg-surface-high" />
                            <div className="h-3 w-5/6 animate-pulse rounded bg-surface-high" />
                        </div>
                    </div>
                )}

                {status === "error" && (
                    <div className="p-6 text-center sm:p-10" role="alert">
                        <span className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-100 text-red-700">
                            <AlertTriangle size={22} />
                        </span>
                        <h3 className="font-display text-xl">We couldn’t capture that</h3>
                        <p className="mx-auto mt-2 max-w-lg text-sm text-red-700">{errorMessage}</p>
                        <div className="mt-5 flex flex-col justify-center gap-2 sm:flex-row">
                            {youtubeCaptureFailed && url && (
                                <Button
                                    variant="ghost"
                                    onClick={() => {
                                        setStatus("idle");
                                        setErrorMessage("");
                                        window.requestAnimationFrame(() => textInputRef.current?.focus());
                                    }}
                                >
                                    Paste captions instead
                                </Button>
                            )}
                            <Button variant="ghost" onClick={reset}>Try another source</Button>
                        </div>
                    </div>
                )}

                {status === "ready" && capturedDocument && (
                    <div className="p-6 text-center sm:p-10">
                        <span className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-emerald-100 text-emerald-700">
                            <Check size={23} />
                        </span>
                        <h3 className="font-display text-xl">Ready to explore</h3>
                        <p className="mt-2 break-words text-sm text-text-muted">
                            <strong className="text-text-primary">{capturedDocument.filename}</strong> is searchable and ready for questions.
                        </p>
                        <div className="mt-6 flex flex-col justify-center gap-3 sm:flex-row">
                            <Button onClick={() => router.push(`/dashboard/chat/${capturedDocument.id}`)}>
                                Ask questions
                            </Button>
                            <Button variant="ghost" onClick={reset}>Capture another</Button>
                        </div>
                    </div>
                )}
            </Card>
            <p className="mt-4 flex items-center justify-center gap-2 text-center text-xs text-text-muted">
                <AudioLines size={14} /> Images become visual notes; audio/video speech becomes searchable transcripts.
            </p>
        </div>
    );
}
