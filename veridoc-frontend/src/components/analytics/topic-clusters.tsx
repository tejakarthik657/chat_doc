"use client";

import { motion } from "framer-motion";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { ClusterSummary } from "@/services/analytics.service";

interface TopicClustersProps {
    data?: ClusterSummary[];
}

export function TopicClusters({ data = [] }: TopicClustersProps) {
    // Fixed positions for up to 5 clusters to ensure they look good
    const POSITIONS = [
        { x: 20, y: 30, color: "bg-accent" },
        { x: 60, y: 20, color: "bg-accent/80" },
        { x: 40, y: 70, color: "bg-accent/60" },
        { x: 80, y: 60, color: "bg-surface-high" },
        { x: 15, y: 75, color: "bg-accent/40" },
    ];

    const clusters = data.slice(0, 5).map((c, i) => ({
        ...c,
        // Scale size based on question count (min 60, max 140)
        size: Math.max(60, Math.min(140, c.question_count * 10)),
        x: POSITIONS[i]?.x ?? 50,
        y: POSITIONS[i]?.y ?? 50,
        color: POSITIONS[i]?.color ?? "bg-surface-high"
    }));

    if (clusters.length === 0) {
        return (
            <Card className="h-[400px] relative overflow-hidden bg-surface/50 border-border/50">
                <CardHeader>
                    <CardTitle>What You&apos;ve Been Asking About</CardTitle>
                </CardHeader>
                <CardContent className="h-full flex items-center justify-center text-text-muted font-mono text-xs">
                    No topic clusters generated yet.
                </CardContent>
            </Card>
        )
    }


    return (
        <Card className="h-[400px] relative overflow-hidden bg-surface/50 border-border/50">
            <CardHeader>
                <CardTitle>What You&apos;ve Been Asking About</CardTitle>
            </CardHeader>
            <CardContent className="h-full relative">
                <div className="absolute inset-0 bg-[url('/grid.svg')] opacity-5 pointer-events-none" />

                {clusters.map((cluster) => (
                    <motion.div
                        key={cluster.cluster_id}
                        initial={{ scale: 0 }}
                        animate={{
                            scale: 1,
                            y: [0, -10, 0],
                        }}
                        transition={{
                            scale: { duration: 0.5 },
                            y: { duration: 4, repeat: Infinity, ease: "easeInOut", delay: cluster.cluster_id * 0.2 }
                        }}
                        style={{
                            width: cluster.size,
                            height: cluster.size,
                            left: `${cluster.x}%`,
                            top: `${cluster.y}%`
                        }}
                        className={`absolute rounded-full flex items-center justify-center text-xs font-mono font-bold text-background ${cluster.color} shadow-lg backdrop-blur-sm -translate-x-1/2 -translate-y-1/2 cursor-pointer hover:scale-110 transition-transform z-10`}
                        title={`${cluster.question_count} questions`}
                    >
                        {cluster.label}
                    </motion.div>
                ))}
            </CardContent>
        </Card>
    );
}
