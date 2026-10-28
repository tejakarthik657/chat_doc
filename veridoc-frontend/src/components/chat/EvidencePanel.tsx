"use client";

import React, { useEffect } from "react";
import { X, ShieldCheck, FileText, ExternalLink, Layers, ArrowUpRight } from "lucide-react";

export interface EvidenceItem {
  chunk_id: string;
  page: number;
  score: number;
  source: string;
  snippet: string;
}

interface EvidencePanelProps {
  isOpen: boolean;
  onClose: () => void;
  evidenceItems: EvidenceItem[];
  supportLabel?: string;
  supportConfidence?: number;
  onJumpToPage?: (page: number) => void;
  question?: string;
  onAskGeneralAI?: (question: string) => void;
}

export const EvidencePanel: React.FC<EvidencePanelProps> = ({
  isOpen,
  onClose,
  evidenceItems,
  supportLabel,
  supportConfidence,
  onJumpToPage,
  question,
  onAskGeneralAI,
}) => {
  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    if (isOpen) {
      window.addEventListener("keydown", handleKeyDown);
    }
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const getScoreBadgeClass = (score: number) => {
    if (score >= 0.75) return "bg-emerald-50 text-emerald-700 border-emerald-300 font-semibold";
    if (score >= 0.5) return "bg-cyan-50 text-cyan-700 border-cyan-300 font-semibold";
    return "bg-amber-50 text-amber-700 border-amber-300 font-semibold";
  };

  return (
    <>
      {/* Click-outside Backdrop */}
      <div
        className="fixed inset-0 bg-slate-950/40 backdrop-blur-xs z-[999] transition-opacity animate-in fade-in"
        onClick={onClose}
        aria-label="Close Evidence Inspector Backdrop"
      />

      {/* Drawer */}
      <div className="fixed inset-y-0 right-0 z-[1000] w-full sm:w-[480px] bg-white shadow-2xl border-l border-slate-200 flex flex-col transition-all duration-300 animate-in slide-in-from-right">
        {/* Header */}
        <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-slate-50/90 shadow-2xs">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-xl bg-cyan-500/10 text-cyan-600 border border-cyan-200">
              <Layers className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-900">Evidence & Source Inspector</h3>
              <p className="text-xs text-slate-500">Underlying RAG retrieval chunks & match scores</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="px-2.5 py-1.5 rounded-lg bg-slate-100 hover:bg-rose-50 hover:border-rose-200 hover:text-rose-600 text-slate-700 text-xs font-medium flex items-center gap-1.5 transition-colors border border-slate-200 cursor-pointer shadow-2xs"
            title="Close Inspector (or press Esc)"
          >
            <X className="w-4 h-4" />
            <span>Close</span>
            <kbd className="hidden sm:inline-block px-1 py-0.5 text-[9px] font-mono bg-white rounded border border-slate-300 text-slate-500">Esc</kbd>
          </button>
        </div>

      {/* Confidence Header */}
      {supportLabel && (
        <div className="p-3 mx-4 mt-4 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
            <span className="text-xs font-medium text-slate-700">Grounding Integrity</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-300 capitalize font-medium">
              {supportLabel.replace("_", " ")}
            </span>
            {supportConfidence !== undefined && (
              <span className="text-xs font-mono text-slate-500">
                {(supportConfidence * 100).toFixed(0)}%
              </span>
            )}
          </div>
        </div>
      )}

      {/* Content Chunk List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-slate-50/40">
        {evidenceItems.length === 0 ? (
          <div className="py-6 px-4 text-center rounded-2xl bg-white border border-slate-200/80 shadow-xs space-y-4">
            <div className="w-10 h-10 rounded-full bg-amber-50 border border-amber-200 text-amber-600 flex items-center justify-center mx-auto text-lg">
              🔍
            </div>
            <div className="space-y-1">
              <h4 className="text-xs font-semibold text-slate-800 uppercase tracking-wide">
                No Direct Evidence In Document
              </h4>
              <p className="text-xs text-slate-500 leading-relaxed max-w-xs mx-auto">
                The vector search evaluated all indexed sections of this document, but none matched this specific query with sufficient semantic confidence.
              </p>
            </div>

            {question && onAskGeneralAI && (
              <div className="pt-2 border-t border-slate-100">
                <button
                  onClick={() => {
                    onAskGeneralAI(question);
                    onClose();
                  }}
                  className="w-full py-2.5 px-3 rounded-xl bg-gradient-to-r from-cyan-600 to-indigo-600 hover:from-cyan-700 hover:to-indigo-700 text-white text-xs font-medium shadow-sm flex items-center justify-center gap-2 transition-all active:scale-[0.98]"
                >
                  <span>🌐</span>
                  Ask General AI "{question.length > 25 ? question.slice(0, 25) + "..." : question}"
                </button>
                <p className="text-[10px] text-slate-400 mt-1.5">
                  Uses open world LLM knowledge outside of document restrictions.
                </p>
              </div>
            )}
          </div>
        ) : (
          evidenceItems.map((item, idx) => (
            <div
              key={item.chunk_id || idx}
              className="p-3.5 rounded-xl bg-white border border-slate-200/80 shadow-xs hover:border-indigo-300 transition-all space-y-2 group"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 overflow-hidden">
                  <FileText className="w-3.5 h-3.5 text-indigo-600 shrink-0" />
                  <span className="text-xs font-medium text-slate-800 truncate">
                    {item.source}
                  </span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 font-mono border border-slate-200">
                    Pg {item.page}
                  </span>
                </div>
                <span
                  className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${getScoreBadgeClass(
                    item.score
                  )}`}
                >
                  {(item.score * 100).toFixed(0)}% match
                </span>
              </div>

              <p className="text-xs text-slate-700 font-serif leading-relaxed italic bg-slate-50 p-2.5 rounded-lg border border-slate-200/60">
                "{item.snippet}..."
              </p>

              {onJumpToPage && (
                <div className="flex justify-end pt-1">
                  <button
                    onClick={() => onJumpToPage(item.page)}
                    className="text-[11px] text-indigo-600 hover:text-indigo-800 flex items-center gap-1 font-medium group-hover:underline"
                  >
                    Jump to Page {item.page}
                    <ArrowUpRight className="w-3 h-3" />
                  </button>
                </div>
              )}
            </div>
          ))
        )}

        {/* Global knowledge fallback even if evidence was present */}
        {evidenceItems.length > 0 && question && onAskGeneralAI && (
          <div className="pt-2">
            <button
              onClick={() => {
                onAskGeneralAI(question);
                onClose();
              }}
              className="w-full py-2 px-3 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 hover:text-slate-900 text-xs font-medium flex items-center justify-center gap-2 transition-all"
            >
              <span>🌐</span>
              Need broader context? Ask General AI
            </button>
          </div>
        )}
      </div>
    </div>
    </>
  );
};
