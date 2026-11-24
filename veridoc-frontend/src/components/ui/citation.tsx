import * as React from "react";
import { cn } from "@/lib/utils";
import { FileText, ExternalLink } from "lucide-react";

export interface CitationProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    page: number;
}

const Citation = React.forwardRef<HTMLButtonElement, CitationProps>(
    ({ className, page, onClick, ...props }, ref) => {
        const [isHovered, setIsHovered] = React.useState(false);

        return (
            <div className="relative inline-block group">
                <button
                    ref={ref}
                    type="button"
                    onClick={onClick}
                    onMouseEnter={() => setIsHovered(true)}
                    onMouseLeave={() => setIsHovered(false)}
                    className={cn(
                        "inline-flex items-center gap-1 cursor-pointer",
                        "bg-indigo-50/90 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 px-2 py-0.5 rounded-md",
                        "text-[11px] font-mono font-medium transition-all duration-150 shadow-2xs hover:shadow-xs active:scale-95",
                        className
                    )}
                    title={`Jump to Page ${page} in source document`}
                    {...props}
                >
                    <FileText size={10} className="text-indigo-500" />
                    <span>p.{page}</span>
                    <ExternalLink size={9} className="text-indigo-400 opacity-60 group-hover:opacity-100 transition-opacity" />
                </button>

                {/* Claude-style Hover Preview Card */}
                {isHovered && (
                    <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 w-44 p-2 bg-slate-900/95 backdrop-blur-md text-white text-[10px] font-sans rounded-lg shadow-xl border border-slate-700/80 z-30 pointer-events-none animate-in fade-in zoom-in-95 duration-150">
                        <div className="flex items-center justify-between font-mono text-[9px] text-indigo-300 pb-1 border-b border-slate-800">
                            <span>CITATION</span>
                            <span>PAGE {page}</span>
                        </div>
                        <p className="mt-1 text-slate-300 text-[10px] leading-tight font-sans">
                            Click to highlight & verify this passage in the document viewer.
                        </p>
                    </div>
                )}
            </div>
        );
    }
);
Citation.displayName = "Citation";

export { Citation };

