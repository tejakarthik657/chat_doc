"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { LayoutDashboard, Files, BarChart3, Settings, Database } from "lucide-react";

const navItems = [
    { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
    { href: "/dashboard/documents", label: "My Documents", icon: Files },
    { href: "/dashboard/analytics", label: "Analytics", icon: BarChart3 },
    { href: "/dashboard/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
    const pathname = usePathname();

    return (
        <div className="fixed left-0 top-0 h-full w-[240px] border-r border-border bg-background flex flex-col z-40">
            <div className="p-6">
                <h1 className="font-display text-2xl text-text-primary">Veridoc</h1>
            </div>

            <nav className="flex-1 px-4 space-y-2">
                {navItems.map((item) => {
                    const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);
                    const Icon = item.icon;

                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={cn(
                                "flex items-center gap-3 px-4 py-3 text-sm font-medium transition-colors relative group",
                                isActive
                                    ? "text-accent bg-surface-high/50"
                                    : "text-text-muted hover:text-text-primary hover:bg-surface-high/30"
                            )}
                        >
                            {isActive && (
                                <div className="absolute left-0 top-0 bottom-0 w-1 bg-accent" />
                            )}
                            <Icon size={18} />
                            {item.label}
                        </Link>
                    );
                })}
            </nav>

            <div className="p-6 border-t border-border mt-auto">
                <div className="mb-4">
                    <div className="flex justify-between text-xs font-mono mb-1 text-text-secondary">
                        <span>STORAGE</span>
                        <span>14.6 MB</span>
                    </div>
                    <div className="h-1 bg-surface-high rounded-full overflow-hidden">
                        <div className="h-full bg-accent w-[30%]" />
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    <div className="h-8 w-8 bg-surface-high border border-border flex items-center justify-center text-xs font-mono">
                        TK
                    </div>
                    <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate text-text-primary">Teja K.</p>
                        <div className="px-1.5 py-0.5 inline-block bg-surface border border-border text-[10px] font-mono text-text-muted rounded-none">
                            FREE PLAN
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
