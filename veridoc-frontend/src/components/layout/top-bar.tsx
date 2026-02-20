"use client";

import { Search, Bell } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export function TopBar() {
    return (
        <header className="h-[60px] border-b border-border bg-background/50 backdrop-blur-sm fixed top-0 right-0 left-[240px] z-30 flex items-center px-6 gap-4">
            <div className="flex-1 max-w-xl relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted" />
                <Input
                    placeholder="Search across all documents..."
                    className="pl-9 bg-surface-high/50 border-transparent focus:bg-surface focus:border-accent"
                />
                <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1 pointer-events-none">
                    <kbd className="hidden sm:inline-flex h-5 items-center gap-1 rounded border border-border bg-surface px-1.5 font-mono text-[10px] font-medium text-text-muted">
                        ⌘K
                    </kbd>
                </div>
            </div>

            <div className="ml-auto flex items-center gap-4">
                <Button variant="ghost" size="icon" className="text-text-secondary hover:text-text-primary">
                    <Bell className="h-5 w-5" />
                </Button>
            </div>
        </header>
    );
}
