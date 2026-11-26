"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { CheckCircle2, Info, X } from "lucide-react";

type ToastTone = "success" | "info";

interface ToastNotice {
    title: string;
    message: string;
    tone?: ToastTone;
}

type ShowToast = (notice: ToastNotice) => void;

const ToastContext = createContext<ShowToast | null>(null);

export function ToastProvider({ children }: { children: React.ReactNode }) {
    const [notice, setNotice] = useState<ToastNotice | null>(null);
    const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    const dismiss = useCallback(() => {
        if (timeoutRef.current) clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
        setNotice(null);
    }, []);

    const showToast = useCallback((nextNotice: ToastNotice) => {
        if (timeoutRef.current) clearTimeout(timeoutRef.current);
        setNotice(nextNotice);
        timeoutRef.current = setTimeout(() => setNotice(null), 5200);
    }, []);

    useEffect(() => () => {
        if (timeoutRef.current) clearTimeout(timeoutRef.current);
    }, []);

    return (
        <ToastContext.Provider value={showToast}>
            {children}
            <div className="pointer-events-none fixed inset-x-4 bottom-4 z-[100] flex justify-center sm:inset-x-auto sm:right-6 sm:justify-end">
                {notice && (
                    <div
                        role="status"
                        aria-live="polite"
                        className="pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-xl border border-blue-200 bg-white p-4 shadow-[0_16px_48px_-20px_rgba(15,23,42,0.35)] animate-fadeUp"
                    >
                        <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-blue-50 text-blue-700">
                            {notice.tone === "info" ? <Info size={18} /> : <CheckCircle2 size={18} />}
                        </span>
                        <div className="min-w-0 flex-1">
                            <p className="text-sm font-semibold text-slate-950">{notice.title}</p>
                            <p className="mt-1 text-sm leading-5 text-slate-600">{notice.message}</p>
                        </div>
                        <button
                            type="button"
                            onClick={dismiss}
                            aria-label="Dismiss notification"
                            className="rounded-md p-1 text-slate-500 transition-colors hover:bg-blue-50 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                        >
                            <X size={16} />
                        </button>
                    </div>
                )}
            </div>
        </ToastContext.Provider>
    );
}

export function useToast() {
    const showToast = useContext(ToastContext);
    if (!showToast) throw new Error("useToast must be used within ToastProvider.");
    return showToast;
}
