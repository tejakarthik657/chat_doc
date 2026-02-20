"use client";

import { Sidebar } from "@/components/layout/sidebar";
import { TopBar } from "@/components/layout/top-bar";

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <div className="min-h-screen bg-background text-text-primary">
            <Sidebar />
            <TopBar />
            <div className="pl-[240px] pt-[60px] min-h-screen bg-background">
                {children}
            </div>
        </div>
    );
}
