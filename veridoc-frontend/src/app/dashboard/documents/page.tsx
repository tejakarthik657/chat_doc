"use client";

import { DocumentGrid } from "@/components/dashboard/document-grid";
import { UploadDropzone } from "@/components/upload/upload-dropzone";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Plus, X } from "lucide-react";

export default function DocumentsPage() {
    const [isUploading, setIsUploading] = useState(false);

    return (
        <div className="p-8 max-w-[1600px] mx-auto min-h-[calc(100vh-60px)]">
            <div className="space-y-8">
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="font-display text-3xl mb-1">My Documents</h1>
                        <p className="text-text-secondary text-sm">Manage and chat with your PDF medical records and analysis.</p>
                    </div>
                    <Button
                        variant={isUploading ? "ghost" : "primary"}
                        onClick={() => setIsUploading(!isUploading)}
                        className="gap-2"
                    >
                        {isUploading ? (
                            <>
                                <X size={18} /> Cancel
                            </>
                        ) : (
                            <>
                                <Plus size={18} /> Upload New
                            </>
                        )}
                    </Button>
                </div>

                {isUploading && (
                    <div className="bg-surface border border-border p-8 rounded-lg animate-in fade-in slide-in-from-top-4 duration-300">
                        <UploadDropzone />
                    </div>
                )}

                <div className="bg-surface/30 border border-border/50 rounded-xl p-6">
                    <DocumentGrid />
                </div>
            </div>
        </div>
    );
}
