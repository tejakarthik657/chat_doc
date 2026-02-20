import * as React from "react";
import { cn } from "@/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
    variant?: "default" | "ready" | "processing" | "error";
}

const Badge = React.forwardRef<HTMLDivElement, BadgeProps>(
    ({ className, variant = "default", children, ...props }, ref) => {
        const variants = {
            default: "bg-surface-high text-text-secondary border-border",
            ready: "bg-[#0D1F0D] text-accent border-[#1A3A1A]",
            processing: "bg-[#1A1500] text-accent-warm border-[#3A2800]",
            error: "bg-[#1A0000] text-red-500 border-[#3A0000]",
        };

        return (
            <div
                ref={ref}
                className={cn(
                    "inline-flex items-center border px-2.5 py-0.5 text-xs font-mono uppercase transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
                    variants[variant],
                    className
                )}
                {...props}
            >
                {variant === "ready" && (
                    <span className="mr-2 h-1.5 w-1.5 rounded-full bg-accent animate-pulse" />
                )}
                {variant === "processing" && (
                    <span className="mr-2 h-1.5 w-1.5 rounded-full bg-accent-warm animate-pulse" />
                )}
                {children}
            </div>
        );
    }
);
Badge.displayName = "Badge";

export { Badge };
