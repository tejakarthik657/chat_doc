"use client";

import { use, useState } from "react";
import { DocumentSidebar } from "@/components/chat/document-sidebar";
import { ChatInterface } from "@/components/chat/chat-interface";
import { SourcePanel } from "@/components/chat/source-panel";
import { AnimatePresence, motion } from "framer-motion";

export default function ChatPage({ params }: { params: Promise<{ id: string }> }) {
    const { id } = use(params);
    const [activeCitation, setActiveCitation] = useState<number | null>(null);

    return (
        <div className="flex h-[calc(100vh-60px)] overflow-hidden">
            {/* Left Panel - Document List */}
            <div className="w-[280px] border-r border-border hidden lg:block bg-background">
                <DocumentSidebar activeDocId={id} />
            </div>

            {/* Center Panel - Chat */}
            <div className="flex-1 flex flex-col min-w-0 bg-background relative z-10">
                <ChatInterface
                    docId={id}
                    onCitationClick={(page) => setActiveCitation(page)}
                />
            </div>

            {/* Right Panel - Source Viewer */}
            <AnimatePresence>
                {activeCitation && (
                    <motion.div
                        initial={{ width: 0, opacity: 0 }}
                        animate={{ width: 300, opacity: 1 }}
                        exit={{ width: 0, opacity: 0 }}
                        transition={{ duration: 0.3, ease: "easeInOut" }}
                        className="border-l border-border bg-surface-high/10 overflow-hidden"
                    >
                        <div className="w-[300px] h-full">
                            <SourcePanel
                                page={activeCitation}
                                onClose={() => setActiveCitation(null)}
                            />
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
