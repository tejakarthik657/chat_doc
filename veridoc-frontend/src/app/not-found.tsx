import Link from "next/link";
import { Button } from "@/components/ui/button";
import { FileWarning } from "lucide-react";

export default function NotFound() {
    return (
        <div className="min-h-screen bg-background flex flex-col items-center justify-center text-center p-6 relative overflow-hidden">
            {/* Background 404 */}
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 font-display text-[300px] text-surface-high pointer-events-none opacity-20 select-none z-0">
                404
            </div>

            <div className="relative z-10 space-y-6 max-w-lg">
                <div className="mx-auto h-24 w-24 bg-surface-high/50 rounded-full flex items-center justify-center text-text-muted border border-border mb-8 animate-pulse">
                    <FileWarning size={48} />
                </div>

                <h1 className="font-display text-5xl">This page doesn't exist.</h1>
                <p className="font-mono text-text-secondary border-y border-border py-4">
                    Unlike our AI, we won't make something up.
                </p>

                <div className="flex items-center justify-center gap-4 pt-4">
                    <Link href="/dashboard">
                        <Button variant="primary">Back to Dashboard</Button>
                    </Link>
                    <Link href="/">
                        <Button variant="ghost">Return Home</Button>
                    </Link>
                </div>

                <div className="pt-12 text-[10px] font-mono text-text-muted opacity-50 space-y-1">
                    <div>ERROR_CODE: PAGE_NOT_FOUND</div>
                    <div>RETRIEVAL_STATUS: NULL</div>
                    <div>HALLUCINATION_ATTEMPT: DENIED</div>
                </div>
            </div>
        </div>
    );
}
