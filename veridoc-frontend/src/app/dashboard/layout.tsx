"use client";

import { Sidebar } from "@/components/layout/sidebar";
import { TopBar } from "@/components/layout/top-bar";
import { SearchProvider } from "@/lib/contexts/search-context";

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <SearchProvider>
            <div className="min-h-screen bg-background text-text-primary">
                <Sidebar />
                <TopBar />
                <div className="pl-[240px] pt-[60px] min-h-screen bg-background">
                    {children}
                </div>
            </div>
        </SearchProvider>
    );
}
