import { useState } from "react";
import { Search, Bell, LogOut, Menu } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { authService } from "@/services/auth.service";
import { cn } from "@/lib/utils";
import { useSearch } from "@/lib/contexts/search-context";

export function TopBar() {
    const { searchQuery, setSearchQuery, toggleMobileNav } = useSearch();
    const [showNotifications, setShowNotifications] = useState(false);

    return (
        <header className="h-[60px] border-b border-border bg-background/80 backdrop-blur-md fixed top-0 right-0 left-0 md:left-[240px] z-30 flex items-center px-2.5 sm:px-6 gap-2 sm:gap-4 transition-all duration-300">
            {/* Mobile Hamburger Toggle */}
            <Button
                variant="ghost"
                size="icon"
                className="md:hidden text-text-secondary hover:text-text-primary h-9 w-9 shrink-0 active:scale-95"
                onClick={toggleMobileNav}
                aria-label="Toggle navigation menu"
            >
                <Menu className="h-5 w-5" />
            </Button>

            <div className="flex-1 max-w-xl relative min-w-0">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted" />
                <Input
                    placeholder="Search documents..."
                    className="pl-9 h-9 sm:h-10 text-base sm:text-sm bg-surface-high/50 border-transparent focus:bg-surface focus:border-accent"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                />
                <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1 pointer-events-none">
                    <kbd className="hidden sm:inline-flex h-5 items-center gap-1 rounded border border-border bg-surface px-1.5 font-mono text-[10px] font-medium text-text-muted">
                        ⌘K
                    </kbd>
                </div>
            </div>

            <div className="ml-auto flex items-center gap-1 sm:gap-3 shrink-0">
                <div className="relative">
                    <Button
                        variant="ghost"
                        size="icon"
                        className={cn(
                            "text-text-secondary hover:text-text-primary relative h-9 w-9 active:scale-95",
                            showNotifications && "bg-surface-high text-text-primary"
                        )}
                        onClick={() => setShowNotifications(!showNotifications)}
                        aria-label="Notifications"
                    >
                        <Bell className="h-4.5 w-4.5 sm:h-5 sm:w-5" />
                    </Button>

                    {showNotifications && (
                        <>
                            {/* Mobile Click-outside backdrop */}
                            <div
                                className="fixed inset-0 z-40 bg-slate-950/20 backdrop-blur-2xs sm:hidden"
                                onClick={() => setShowNotifications(false)}
                                aria-label="Close notifications backdrop"
                            />
                            <div className="fixed sm:absolute right-2 sm:right-0 top-[64px] sm:top-auto sm:mt-2 w-[calc(100vw-1rem)] sm:w-80 max-w-sm bg-surface border border-border shadow-2xl rounded-xl overflow-hidden animate-in fade-in zoom-in-95 duration-200 z-50">
                                <div className="border-b border-border bg-surface-high/40 px-4 py-3">
                                    <h3 className="text-sm font-semibold">Notifications</h3>
                                </div>
                                <div className="px-6 py-10 text-center">
                                    <Bell className="mx-auto mb-3 h-5 w-5 text-blue-500" />
                                    <p className="text-sm font-medium text-text-primary">You’re all caught up</p>
                                    <p className="mt-1 text-xs text-text-muted">New updates will appear here.</p>
                                </div>
                            </div>
                        </>
                    )}
                </div>

                <Button
                    variant="ghost"
                    size="icon"
                    className="text-text-secondary hover:text-text-primary h-9 w-9 active:scale-95"
                    onClick={() => authService.logout()}
                    title="Logout"
                    aria-label="Logout"
                >
                    <LogOut className="h-4.5 w-4.5 sm:h-5 sm:w-5" />
                </Button>
            </div>
        </header>
    );
}
