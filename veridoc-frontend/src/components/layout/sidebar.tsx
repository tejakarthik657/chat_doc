"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { LayoutDashboard, Files, BarChart3, Settings, Database, LogOut, X } from "lucide-react";
import { authService } from "@/services/auth.service";
import { Button } from "@/components/ui/button";
import { useSearch } from "@/lib/contexts/search-context";

const navItems = [
    { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
    { href: "/dashboard/documents", label: "My Documents", icon: Files },
    { href: "/dashboard/projects", label: "Knowledge Projects", icon: Database },
    { href: "/dashboard/analytics", label: "Analytics", icon: BarChart3 },
    { href: "/dashboard/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
    const pathname = usePathname();
    const { mobileNavOpen, setMobileNavOpen } = useSearch();
    const [user, setUser] = useState<{ email: string; storage_used_mb: number; plan: string } | null>(null);

    // Close mobile drawer when route changes
    useEffect(() => {
        setMobileNavOpen(false);
    }, [pathname, setMobileNavOpen]);

    useEffect(() => {
        const loadUser = async () => {
            try {
                const userData = await authService.getMe();
                setUser(userData);
            } catch (error) {
                console.error("Failed to load user info:", error);
            }
        };
        loadUser();
    }, []);

    const storageLimit = 100; // Assuming 100MB for free plan, should ideally come from backend
    const storagePercent = user ? Math.min((user.storage_used_mb / storageLimit) * 100, 100) : 0;
    const userInitials = user?.email.split('@')[0].substring(0, 2).toUpperCase() || "??";
    const displayName = user?.email.split('@')[0] || "User";

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
                        <span className="font-display text-xl text-text-primary tracking-tight font-bold">NEXUS AI</span>
                        <span className="text-[9px] font-mono text-text-muted tracking-wider leading-none uppercase mt-0.5">Explore &bull; Understand &bull; Build</span>
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
                        <span>{user?.storage_used_mb.toFixed(1) || "0.0"} MB</span>
                    </div>
                    <div className="h-1 bg-surface-high rounded-full overflow-hidden">
                        <div
                            className="h-full bg-accent transition-all duration-500"
                            style={{ width: `${storagePercent}%` }}
                        />
                    </div>
                </div>

                <div className="flex items-center gap-3 mb-3">
                    <div className="h-8 w-8 bg-surface-high border border-border flex items-center justify-center text-xs font-mono uppercase rounded">
                        {userInitials}
                    </div>
                    <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate text-text-primary">{displayName}</p>
                        <div className="px-1.5 py-0.5 inline-block bg-surface border border-border text-[10px] font-mono text-text-muted rounded">
                            {user?.plan.toUpperCase() || "FREE PLAN"}
                        </div>
                    </div>
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
