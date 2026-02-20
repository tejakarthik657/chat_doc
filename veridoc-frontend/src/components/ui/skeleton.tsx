import * as React from "react";
import { cn } from "@/lib/utils";

function Skeleton({
    className,
    ...props
}: React.HTMLAttributes<HTMLDivElement>) {
    return (
        <div
            className={cn("animate-shimmer bg-surface-high/50 rounded-md", className)}
            {...props}
        />
    );
}

export { Skeleton };
