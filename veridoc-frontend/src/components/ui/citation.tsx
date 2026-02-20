import * as React from "react";
import { cn } from "@/lib/utils";

export interface CitationProps extends React.HTMLAttributes<HTMLDivElement> {
    page: number;
}

const Citation = React.forwardRef<HTMLDivElement, CitationProps>(
    ({ className, page, ...props }, ref) => {
        return (
            <div
                ref={ref}
                className={cn(
                    "inline-flex items-center justify-center cursor-pointer",
                    "bg-[#1A1000] text-accent-warm border border-[#F59E0B] px-1.5 py-0.5 mt-1 mx-1",
                    "text-xs font-mono hover:bg-accent-warm/20 transition-colors",
                    className
                )}
                {...props}
            >
                [p.{page}]
            </div>
        );
    }
);
Citation.displayName = "Citation";

export { Citation };
