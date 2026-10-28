import { useState, useEffect } from "react";
import { Search, Bell, LogOut, CheckCircle2, AlertCircle, Clock } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { authService } from "@/services/auth.service";
import { cn } from "@/lib/utils";
import { useSearch } from "@/lib/contexts/search-context";

interface Notification {
    id: string;
    title: string;
    message: string;
    type: "info" | "success" | "warning";
    timestamp: Date;
    read: boolean;
}

export function TopBar() {
    const { searchQuery, setSearchQuery } = useSearch();
    const [notifications, setNotifications] = useState<Notification[]>([
        {
            id: "1",
            title: "Welcome to NEXUS AI",
            message: "Start by creating a knowledge project or uploading your documents.",
            type: "info",
            timestamp: new Date(),
            read: false
        }
    ]);
    const [showNotifications, setShowNotifications] = useState(false);

    // Mock real-time notification
    useEffect(() => {
        const timer = setTimeout(() => {
            setNotifications(prev => [
                {
                    id: "2",
                    title: "System Ready",
                    message: "All analysis engines are online and grounded.",
                    type: "success",
                    timestamp: new Date(),
                    read: false
                },
                ...prev
            ]);
        }, 5000);
        return () => clearTimeout(timer);
    }, []);

    const unreadCount = notifications.filter(n => !n.read).length;

    return (
        <header className="h-[60px] border-b border-border bg-background/50 backdrop-blur-sm fixed top-0 right-0 left-[240px] z-30 flex items-center px-6 gap-4">
            <div className="flex-1 max-w-xl relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted" />
                <Input
                    placeholder="Search across all documents..."
                    className="pl-9 bg-surface-high/50 border-transparent focus:bg-surface focus:border-accent"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                />
                <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1 pointer-events-none">
                    <kbd className="hidden sm:inline-flex h-5 items-center gap-1 rounded border border-border bg-surface px-1.5 font-mono text-[10px] font-medium text-text-muted">
                        ⌘K
                    </kbd>
                </div>
            </div>

            <div className="ml-auto flex items-center gap-4">
                <div className="relative">
                    <Button
                        variant="ghost"
                        size="icon"
                        className={cn(
                            "text-text-secondary hover:text-text-primary relative",
                            showNotifications && "bg-surface-high text-text-primary"
                        )}
                        onClick={() => setShowNotifications(!showNotifications)}
                    >
                        <Bell className="h-5 w-5" />
                        {unreadCount > 0 && (
                            <span className="absolute top-1.5 right-1.5 h-2 w-2 bg-accent rounded-full border border-background" />
                        )}
                    </Button>

                    {showNotifications && (
                        <div className="absolute right-0 mt-2 w-80 bg-surface border border-border shadow-2xl rounded-lg overflow-hidden animate-in fade-in zoom-in-95 duration-200">
                            <div className="p-4 border-b border-border flex justify-between items-center">
                                <h3 className="font-medium text-sm">Notifications</h3>
                                <Button variant="ghost" size="sm" className="h-7 text-[10px] uppercase font-mono" onClick={() => setNotifications(n => n.map(x => ({ ...x, read: true })))}>
                                    Mark all read
                                </Button>
                            </div>
                            <div className="max-h-96 overflow-y-auto">
                                {notifications.length === 0 ? (
                                    <div className="p-8 text-center text-text-muted text-xs">
                                        No new notifications
                                    </div>
                                ) : (
                                    notifications.map(n => (
                                        <div key={n.id} className={cn(
                                            "p-4 border-b border-border/50 last:border-0 hover:bg-surface-high/30 transition-colors cursor-pointer relative",
                                            !n.read && "bg-accent/5"
                                        )}>
                                            {!n.read && <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-accent" />}
                                            <div className="flex gap-3">
                                                <div className="mt-0.5">
                                                    {n.type === "success" && <CheckCircle2 size={14} className="text-green-500" />}
                                                    {n.type === "info" && <Clock size={14} className="text-accent" />}
                                                    {n.type === "warning" && <AlertCircle size={14} className="text-amber-500" />}
                                                </div>
                                                <div className="space-y-1">
                                                    <p className="text-sm font-medium leading-none">{n.title}</p>
                                                    <p className="text-xs text-text-muted leading-relaxed">{n.message}</p>
                                                    <p className="text-[10px] text-text-muted font-mono uppercase">
                                                        {new Date(n.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                                    </p>
                                                </div>
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>
                    )}
                </div>

                <Button
                    variant="ghost"
                    size="icon"
                    className="text-text-secondary hover:text-text-primary"
                    onClick={() => authService.logout()}
                    title="Logout"
                >
                    <LogOut className="h-5 w-5" />
                </Button>
            </div>
        </header>
    );
}
