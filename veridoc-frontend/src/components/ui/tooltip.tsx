import * as React from "react";
import { cn } from "@/lib/utils";

export interface TooltipProps {
    content: string;
    children: React.ReactNode;
    className?: string;
}

export function Tooltip({ content, children, className }: TooltipProps) {
    return (
        <div className="group relative inline-block">
            {children}
            <div
                className={cn(
                    "pointer-events-none absolute bottom-full left-1/2 mb-2 -translate-x-1/2 whitespace-nowrap bg-surface-high border border-border px-2 py-1 text-xs font-mono text-white opacity-0 transition-opacity delay-150 duration-300 group-hover:opacity-100 z-50",
                    className
                )}
            >
                {content}
                {/* Arrow */}
                <div className="absolute left-1/2 top-full -translate-x-1/2 border-4 border-transparent border-t-border" />
            </div>
        </div>
    );
}
