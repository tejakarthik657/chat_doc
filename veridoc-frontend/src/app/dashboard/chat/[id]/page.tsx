"use client";

import { use, useState } from "react";
import { DocumentSidebar } from "@/components/chat/document-sidebar";
import { ChatInterface } from "@/components/chat/chat-interface";
import { SourcePanel } from "@/components/chat/source-panel";
import { InsightsPanel } from "@/components/chat/insights-panel";
import { AnimatePresence, motion } from "framer-motion";

export default function ChatPage({ params }: { params: Promise<{ id: string }> }) {
    const { id } = use(params);
    const [activeCitation, setActiveCitation] = useState<number | null>(null);
    const [docsDrawerOpen, setDocsDrawerOpen] = useState(false);
    const [insightsDrawerOpen, setInsightsDrawerOpen] = useState(false);

    return (
        <div className="flex h-[calc(100dvh-60px)] overflow-hidden relative">
            {/* Desktop Left Panel - Document List */}
            <div className="w-[280px] border-r border-border hidden lg:block bg-background shrink-0">
                <DocumentSidebar activeDocId={id} />
            </div>

            {/* Mobile Document Drawer Overlay */}
            <AnimatePresence>
                {docsDrawerOpen && (
                    <>
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            onClick={() => setDocsDrawerOpen(false)}
                            className="fixed inset-0 bg-slate-950/50 backdrop-blur-xs z-50 lg:hidden"
                        />
                        <motion.div
                            initial={{ x: "-100%" }}
                            animate={{ x: 0 }}
                            exit={{ x: "-100%" }}
                            transition={{ type: "spring", damping: 25, stiffness: 200 }}
                            className="fixed inset-y-0 left-0 w-[280px] max-w-[85vw] bg-background border-r border-border z-50 lg:hidden shadow-2xl flex flex-col"
                        >
                            <div className="flex-1 overflow-hidden" onClick={() => setDocsDrawerOpen(false)}>
                                <DocumentSidebar activeDocId={id} />
                            </div>
                        </motion.div>
                    </>
                )}
            </AnimatePresence>

            {/* Center Panel - Chat */}
            <div className="flex-1 flex flex-col min-w-0 bg-background relative h-full">
                <ChatInterface
                    docId={id}
                    onCitationClick={(page) => setActiveCitation(page)}
                    onToggleDocs={() => setDocsDrawerOpen(true)}
                    onToggleInsights={() => setInsightsDrawerOpen(true)}
                />
            </div>

            {/* Desktop Right Panel - Insights Viewer */}
            <div className="w-[340px] hidden xl:block shrink-0">
                <InsightsPanel docId={id} />
            </div>

            {/* Mobile Insights Drawer Overlay */}
            <AnimatePresence>
                {insightsDrawerOpen && (
                    <>
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            onClick={() => setInsightsDrawerOpen(false)}
                            className="fixed inset-0 bg-slate-950/50 backdrop-blur-xs z-50 xl:hidden"
                        />
                        <motion.div
                            initial={{ x: "100%" }}
                            animate={{ x: 0 }}
                            exit={{ x: "100%" }}
                            transition={{ type: "spring", damping: 25, stiffness: 200 }}
                            className="fixed inset-y-0 right-0 w-full sm:w-[360px] bg-background border-l border-border z-50 xl:hidden shadow-2xl flex flex-col"
                        >
                            <div className="p-3 border-b border-border flex items-center justify-between bg-surface">
                                <span className="font-mono text-xs font-bold text-text-secondary uppercase">Document Intelligence</span>
                                <button
                                    onClick={() => setInsightsDrawerOpen(false)}
                                    className="p-1.5 text-text-muted hover:text-text-primary rounded-lg text-xs"
                                >
                                    ✕ Close
                                </button>
                            </div>
                            <div className="flex-1 overflow-y-auto">
                                <InsightsPanel docId={id} />
                            </div>
                        </motion.div>
                    </>
                )}
            </AnimatePresence>

            {/* Citation Source Panel (Desktop inline, Mobile overlay drawer) */}
            <AnimatePresence>
                {activeCitation && (
                    <>
                        {/* Mobile backdrop for citation */}
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            onClick={() => setActiveCitation(null)}
                            className="fixed inset-0 bg-slate-950/40 backdrop-blur-xs z-50 lg:hidden"
                        />
                        <motion.div
                            initial={{ x: "100%", opacity: 0 }}
                            animate={{ x: 0, opacity: 1 }}
                            exit={{ x: "100%", opacity: 0 }}
                            transition={{ duration: 0.25, ease: "easeOut" }}
                            className="fixed inset-y-0 right-0 w-full sm:w-[340px] lg:static lg:w-[320px] lg:animate-none z-50 lg:z-10 border-l border-border bg-surface shadow-2xl lg:shadow-none flex flex-col shrink-0"
                        >
                            <div className="w-full h-full">
                                <SourcePanel
                                    page={activeCitation}
                                    onClose={() => setActiveCitation(null)}
                                />
                            </div>
                        </motion.div>
                    </>
                )}
            </AnimatePresence>
        </div>
    );
}
