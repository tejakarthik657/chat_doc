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
            <div className="min-h-[100dvh] bg-background text-text-primary overflow-x-hidden">
                <Sidebar />
                <TopBar />
                <div className="pl-0 md:pl-[240px] pt-[60px] min-h-[100dvh] bg-background w-full transition-all duration-300">
                    {children}
                </div>
            </div>
        </SearchProvider>
    );
}
