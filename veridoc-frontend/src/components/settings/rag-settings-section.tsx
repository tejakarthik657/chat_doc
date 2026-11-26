"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Layers3, SearchCheck, ShieldCheck } from "lucide-react";

const retrievalFeatures = [
    {
        title: "Meaning + keyword search",
        description: "Search combines semantic matching with exact terms to find useful passages across your sources.",
        icon: SearchCheck,
    },
    {
        title: "Automatic relevance ranking",
        description: "Relevant passages are ranked automatically for each question. You don’t need to tune a threshold.",
        icon: Layers3,
    },
    {
        title: "Source-linked answers",
        description: "Answers include references to the documents and projects used to form them.",
        icon: ShieldCheck,
    },
];

export function RagSettingsSection() {
    return (
        <div className="space-y-6">
            <div>
                <h2 className="mb-1 font-display text-2xl">Answer preferences</h2>
                <p className="text-sm text-text-secondary">
                    Threadwell manages retrieval automatically so answers stay consistent across your saved sources.
                </p>
            </div>

            <div className="space-y-4">
                {retrievalFeatures.map(({ title, description, icon: Icon }) => (
                    <Card key={title}>
                        <CardHeader className="flex flex-row items-start gap-4 space-y-0 p-5 sm:p-6">
                            <span className="mt-0.5 rounded-lg bg-accent/10 p-2 text-accent">
                                <Icon size={18} />
                            </span>
                            <div className="space-y-1">
                                <CardTitle className="text-base">{title}</CardTitle>
                                <p className="text-sm leading-relaxed text-text-muted">{description}</p>
                            </div>
                        </CardHeader>
                    </Card>
                ))}
            </div>

            <Card className="border-accent/20 bg-accent/5">
                <CardContent className="p-5 text-sm leading-relaxed text-text-secondary sm:p-6">
                    Need stricter answers? Turn on <strong className="text-text-primary">Strict evidence mode</strong> in Ask Your Space for a question-by-question evidence check.
                </CardContent>
            </Card>
        </div>
    );
}
