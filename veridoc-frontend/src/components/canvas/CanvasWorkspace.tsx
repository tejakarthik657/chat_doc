"use client";

import React, { useState, useEffect } from "react";
import { featuresService } from "@/services/features.service";
import { 
  X, Copy, Check, Download, LayoutTemplate, Sparkles, Wand2, Trash2, 
  Table, FileCheck, HelpCircle, Lightbulb, BookOpen, RefreshCw 
} from "lucide-react";

interface CanvasWorkspaceProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  initialContent?: string;
  onSave?: (content: string) => void;
  onInsertToChat?: (text: string) => void;
}

export const CanvasWorkspace: React.FC<CanvasWorkspaceProps> = ({
  isOpen,
  onClose,
  title = "Document Canvas & Interactive Artifact",
  initialContent = "",
  onSave,
  onInsertToChat,
}) => {
  const [content, setContent] = useState(initialContent);
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<"edit" | "preview">("preview");
  const [isTransforming, setIsTransforming] = useState(false);
  const [activeAction, setActiveAction] = useState<string | null>(null);

  useEffect(() => {
    if (initialContent) {
      if (initialContent.includes("I am not capable of providing any conversational context")) {
        setContent("# Document Notes & Canvas Workspace\n\nType, edit, or format markdown reports and extracted tables here.");
      } else {
        setContent(initialContent);
      }
    }
  }, [initialContent]);

  // Keyboard shortcut: Press Escape to close
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

  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([content], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${title.toLowerCase().replace(/\s+/g, "_")}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleAITransform = async (action: 'polish' | 'table' | 'summary' | 'quiz' | 'simplify' | 'expand') => {
    if (!content.trim() || isTransforming) return;
    setIsTransforming(true);
    setActiveAction(action);
    try {
      const res = await featuresService.transformCanvas(content, action);
      if (res && res.transformed_content) {
        setContent(res.transformed_content);
        if (onSave) onSave(res.transformed_content);
        setActiveTab("preview");
      }
    } catch (err) {
      console.error("[Canvas AI Transform Error]", err);
    } finally {
      setIsTransforming(false);
      setActiveAction(null);
    }
  };

  return (
    <>
      {/* Click-outside Backdrop */}
      <div
        className="fixed inset-0 bg-slate-950/40 backdrop-blur-xs z-[999] transition-opacity animate-in fade-in"
        onClick={onClose}
        aria-label="Close Canvas Backdrop"
      />

      {/* Canvas Workspace Drawer */}
      <div className="fixed inset-y-0 right-0 z-[1000] w-full lg:w-[720px] bg-white shadow-2xl border-l border-slate-200 flex flex-col transition-all duration-300 animate-in slide-in-from-right">
        {/* Header Bar */}
        <div className="p-3 sm:p-4 border-b border-slate-200 flex items-center justify-between bg-slate-50/90 shadow-2xs gap-2">
          <div className="flex items-center gap-2 sm:gap-2.5 min-w-0">
            <div className="p-1.5 sm:p-2 rounded-xl bg-purple-500/10 text-purple-600 border border-purple-200 shrink-0">
              <LayoutTemplate className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <h3 className="text-xs sm:text-sm font-semibold text-slate-900 truncate">{title}</h3>
              <p className="text-[11px] text-slate-500 hidden sm:block truncate">Interactive live editing workspace & artifact canvas</p>
            </div>
          </div>

          <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
            {onInsertToChat && (
              <button
                onClick={() => onInsertToChat(content)}
                className="px-2 py-1 sm:px-2.5 sm:py-1.5 text-[11px] sm:text-xs font-medium text-purple-700 bg-purple-50 hover:bg-purple-100 rounded-lg border border-purple-200 transition-all touch-manipulation active:scale-95"
                title="Insert canvas text into chat prompt"
              >
                Insert
              </button>
            )}
            <button
              onClick={handleCopy}
              className="p-1.5 rounded-lg text-slate-500 hover:text-slate-900 hover:bg-slate-200/60 transition-all touch-manipulation active:scale-95"
              title="Copy content"
            >
              {copied ? <Check className="w-4 h-4 text-emerald-600" /> : <Copy className="w-4 h-4" />}
            </button>
            <button
              onClick={handleDownload}
              className="p-1.5 rounded-lg text-slate-500 hover:text-slate-900 hover:bg-slate-200/60 transition-all touch-manipulation active:scale-95"
              title="Export Markdown (.md)"
            >
              <Download className="w-4 h-4" />
            </button>
            <button
              onClick={onClose}
              className="px-2 py-1 sm:px-2.5 sm:py-1.5 rounded-lg bg-slate-100 hover:bg-rose-50 hover:border-rose-200 hover:text-rose-600 text-slate-700 text-xs font-medium flex items-center gap-1 sm:gap-1.5 transition-all border border-slate-200 shadow-2xs cursor-pointer touch-manipulation active:scale-95"
              title="Close Canvas (or press Esc)"
            >
              <X className="w-4 h-4" />
              <span className="hidden xs:inline">Close</span>
              <kbd className="hidden sm:inline-block px-1 py-0.5 text-[9px] font-mono bg-white rounded border border-slate-300 text-slate-500">Esc</kbd>
            </button>
          </div>
        </div>

      {/* AI Assistant Quick Actions Bar */}
      <div className="px-3 sm:px-4 py-2 bg-gradient-to-r from-purple-50/60 via-indigo-50/40 to-slate-50 border-b border-purple-100 flex items-center gap-2 overflow-x-auto no-scrollbar touch-pan-x">
        <span className="text-[10px] font-mono uppercase text-purple-700 font-semibold flex items-center gap-1 shrink-0">
          <Sparkles className="w-3 h-3 text-purple-600" />
          AI Actions:
        </span>

        <button
          onClick={() => handleAITransform("polish")}
          disabled={isTransforming || !content.trim()}
          className="px-2.5 py-1 text-[11px] font-medium text-slate-700 bg-white hover:bg-purple-50 hover:text-purple-700 border border-slate-200 rounded-lg flex items-center gap-1.5 shrink-0 transition-all disabled:opacity-50"
        >
          {isTransforming && activeAction === "polish" ? <RefreshCw className="w-3 h-3 animate-spin text-purple-600" /> : <Wand2 className="w-3 h-3 text-purple-600" />}
          Polish & Structure
        </button>

        <button
          onClick={() => handleAITransform("summary")}
          disabled={isTransforming || !content.trim()}
          className="px-2.5 py-1 text-[11px] font-medium text-slate-700 bg-white hover:bg-indigo-50 hover:text-indigo-700 border border-slate-200 rounded-lg flex items-center gap-1.5 shrink-0 transition-all disabled:opacity-50"
        >
          {isTransforming && activeAction === "summary" ? <RefreshCw className="w-3 h-3 animate-spin text-indigo-600" /> : <FileCheck className="w-3 h-3 text-indigo-600" />}
          Executive Summary
        </button>

        <button
          onClick={() => handleAITransform("table")}
          disabled={isTransforming || !content.trim()}
          className="px-2.5 py-1 text-[11px] font-medium text-slate-700 bg-white hover:bg-cyan-50 hover:text-cyan-700 border border-slate-200 rounded-lg flex items-center gap-1.5 shrink-0 transition-all disabled:opacity-50"
        >
          {isTransforming && activeAction === "table" ? <RefreshCw className="w-3 h-3 animate-spin text-cyan-600" /> : <Table className="w-3 h-3 text-cyan-600" />}
          Convert to Tables
        </button>

        <button
          onClick={() => handleAITransform("quiz")}
          disabled={isTransforming || !content.trim()}
          className="px-2.5 py-1 text-[11px] font-medium text-slate-700 bg-white hover:bg-emerald-50 hover:text-emerald-700 border border-slate-200 rounded-lg flex items-center gap-1.5 shrink-0 transition-all disabled:opacity-50"
        >
          {isTransforming && activeAction === "quiz" ? <RefreshCw className="w-3 h-3 animate-spin text-emerald-600" /> : <HelpCircle className="w-3 h-3 text-emerald-600" />}
          Generate Quiz
        </button>

        <button
          onClick={() => handleAITransform("simplify")}
          disabled={isTransforming || !content.trim()}
          className="px-2.5 py-1 text-[11px] font-medium text-slate-700 bg-white hover:bg-amber-50 hover:text-amber-700 border border-slate-200 rounded-lg flex items-center gap-1.5 shrink-0 transition-all disabled:opacity-50"
        >
          {isTransforming && activeAction === "simplify" ? <RefreshCw className="w-3 h-3 animate-spin text-amber-600" /> : <Lightbulb className="w-3 h-3 text-amber-600" />}
          Simplify (ELI5)
        </button>

        <button
          onClick={() => handleAITransform("expand")}
          disabled={isTransforming || !content.trim()}
          className="px-2.5 py-1 text-[11px] font-medium text-slate-700 bg-white hover:bg-blue-50 hover:text-blue-700 border border-slate-200 rounded-lg flex items-center gap-1.5 shrink-0 transition-all disabled:opacity-50"
        >
          {isTransforming && activeAction === "expand" ? <RefreshCw className="w-3 h-3 animate-spin text-blue-600" /> : <BookOpen className="w-3 h-3 text-blue-600" />}
          Expand Context
        </button>
      </div>

      {/* Mode Switcher & Clear */}
      <div className="px-4 py-2 bg-slate-50 border-b border-slate-200 flex flex-wrap items-center justify-between gap-2">
        <div className="flex gap-1 p-0.5 bg-slate-200/60 rounded-lg border border-slate-200">
          <button
            onClick={() => setActiveTab("preview")}
            className={`px-3 py-1 text-xs rounded-md font-medium transition-all ${
              activeTab === "preview"
                ? "bg-purple-600 text-white shadow-xs"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            Formatted Preview
          </button>
          <button
            onClick={() => setActiveTab("edit")}
            className={`px-3 py-1 text-xs rounded-md font-medium transition-all ${
              activeTab === "edit"
                ? "bg-purple-600 text-white shadow-xs"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            Markdown Code
          </button>
        </div>

        <button
          onClick={() => setContent("")}
          className="px-2 py-1 text-[11px] font-mono text-slate-500 hover:text-red-600 hover:bg-red-50 border border-slate-200 rounded flex items-center gap-1 transition-all"
          title="Clear canvas"
        >
          <Trash2 className="w-3 h-3" />
          Clear
        </button>
      </div>

      {/* Editor & Rich Preview Body */}
      <div className="flex-1 overflow-y-auto p-3.5 sm:p-5 pb-[max(1.25rem,env(safe-area-inset-bottom))] bg-slate-50/40">
        {activeTab === "edit" ? (
          <textarea
            value={content}
            onChange={(e) => {
              setContent(e.target.value);
              if (onSave) onSave(e.target.value);
            }}
            placeholder="Type or paste markdown content here..."
            className="w-full h-full min-h-[450px] p-3.5 sm:p-4 bg-white text-slate-800 font-mono text-[16px] sm:text-xs rounded-xl border border-slate-200 focus:border-purple-500 focus:outline-none resize-none leading-relaxed shadow-xs"
          />
        ) : (
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs min-h-[450px]">
            {content ? (
              <CanvasMarkdownRenderer content={content} />
            ) : (
              <div className="py-20 text-center text-slate-400 text-xs">
                Canvas is empty. Send any AI response to Canvas or type markdown content here.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
    </>
  );
};

function CanvasMarkdownRenderer({ content }: { content: string }) {
  const lines = content.split("\n");
  const elements: React.ReactNode[] = [];
  let listItems: React.ReactNode[] = [];
  let tableRows: string[][] = [];

  const renderInline = (text: string) => {
    const parts = text.split(/(\*\*.*?\*\*)/g);
    return parts.map((part, i) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return <strong key={i} className="font-semibold text-slate-950">{part.slice(2, -2)}</strong>;
      }
      const codeParts = part.split(/(`.*?`)/g);
      return codeParts.map((subPart, j) => {
        if (subPart.startsWith("`") && subPart.endsWith("`")) {
          return <code key={j} className="px-1.5 py-0.5 bg-purple-50 text-purple-700 font-mono text-xs rounded border border-purple-200">{subPart.slice(1, -1)}</code>;
        }
        return subPart;
      });
    });
  };

  const flushList = (key: number) => {
    if (listItems.length > 0) {
      elements.push(
        <ul key={`list-${key}`} className="list-disc pl-5 my-2.5 space-y-1 text-slate-700 text-xs">
          {listItems}
        </ul>
      );
      listItems = [];
    }
  };

  const flushTable = (key: number) => {
    if (tableRows.length > 0) {
      const headers = tableRows[0];
      const rows = tableRows.slice(2);
      elements.push(
        <div key={`table-${key}`} className="overflow-x-auto my-4 border border-slate-200 rounded-lg shadow-xs">
          <table className="min-w-full divide-y divide-slate-200 text-xs font-sans text-left">
            <thead className="bg-slate-50 font-mono text-[10px] text-slate-500 uppercase tracking-wider">
              <tr>
                {headers.map((h, idx) => (
                  <th key={idx} className="px-3.5 py-2.5 border-r border-slate-200 last:border-0 font-semibold">
                    {h.trim()}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-slate-100 text-slate-700">
              {rows.map((row, rIdx) => (
                <tr key={rIdx} className="hover:bg-slate-50/50">
                  {row.map((cell, cIdx) => (
                    <td key={cIdx} className="px-3.5 py-2.5 border-r border-slate-200 last:border-0">
                      {renderInline(cell.trim())}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      tableRows = [];
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    if (line.trim().startsWith("|")) {
      flushList(i);
      const cells = line.split("|").map(c => c.trim()).filter((_, idx, arr) => idx > 0 && idx < arr.length - 1);
      tableRows.push(cells);
      continue;
    } else {
      flushTable(i);
    }

    if (line.trim().startsWith("- [ ] ") || line.trim().startsWith("- [x] ")) {
      const isChecked = line.trim().startsWith("- [x] ");
      const taskText = line.trim().substring(6);
      listItems.push(
        <li key={`task-${i}`} className="flex items-center gap-2 list-none my-1 font-mono text-xs">
          <input
            type="checkbox"
            checked={isChecked}
            readOnly
            className="w-3.5 h-3.5 rounded text-indigo-600 border-slate-300 focus:ring-0 cursor-pointer"
          />
          <span className={isChecked ? "line-through text-slate-400" : "text-slate-800"}>
            {renderInline(taskText)}
          </span>
        </li>
      );
      continue;
    }

    if (line.trim().startsWith("- ") || line.trim().startsWith("* ")) {
      const contentText = line.trim().substring(2);
      listItems.push(
        <li key={`li-${i}`}>
          {renderInline(contentText)}
        </li>
      );
      continue;
    } else {
      flushList(i);
    }

    if (line.trim().startsWith("### ")) {
      elements.push(<h3 key={i} className="text-sm font-bold text-slate-900 mt-4 mb-1.5 tracking-tight">{renderInline(line.trim().substring(4))}</h3>);
    } else if (line.trim().startsWith("## ")) {
      elements.push(<h2 key={i} className="text-base font-semibold text-slate-950 mt-5 mb-2 border-b border-slate-200 pb-1 tracking-tight">{renderInline(line.trim().substring(3))}</h2>);
    } else if (line.trim().startsWith("# ")) {
      elements.push(<h1 key={i} className="text-xl font-bold text-slate-950 mt-6 mb-3 border-b border-slate-300 pb-2 tracking-tight">{renderInline(line.trim().substring(2))}</h1>);
    } else if (line.trim()) {
      elements.push(
        <p key={i} className="my-2 leading-relaxed text-slate-800 font-sans text-xs">
          {renderInline(line)}
        </p>
      );
    }
  }

  flushList(lines.length);
  flushTable(lines.length);

  return <div className="space-y-1">{elements}</div>;
}
