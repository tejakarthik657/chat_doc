"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, FileText, Check, Loader2, X, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { documentService, DocumentOut } from "@/services/document.service";
import { useRouter } from "next/navigation";

export function UploadDropzone() {
    const router = useRouter();
    const [isDragActive, setIsDragActive] = useState(false);
    const [file, setFile] = useState<File | null>(null);
    const [uploadStatus, setUploadStatus] = useState<"idle" | "uploading" | "processing" | "ready" | "error">("idle");
    const [progressStep, setProgressStep] = useState(0);
    const [uploadedDoc, setUploadedDoc] = useState<DocumentOut | null>(null);
    const [errorMsg, setErrorMsg] = useState("");

    const handleDragOver = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragActive(true);
    };

    const handleDragLeave = () => {
        setIsDragActive(false);
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragActive(false);
        const droppedFile = e.dataTransfer.files[0];
        if (droppedFile && droppedFile.type === "application/pdf") {
            startUpload(droppedFile);
        }
    };

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            startUpload(e.target.files[0]);
        }
    };

    const startUpload = async (selectedFile: File) => {
        setFile(selectedFile);
        setUploadStatus("uploading");
        setErrorMsg("");

        try {
            // Step 1: Upload
            setProgressStep(0);
            const doc = await documentService.upload(selectedFile);
            setUploadedDoc(doc);

            // Step 2: Simulate processing tracking (since backend does it in background)
            setUploadStatus("processing");
            simulateProcessing(doc.id);

        } catch (err: any) {
            setUploadStatus("error");
            setErrorMsg(err.response?.data?.detail || "Upload failed. Please try again.");
        }
    };

    const simulateProcessing = (docId: string) => {
        // Poll for status or just simulate for now since we don't have websocket
        let step = 0;
        const interval = setInterval(async () => {
            step++;
            setProgressStep(step);

            // In a real app we would poll documentService.get(docId) here
            // For now, we assume it succeeds after a few seconds
            try {
                const doc = await documentService.get(docId);
                if (doc.status === 'ready') {
                    clearInterval(interval);
                    setUploadStatus("ready");
                    setUploadedDoc(doc);
                } else if (doc.status === 'error') {
                    clearInterval(interval);
                    setUploadStatus("error");
                    setErrorMsg("Processing failed on server.");
                }
            } catch (e) {
                // ignore poll errors
            }

            if (step >= 4) {
                // Fallback if polling is slow, force check
            }
        }, 2000);
    };

    const reset = () => {
        setFile(null);
        setUploadStatus("idle");
        setProgressStep(0);
        setUploadedDoc(null);
        setErrorMsg("");
    };

    const steps = [
        "Uploading to secure storage...",
        "Extracting text content...",
        "Generating vector embeddings...",
        "Indexing for semantic search..."
    ];

    return (
        <div className="w-full max-w-2xl mx-auto">
            <Card className="p-8 bg-surface-high/20 border-border/50 backdrop-blur-sm">
                <AnimatePresence mode="wait">
                    {uploadStatus === "idle" && (
                        <motion.div
                            key="dropzone"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className={cn(
                                "border-2 border-dashed rounded-lg p-12 flex flex-col items-center justify-center text-center transition-colors duration-300",
                                isDragActive ? "border-accent bg-accent/5" : "border-border hover:border-accent/50 hover:bg-surface-high/30"
                            )}
                            onDragOver={handleDragOver}
                            onDragLeave={handleDragLeave}
                            onDrop={handleDrop}
                        >
                            <div className={cn("h-16 w-16 mb-4 rounded-full flex items-center justify-center transition-colors", isDragActive ? "bg-accent/20 text-accent" : "bg-surface-high text-text-muted")}>
                                <Upload size={32} />
                            </div>
                            <h3 className="font-display text-xl mb-2">Drop your PDF here</h3>
                            <p className="text-text-muted text-sm mb-6">or click to browse (MAX 50MB)</p>

                            <input
                                type="file"
                                id="file-upload"
                                className="hidden"
                                accept="application/pdf"
                                onChange={handleFileSelect}
                            />
                            <label
                                htmlFor="file-upload"
                                className={cn(
                                    "inline-flex items-center justify-center whitespace-nowrap text-sm font-mono uppercase tracking-wide h-10 px-4 py-2 cursor-pointer transition-all bg-accent text-black hover:brightness-110 shadow-md rounded-md"
                                )}
                            >
                                Select File
                            </label>
                        </motion.div>
                    )}

                    {(uploadStatus === "uploading" || uploadStatus === "processing") && (
                        <motion.div
                            key="processing"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="space-y-6"
                        >
                            <div className="flex items-center justify-between p-4 bg-surface border border-border rounded-lg">
                                <div className="flex items-center gap-3">
                                    <div className="h-10 w-10 bg-red-500/10 text-red-500 rounded flex items-center justify-center">
                                        <FileText size={20} />
                                    </div>
                                    <div>
                                        <div className="font-medium text-sm">{file?.name}</div>
                                        <div className="text-xs text-text-muted">{(file?.size || 0) / 1024 / 1024 < 1 ? ((file?.size || 0) / 1024).toFixed(0) + " KB" : ((file?.size || 0) / 1024 / 1024).toFixed(2) + " MB"}</div>
                                    </div>
                                </div>
                                {uploadStatus === "uploading" ? (
                                    <Loader2 className="animate-spin text-accent" />
                                ) : (
                                    <div className="text-xs font-mono text-accent animate-pulse">PROCESSING</div>
                                )}
                            </div>

                            <div className="space-y-4 pl-4 border-l border-border ml-5 relative">
                                {steps.map((label, i) => (
                                    <div key={i} className="flex items-center gap-3 relative">
                                        <div className={cn(
                                            "absolute -left-[21px] h-3 w-3 rounded-full border-2 transition-colors duration-500",
                                            i < progressStep ? "bg-accent border-accent" :
                                                i === progressStep ? "bg-background border-accent animate-pulse" : "bg-background border-border"
                                        )} />
                                        <span className={cn(
                                            "text-sm font-mono transition-colors duration-500",
                                            i < progressStep ? "text-text-primary" :
                                                i === progressStep ? "text-accent" : "text-text-muted"
                                        )}>
                                            {label}
                                        </span>
                                        {i < progressStep && <Check size={14} className="text-accent" />}
                                    </div>
                                ))}
                            </div>
                        </motion.div>
                    )}

                    {uploadStatus === "error" && (
                        <motion.div
                            key="error"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            className="text-center py-8"
                        >
                            <div className="mx-auto h-20 w-20 bg-red-500/20 text-red-500 rounded-full flex items-center justify-center mb-6">
                                <AlertTriangle size={40} />
                            </div>
                            <h2 className="font-display text-3xl mb-2">Upload Failed</h2>
                            <p className="text-red-400 mb-8">
                                {errorMsg}
                            </p>

                            <Button variant="ghost" onClick={reset}>
                                Try Again
                            </Button>
                        </motion.div>
                    )}

                    {uploadStatus === "ready" && (
                        <motion.div
                            key="ready"
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            className="text-center py-8"
                        >
                            <div className="mx-auto h-20 w-20 bg-accent/20 text-accent rounded-full flex items-center justify-center mb-6">
                                <Check size={40} />
                            </div>
                            <h2 className="font-display text-3xl mb-2">Document Ready</h2>
                            <p className="text-text-secondary mb-8">
                                Ready for semantic search and Q&A.
                            </p>

                            <div className="flex justify-center gap-4">
                                <Button variant="primary" size="lg" onClick={() => router.push(`/dashboard/chat/${uploadedDoc?.id}`)}>
                                    Start Asking Questions →
                                </Button>
                                <Button variant="ghost" onClick={reset}>
                                    Upload Another
                                </Button>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </Card>
        </div>
    );
}
