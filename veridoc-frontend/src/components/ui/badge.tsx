import * as React from "react";
import { cn } from "@/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
    variant?: "default" | "ready" | "processing" | "error" | "success" | "info" | "warning" | "destructive" | "secondary";
}

const Badge = React.forwardRef<HTMLDivElement, BadgeProps>(
    ({ className, variant = "default", children, ...props }, ref) => {
        const variants = {
            default: "bg-slate-100 text-slate-600 border-slate-200",
            secondary: "bg-slate-100 text-slate-600 border-slate-200",
            ready: "bg-blue-50 text-blue-700 border-blue-200/50",
            success: "bg-blue-50 text-blue-700 border-blue-200/50",
            processing: "bg-blue-50 text-blue-700 border-blue-200/50",
            warning: "bg-blue-50 text-blue-700 border-blue-200/50",
            info: "bg-blue-50 text-blue-700 border-blue-200/50",
            error: "bg-blue-50 text-blue-700 border-blue-200/50",
            destructive: "bg-blue-50 text-blue-700 border-blue-200/50",
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
                {(variant === "ready" || variant === "success") && (
                    <span className="mr-2 h-1.5 w-1.5 rounded-full bg-blue-500 animate-pulse" />
                )}
                {(variant === "processing" || variant === "warning" || variant === "info") && (
                    <span className="mr-2 h-1.5 w-1.5 rounded-full bg-blue-500 animate-pulse" />
                )}
                {children}
            </div>
        );
    }
);
Badge.displayName = "Badge";

export { Badge };
