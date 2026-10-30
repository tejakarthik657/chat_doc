"use client";

import { DocumentGrid } from "@/components/dashboard/document-grid";
import { UploadDropzone } from "@/components/upload/upload-dropzone";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Plus, X } from "lucide-react";

export default function DocumentsPage() {
    const [isUploading, setIsUploading] = useState(false);

    return (
        <div className="p-4 sm:p-6 md:p-8 max-w-[1600px] mx-auto min-h-[calc(100vh-60px)]">
            <div className="space-y-6 sm:space-y-8">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div>
                        <h1 className="font-display text-2xl sm:text-3xl mb-1">My Documents</h1>
                        <p className="text-text-secondary text-xs sm:text-sm">Manage and chat with your PDF medical records and analysis.</p>
                    </div>
                    <Button
                        variant={isUploading ? "ghost" : "primary"}
                        onClick={() => setIsUploading(!isUploading)}
                        className="gap-2 w-full sm:w-auto justify-center"
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
                    <div className="bg-surface border border-border p-4 sm:p-8 rounded-lg animate-in fade-in slide-in-from-top-4 duration-300">
                        <UploadDropzone />
                    </div>
                )}

                <div className="bg-surface/30 border border-border/50 rounded-xl p-3 sm:p-6">
                    <DocumentGrid />
                </div>
            </div>
        </div>
    );
}
