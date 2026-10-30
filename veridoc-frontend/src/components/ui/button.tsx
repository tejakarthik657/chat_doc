import * as React from "react";
import { cn } from "@/lib/utils";
import { Loader2 } from "lucide-react";

export interface ButtonProps
    extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: "primary" | "ghost" | "danger" | "default" | "outline";
    size?: "default" | "sm" | "lg" | "icon";
    isLoading?: boolean;
    asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
    ({ className, variant = "default", size = "default", isLoading, children, asChild, ...props }, ref) => {
        const variants = {
            default: "bg-surface text-text-primary border border-border hover:border-text-secondary hover:-translate-y-0.5 shadow-sm",
            outline: "bg-surface text-text-primary border border-border hover:border-text-secondary hover:-translate-y-0.5 shadow-sm",
            primary: "bg-accent text-black hover:brightness-110 shadow-md",
            ghost: "bg-transparent text-accent border border-accent/20 hover:bg-accent/10 hover:border-accent",
            danger: "bg-transparent text-red-500 border border-red-500/20 hover:bg-red-500/10 hover:border-red-500",
        };

        const sizes = {
            default: "h-10 px-4 py-2",
            sm: "h-9 rounded-md px-3",
            lg: "h-11 rounded-md px-8",
            icon: "h-10 w-10",
        };

        return (
            <button
                className={cn(
                    "inline-flex items-center justify-center whitespace-nowrap text-sm font-mono uppercase tracking-wide transition-all active:scale-[0.98] select-none touch-manipulation focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50",
                    variants[variant],
                    sizes[size],
                    className
                )}
                ref={ref}
                disabled={isLoading || props.disabled}
                {...props}
            >
                {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {children}
            </button>
        );
    }
);
Button.displayName = "Button";

export { Button };
