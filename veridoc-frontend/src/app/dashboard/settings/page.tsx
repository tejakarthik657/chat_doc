"use client";

import { useState } from "react";
import { User, Lock, Settings, BarChart } from "lucide-react";
import { cn } from "@/lib/utils";
import { ProfileSection } from "@/components/settings/profile-section";
import { SecuritySection } from "@/components/settings/security-section";
import { RagSettingsSection } from "@/components/settings/rag-settings-section";

export default function SettingsPage() {
    const [activeSection, setActiveSection] = useState("rag");

    const navItems = [
        {
            id: "account", label: "Account", items: [
                { id: "profile", label: "Profile", icon: User },
                { id: "security", label: "Security", icon: Lock },
            ]
        },
        {
            id: "preferences", label: "Preferences", items: [
                { id: "rag", label: "RAG Settings", icon: Settings },
                { id: "limits", label: "Usage & Limits", icon: BarChart },
            ]
        },
    ];

    return (
        <div className="p-8 max-w-[1600px] mx-auto min-h-[calc(100vh-60px)] flex gap-12">
            {/* Settings Navigation Sidebar */}
            <div className="w-64 shrink-0 space-y-8">
                <h1 className="font-display text-3xl mb-8">Settings</h1>

                {navItems.map((section) => (
                    <div key={section.id} className="space-y-2">
                        <h3 className="font-mono text-xs text-text-muted uppercase tracking-wider px-2 mb-2">{section.label}</h3>
                        <div className="space-y-1">
                            {section.items.map((item) => (
                                <button
                                    key={item.id}
                                    onClick={() => setActiveSection(item.id)}
                                    className={cn(
                                        "w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors text-left",
                                        activeSection === item.id
                                            ? "bg-surface-high text-accent"
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
            </div>

            {/* Content Area */}
            <div className="flex-1 max-w-3xl">
                {activeSection === "profile" && <ProfileSection />}
                {activeSection === "security" && <SecuritySection />}
                {activeSection === "rag" && <RagSettingsSection />}
                {/* Placeholder for others */}
            </div>
        </div>
    );
}
