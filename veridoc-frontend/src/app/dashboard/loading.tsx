import { Skeleton } from "@/components/ui/skeleton";

export default function DashboardLoading() {
    return (
        <main
            aria-busy="true"
            aria-label="Opening your workspace"
            className="mx-auto min-h-[calc(100vh-60px)] max-w-[1600px] p-4 sm:p-6 md:p-8"
        >
            <div className="space-y-8">
                <div className="flex items-center justify-between">
                    <Skeleton className="h-9 w-44" />
                    <Skeleton className="hidden h-4 w-36 sm:block" />
                </div>
                <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                    {Array.from({ length: 4 }, (_, index) => (
                        <div key={index} className="space-y-4 rounded-xl border border-border bg-surface p-5">
                            <Skeleton className="h-3 w-24" />
                            <Skeleton className="h-8 w-32" />
                            <Skeleton className="h-3 w-full" />
                        </div>
                    ))}
                </div>
                <div className="grid gap-8 lg:grid-cols-[minmax(0,3fr),minmax(240px,1fr)]">
                    <div className="space-y-4">
                        <Skeleton className="h-7 w-40" />
                        <div className="grid gap-4 sm:grid-cols-2">
                            {Array.from({ length: 4 }, (_, index) => (
                                <div key={index} className="space-y-4 rounded-xl border border-border bg-surface p-5">
                                    <Skeleton className="h-32 w-full" />
                                    <Skeleton className="h-4 w-3/4" />
                                    <Skeleton className="h-3 w-1/2" />
                                </div>
                            ))}
                        </div>
                    </div>
                    <div className="space-y-4">
                        <Skeleton className="h-7 w-36" />
                        <div className="space-y-5 rounded-xl border border-border bg-surface p-5">
                            {Array.from({ length: 4 }, (_, index) => (
                                <div key={index} className="space-y-2">
                                    <Skeleton className="h-4 w-full" />
                                    <Skeleton className="h-3 w-2/3" />
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
            <p className="sr-only" role="status">Preparing your workspace…</p>
        </main>
    );
}
