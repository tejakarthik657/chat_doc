"use client";

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { PHASES, Phase } from '@/lib/three/scene-engine';
import { cn } from '@/lib/utils';
import { Activity, Database, Lock, Server, Share2, Wifi } from 'lucide-react';

export default function HudOverlay({ phase }: { phase: Phase }) {
    const [metrics, setMetrics] = useState({
        fps: 60,
        nodes: 0,
        status: 'IDLE'
    });

    useEffect(() => {
        const interval = setInterval(() => {
            setMetrics(prev => ({
                fps: Math.floor(58 + Math.random() * 4),
                nodes: phase === PHASES.GALAXY ? 58402 : Math.floor(Math.random() * 1000),
                status: phase.toUpperCase()
            }));
        }, 500);
        return () => clearInterval(interval);
    }, [phase]);

    return (
        <div className="absolute inset-0 z-10 pointer-events-none select-none overflow-hidden">
            {/* Corner Brackets */}
            <div className="absolute top-6 left-6 w-8 h-8 border-t border-l border-white/20" />
            <div className="absolute top-6 right-6 w-8 h-8 border-t border-r border-white/20" />
            <div className="absolute bottom-6 left-6 w-8 h-8 border-b border-l border-white/20" />
            <div className="absolute bottom-6 right-6 w-8 h-8 border-b border-r border-white/20" />

            {/* Left Sidebar Status */}
            <div className="absolute top-1/2 left-8 -translate-y-1/2 flex flex-col gap-6">
                <div className="flex flex-col gap-2">
                    <div className="flex items-center gap-3 text-emerald-400/80">
                        <Database size={14} />
                        <span className="font-mono text-[10px] tracking-widest uppercase">Vector DB</span>
                    </div>
                    <div className="h-24 w-1 bg-white/5 relative overflow-hidden rounded-full ml-1.5">
                        <motion.div
                            className="absolute bottom-0 w-full bg-emerald-500"
                            animate={{ height: ["20%", "60%", "40%", "80%"] }}
                            transition={{ repeat: Infinity, duration: 4 }}
                        />
                    </div>
                </div>

                <div className="flex flex-col gap-2">
                    <div className="flex items-center gap-3 text-cyan-400/80">
                        <Server size={14} />
                        <span className="font-mono text-[10px] tracking-widest uppercase">System</span>
                    </div>
                    <div className="font-mono text-[10px] text-white/40 space-y-1">
                        <div>MEM: 14GB</div>
                        <div>CPU: 12%</div>
                        <div>LAT: 24ms</div>
                    </div>
                </div>
            </div>

            {/* Right Sidebar Status */}
            <div className="absolute top-1/2 right-8 -translate-y-1/2 flex flex-col items-end gap-6 text-right">
                <div className="flex flex-col gap-2 items-end">
                    <div className="flex items-center gap-3 text-amber-400/80">
                        <span className="font-mono text-[10px] tracking-widest uppercase">Security</span>
                        <Lock size={14} />
                    </div>
                    <div className="font-mono text-[10px] text-emerald-500">ENCRYPTED</div>
                </div>

                <div className="flex flex-col gap-2 items-end">
                    <div className="flex items-center gap-3 text-violet-400/80">
                        <span className="font-mono text-[10px] tracking-widest uppercase">Network</span>
                        <Wifi size={14} />
                    </div>
                    <div className="flex gap-1">
                        {[1, 2, 3, 4].map(i => (
                            <motion.div
                                key={i}
                                className="w-1 h-4 bg-violet-500/40"
                                animate={{ opacity: [0.3, 1, 0.3] }}
                                transition={{ repeat: Infinity, duration: 1.5, delay: i * 0.2 }}
                            />
                        ))}
                    </div>
                </div>
            </div>

            {/* Bottom Bar */}
            <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex items-center gap-8">
                <div className="flex items-center gap-2">
                    <Activity size={12} className="text-white/40" />
                    <span className="font-mono text-[10px] text-white/40">{metrics.fps} FPS</span>
                </div>
                <div className="h-3 w-[1px] bg-white/10" />
                <div className="font-mono text-[10px] text-white/60">
                    PHASE: <span className="text-emerald-400">{metrics.status}</span>
                </div>
                <div className="h-3 w-[1px] bg-white/10" />
                <div className="font-mono text-[10px] text-white/40">
                    NODES: {metrics.nodes.toLocaleString()}
                </div>
            </div>
        </div>
    );
}
