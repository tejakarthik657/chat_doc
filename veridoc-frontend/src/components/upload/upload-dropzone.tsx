"use client";

import { ChangeEvent, DragEvent, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, AudioLines, Check, FileText, Image, Loader2, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { DocumentOut } from "@/services/document.service";
import { captureSourceFile, waitForCapturedDocument } from "@/lib/source-capture";
import { useRouter } from "next/navigation";

type UploadStatus = "idle" | "capturing" | "indexing" | "ready" | "error";
const ACCEPTED_FILES = "application/pdf,image/*,audio/*,video/*,text/*,.txt,.md,.csv,.json,.html,.xml,.yaml,.yml,.log";

function getErrorMessage(error: unknown): string {
    if (error && typeof error === "object" && "response" in error) {
        const response = (error as { response?: { data?: { detail?: unknown } } }).response;
        const detail = response?.data?.detail;
        if (typeof detail === "string") return detail;
        if (Array.isArray(detail)) {
            const messages = detail
                .map((item) => item && typeof item === "object" && "msg" in item ? item.msg : item)
                .filter((item): item is string => typeof item === "string");
            if (messages.length) return messages.join(", ");
        }
    }
    if (error instanceof Error) return error.message;
    return "Could not capture this file. Please try another supported format.";
}

export function UploadDropzone() {
    const router = useRouter();
    const inputRef = useRef<HTMLInputElement>(null);
    const [isDragActive, setIsDragActive] = useState(false);
    const [file, setFile] = useState<File | null>(null);
    const [uploadStatus, setUploadStatus] = useState<UploadStatus>("idle");
    const [progressMessage, setProgressMessage] = useState("");
    const [uploadedDoc, setUploadedDoc] = useState<DocumentOut | null>(null);
    const [errorMessage, setErrorMessage] = useState("");

    const startCapture = async (selectedFile: File) => {
        setFile(selectedFile);
        setUploadStatus("capturing");
        setProgressMessage("Reading your file...");
        setErrorMessage("");
        setUploadedDoc(null);

        try {
            const document = await captureSourceFile(selectedFile, setProgressMessage);
            setUploadedDoc(document);
            setUploadStatus("indexing");
            const readyDocument = await waitForCapturedDocument(document.id, setProgressMessage);
            setUploadedDoc(readyDocument);
            setUploadStatus("ready");
        } catch (error) {
            console.error("Failed to capture uploaded file:", error);
            setUploadStatus("error");
            setErrorMessage(getErrorMessage(error));
        }
    };

    const handleFileSelect = (event: ChangeEvent<HTMLInputElement>) => {
        const selectedFile = event.target.files?.[0];
        if (selectedFile) void startCapture(selectedFile);
        event.target.value = "";
    };

    const handleDrop = (event: DragEvent<HTMLDivElement>) => {
        event.preventDefault();
        setIsDragActive(false);
        const droppedFile = event.dataTransfer.files[0];
        if (droppedFile) void startCapture(droppedFile);
    };

    const reset = () => {
        setFile(null);
        setUploadStatus("idle");
        setProgressMessage("");
        setUploadedDoc(null);
        setErrorMessage("");
        if (inputRef.current) inputRef.current.value = "";
    };

    return (
        <div className="mx-auto w-full max-w-2xl">
            <Card className="border-border/50 bg-surface-high/20 p-4 backdrop-blur-sm sm:p-8">
                <AnimatePresence mode="wait">
                    {uploadStatus === "idle" && (
                        <motion.div
                            key="dropzone"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className={cn(
                                "flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-6 text-center transition-colors duration-300 sm:p-12",
                                isDragActive
                                    ? "border-accent bg-accent/5"
                                    : "border-border hover:border-accent/50 hover:bg-surface-high/30",
                            )}
                            onDragOver={(event) => {
                                event.preventDefault();
                                setIsDragActive(true);
                            }}
                            onDragLeave={() => setIsDragActive(false)}
                            onDrop={handleDrop}
                        >
                            <div className={cn(
                                "mb-4 flex h-16 w-16 items-center justify-center rounded-full transition-colors",
                                isDragActive ? "bg-accent/20 text-accent" : "bg-surface-high text-text-muted",
                            )}>
                                <Upload size={32} />
                            </div>
                            <h3 className="mb-2 font-display text-xl">Drop a file to capture it</h3>
                            <p className="mb-5 text-sm text-text-muted">
                                PDF, image, audio/video, or common text formats · up to 50 MB for PDFs
                            </p>
                            <input
                                ref={inputRef}
                                type="file"
                                className="sr-only"
                                accept={ACCEPTED_FILES}
                                onChange={handleFileSelect}
                                aria-label="Choose a file to capture"
                            />
                            <Button type="button" onClick={() => inputRef.current?.click()} className="gap-2">
                                <Upload size={16} />
                                Browse files
                            </Button>
                            <p className="mt-4 max-w-lg text-xs leading-5 text-text-muted">
                                Audio and video are transcribed, images are analyzed, and text files are indexed for search and questions.
                            </p>
                        </motion.div>
                    )}

                    {(uploadStatus === "capturing" || uploadStatus === "indexing") && (
                        <motion.div
                            key="processing"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="space-y-6 py-5"
                            role="status"
                            aria-live="polite"
                        >
                            <div className="flex items-center gap-4 rounded-lg border border-border bg-surface p-4">
                                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-accent/10 text-accent">
                                    {file?.type.startsWith("audio/") || file?.type.startsWith("video/")
                                        ? <AudioLines size={21} />
                                        : file?.type.startsWith("image/")
                                            ? <Image size={21} />
                                            : <FileText size={21} />}
                                </div>
                                <div className="min-w-0 flex-1">
                                    <p className="truncate text-sm font-medium">{file?.name}</p>
                                    <p className="mt-1 text-xs text-text-muted">{progressMessage}</p>
                                </div>
                                <Loader2 className="shrink-0 animate-spin text-accent" />
                            </div>
                            <div className="h-1.5 overflow-hidden rounded-full bg-surface-high">
                                <div className="h-full w-1/3 animate-pulse rounded-full bg-accent" />
                            </div>
                            <p className="text-center text-xs text-text-muted">
                                {uploadStatus === "capturing" ? "Extracting content" : "Indexing for search"}
                            </p>
                        </motion.div>
                    )}

                    {uploadStatus === "error" && (
                        <motion.div
                            key="error"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            className="py-8 text-center"
                            role="alert"
                        >
                            <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-full bg-red-100 text-red-700">
                                <AlertTriangle size={32} />
                            </div>
                            <h2 className="mb-2 font-display text-2xl">Couldn’t capture this file</h2>
                            <p className="mx-auto mb-7 max-w-lg text-sm text-red-700">{errorMessage}</p>
                            <Button variant="outline" onClick={reset}>Try another file</Button>
                        </motion.div>
                    )}

                    {uploadStatus === "ready" && (
                        <motion.div
                            key="ready"
                            initial={{ opacity: 0, scale: 0.97 }}
                            animate={{ opacity: 1, scale: 1 }}
                            className="py-8 text-center"
                        >
                            <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-full bg-emerald-100 text-emerald-700">
                                <Check size={32} />
                            </div>
                            <h2 className="mb-2 font-display text-2xl">Ready to explore</h2>
                            <p className="mb-7 text-sm text-text-secondary">
                                <span className="font-medium text-text-primary">{uploadedDoc?.filename}</span> is indexed and ready for questions.
                            </p>
                            <div className="flex flex-col justify-center gap-3 sm:flex-row">
                                <Button onClick={() => router.push(`/dashboard/chat/${uploadedDoc?.id}`)}>
                                    Ask questions
                                </Button>
                                <Button variant="ghost" onClick={reset}>Capture another</Button>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </Card>
        </div>
    );
}
