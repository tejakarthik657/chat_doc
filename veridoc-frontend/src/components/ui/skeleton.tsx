import * as React from "react";
import { cn } from "@/lib/utils";

function Skeleton({
    className,
    ...props
}: React.HTMLAttributes<HTMLDivElement>) {
    return (
        <div
            className={cn(
                "relative overflow-hidden rounded-md bg-surface-high before:absolute before:inset-0 before:bg-[length:200%_100%] before:bg-gradient-to-r before:from-transparent before:via-white/80 before:to-transparent before:animate-shimmer motion-reduce:before:animate-none",
                className
            )}
            {...props}
        />
    );
}

export { Skeleton };
