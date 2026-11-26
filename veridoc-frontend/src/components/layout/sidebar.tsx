"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { LayoutDashboard, Files, BarChart3, Settings, Database, LogOut, X, Plus, MessageSquareText } from "lucide-react";
import { authService } from "@/services/auth.service";
import { analyticsService } from "@/services/analytics.service";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useSearch } from "@/lib/contexts/search-context";

const navItems = [
    { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
    { href: "/dashboard/capture", label: "Capture Anything", icon: Plus },
    { href: "/dashboard/ask", label: "Ask Your Space", icon: MessageSquareText },
    { href: "/dashboard/documents", label: "My Documents", icon: Files },
    { href: "/dashboard/projects", label: "Knowledge Projects", icon: Database },
    { href: "/dashboard/analytics", label: "Analytics", icon: BarChart3 },
    { href: "/dashboard/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
    const pathname = usePathname();
    const { mobileNavOpen, setMobileNavOpen } = useSearch();
    const [user, setUser] = useState<{ email: string; name?: string; storage_used_mb: number; plan: string } | null>(null);
    const [storageLimit, setStorageLimit] = useState<number | null>(null);
    const [userLoading, setUserLoading] = useState(true);

    // Close mobile drawer when route changes
    useEffect(() => {
        setMobileNavOpen(false);
    }, [pathname, setMobileNavOpen]);

    useEffect(() => {
        let mounted = true;
        authService.getMe()
            .then((userData) => {
                if (mounted) setUser(userData);
            })
            .catch((error: unknown) => {
                console.error("Failed to load user info:", error);
            })
            .finally(() => {
                if (mounted) setUserLoading(false);
            });
        analyticsService.getSummary()
            .then((summary) => {
                if (mounted) setStorageLimit(summary.storage_limit_mb);
            })
            .catch((error: unknown) => {
                console.error("Failed to load storage limit:", error);
            });
        return () => {
            mounted = false;
        };
    }, []);

    const storagePercent = user && storageLimit
        ? Math.min((user.storage_used_mb / storageLimit) * 100, 100)
        : 0;
    const displayName = user?.name || user?.email.split("@")[0] || "User";
    const userInitials = displayName.slice(0, 2).toUpperCase();

    return (
        <>
            {/* Mobile Backdrop Overlay */}
            <div
                className={cn(
                    "fixed inset-0 bg-slate-950/50 backdrop-blur-xs z-40 md:hidden transition-opacity duration-300",
                    mobileNavOpen ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
                )}
                onClick={() => setMobileNavOpen(false)}
                aria-label="Close navigation overlay"
            />

            {/* Sidebar drawer container */}
            <div
                className={cn(
                    "fixed left-0 top-0 h-[100dvh] w-[280px] max-w-[85vw] md:w-[240px] border-r border-border bg-background flex flex-col z-50 md:z-40 shadow-2xl md:shadow-none transition-transform duration-300 ease-in-out",
                    mobileNavOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
                )}
            >
                <div className="p-5 md:p-6 flex items-center justify-between">
                    <div className="flex flex-col">
                        <span className="font-display text-xl text-text-primary tracking-tight font-bold">Threadwell</span>
                        <span className="text-[9px] font-mono text-text-muted tracking-wider leading-none uppercase mt-0.5">Keep it close. Find it again.</span>
                    </div>
                    {/* Mobile Close Button */}
                    <Button
                        variant="ghost"
                        size="icon"
                        className="md:hidden h-8 w-8 text-text-muted hover:text-text-primary active:scale-95"
                        onClick={() => setMobileNavOpen(false)}
                        aria-label="Close sidebar"
                    >
                        <X size={18} />
                    </Button>
                </div>

            <nav className="flex-1 px-4 space-y-1.5 overflow-y-auto">
                {navItems.map((item) => {
                    const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);
                    const Icon = item.icon;

                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            onClick={() => setMobileNavOpen(false)}
                            className={cn(
                                "flex items-center gap-3 px-3.5 py-3 text-sm font-medium transition-colors relative group rounded-lg active:scale-[0.98]",
                                isActive
                                    ? "text-accent bg-surface-high/60 font-semibold"
                                    : "text-text-muted hover:text-text-primary hover:bg-surface-high/30"
                            )}
                        >
                            {isActive && (
                                <div className="absolute left-0 top-1 bottom-1 w-1 bg-accent rounded-r-full" />
                            )}
                            <Icon size={18} />
                            {item.label}
                        </Link>
                    );
                })}
            </nav>

            <div className="p-5 sm:p-6 border-t border-border mt-auto pb-[max(1.5rem,env(safe-area-inset-bottom))]">
                <div className="mb-4">
                    <div className="flex justify-between text-xs font-mono mb-1 text-text-secondary">
                        <span>STORAGE</span>
                        {userLoading ? (
                            <Skeleton className="h-3 w-16" />
                        ) : (
                            <span>
                                {user?.storage_used_mb.toFixed(1) ?? "—"} MB
                                {storageLimit !== null && ` / ${storageLimit.toFixed(0)} MB`}
                            </span>
                        )}
                    </div>
                    {userLoading ? (
                        <Skeleton className="h-1 w-full" />
                    ) : (
                        <div
                            className="h-1 overflow-hidden rounded-full bg-surface-high"
                            role="progressbar"
                            aria-label="Storage used"
                            aria-valuenow={Math.min(user?.storage_used_mb ?? 0, storageLimit ?? 0)}
                            aria-valuemin={0}
                            aria-valuemax={storageLimit ?? 0}
                        >
                            <div
                                className="h-full bg-accent transition-all duration-500"
                                style={{ width: `${storagePercent}%` }}
                            />
                        </div>
                    )}
                </div>

                <div className="flex items-center gap-3 mb-3">
                    {userLoading ? (
                        <>
                            <Skeleton className="h-8 w-8 rounded" />
                            <div className="min-w-0 flex-1 space-y-2">
                                <Skeleton className="h-4 w-24" />
                                <Skeleton className="h-4 w-16" />
                            </div>
                        </>
                    ) : (
                        <>
                            <div className="flex h-8 w-8 items-center justify-center rounded border border-border bg-blue-50 text-xs font-mono uppercase text-blue-800">
                                {userInitials}
                            </div>
                            <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium truncate text-text-primary">{displayName}</p>
                                <div className="px-1.5 py-0.5 inline-block bg-surface border border-border text-[10px] font-mono text-text-muted rounded">
                                    {user?.plan.toUpperCase() || "ACCOUNT"}
                                </div>
                            </div>
                        </>
                    )}
                </div>

                <Button
                    onClick={() => authService.logout()}
                    variant="ghost"
                    className="w-full justify-start gap-2 text-text-muted hover:text-text-primary hover:bg-surface-high/30 h-9"
                >
                    <LogOut size={16} />
                    <span className="text-sm">Logout</span>
                </Button>
            </div>
        </div>
    </>
    );
}
