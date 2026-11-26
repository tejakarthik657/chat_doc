"use client";

import { useState } from "react";
import { User, Lock, SlidersHorizontal, ChartNoAxesColumn } from "lucide-react";
import { cn } from "@/lib/utils";
import { ProfileSection } from "@/components/settings/profile-section";
import { SecuritySection } from "@/components/settings/security-section";
import { RagSettingsSection } from "@/components/settings/rag-settings-section";
import { UsageLimitsSection } from "@/components/settings/usage-limits-section";

type SettingsSection = "profile" | "security" | "preferences" | "limits";

export default function SettingsPage() {
    const [activeSection, setActiveSection] = useState<SettingsSection>("profile");

    const navItems = [
        {
            id: "account",
            label: "Account",
            items: [
                { id: "profile" as const, label: "Profile", icon: User },
                { id: "security" as const, label: "Security", icon: Lock },
            ],
        },
        {
            id: "preferences",
            label: "Workspace",
            items: [
                { id: "preferences" as const, label: "Answer preferences", icon: SlidersHorizontal },
                { id: "limits" as const, label: "Usage & limits", icon: ChartNoAxesColumn },
            ],
        },
    ];

    return (
        <div className="mx-auto min-h-[calc(100vh-60px)] max-w-6xl px-4 py-6 sm:px-6 sm:py-8 lg:px-8">
            <header className="mb-8">
                <p className="mb-2 font-mono text-xs uppercase tracking-[0.16em] text-accent">Your account</p>
                <h1 className="font-display text-3xl sm:text-4xl">Settings</h1>
                <p className="mt-2 max-w-2xl text-sm text-text-secondary">
                    Manage your Threadwell profile, sign-in security, and workspace usage.
                </p>
            </header>

            <div className="grid gap-8 lg:grid-cols-[220px,minmax(0,1fr)] lg:gap-12">
                <nav aria-label="Settings sections" className="space-y-5">
                    {navItems.map((section) => (
                        <div key={section.id} className="space-y-2">
                            <h2 className="px-2 font-mono text-xs uppercase tracking-wider text-text-muted">
                                {section.label}
                            </h2>
                            <div className="flex gap-2 overflow-x-auto pb-1 lg:flex-col lg:overflow-visible">
                            {section.items.map((item) => (
                                <button
                                    key={item.id}
                                    onClick={() => setActiveSection(item.id)}
                                    aria-current={activeSection === item.id ? "page" : undefined}
                                    className={cn(
                                        "flex shrink-0 items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm font-medium transition-colors lg:w-full",
                                        activeSection === item.id
                                            ? "bg-accent/10 text-accent"
                                            : "text-text-secondary hover:bg-surface-high/50 hover:text-text-primary"
                                    )}
                                >
                                    <item.icon size={16} />
                                    {item.label}
                                </button>
                            ))}
                            </div>
                        </div>
                    ))}
                </nav>

                <main className="min-w-0 max-w-3xl">
                {activeSection === "profile" && <ProfileSection />}
                {activeSection === "security" && <SecuritySection />}
                {activeSection === "preferences" && <RagSettingsSection />}
                {activeSection === "limits" && <UsageLimitsSection />}
                </main>
            </div>
        </div>
    );
}
