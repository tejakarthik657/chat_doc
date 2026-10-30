"use client";

import { UploadDropzone } from "@/components/upload/upload-dropzone";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function UploadPage() {
    return (
        <div className="p-4 sm:p-6 md:p-8 max-w-5xl mx-auto min-h-[calc(100vh-60px)] flex flex-col justify-center">
            <div className="mb-6 sm:mb-8">
                <Link href="/dashboard">
                    <Button variant="ghost" className="pl-0 hover:pl-2 transition-all text-text-muted hover:text-text-primary mb-3 sm:mb-4 text-xs sm:text-sm">
                        <ArrowLeft className="mr-2 h-4 w-4" /> Back to Dashboard
                    </Button>
                </Link>
                <h1 className="font-display text-2xl sm:text-3xl md:text-4xl mb-2">Index a Document</h1>
                <p className="font-mono text-xs sm:text-sm text-text-secondary">
                    Upload a PDF to extract text, generate embeddings, and enable semantic search.
                </p>
            </div>

            <UploadDropzone />
        </div>
    );
}
