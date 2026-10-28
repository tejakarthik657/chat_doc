"use client";

import React, { useState } from "react";
import { 
    Activity, 
    AlertTriangle, 
    ArrowRight, 
    CheckCircle, 
    Play, 
    RefreshCw, 
    ShieldAlert, 
    X, 
    Zap 
} from "lucide-react";
import api from "@/lib/api";

interface WhatIfSimulatorModalProps {
    isOpen: boolean;
    onClose: () => void;
    projectId: string;
    availableNodes: string[];
    selectedNode?: string;
    onApplySimulationToGraph?: (impactedNodes: Record<string, any>) => void;
}

const PRESET_SCENARIOS = [
    "Complete outage / node unresponsiveness",
    "High latency spike (>5000ms) under load",
    "Corrupted payload / data validation mismatch",
    "Revoked API credentials / authorization failure"
];

export default function WhatIfSimulatorModal({
    isOpen,
    onClose,
    projectId,
    availableNodes,
    selectedNode: initialNode = "",
    onApplySimulationToGraph
}: WhatIfSimulatorModalProps) {
    const [targetNode, setTargetNode] = useState(initialNode || (availableNodes[0] || ""));
    const [scenario, setScenario] = useState(PRESET_SCENARIOS[0]);
    const [loading, setLoading] = useState(false);
    const [simulation, setSimulation] = useState<any>(null);

    const handleRunSimulation = async () => {
        if (!targetNode.trim() || !scenario.trim()) return;
        setLoading(true);
        try {
            const res = await api.post(`/projects/${projectId}/graph/simulate`, {
                perturbed_node: targetNode,
                scenario: scenario
            });
            setSimulation(res.data);
            if (onApplySimulationToGraph && res.data.impacted_nodes) {
                onApplySimulationToGraph(res.data.impacted_nodes);
            }
        } catch (err) {
            console.error("What-If Simulation failed:", err);
        } finally {
            setLoading(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-amber-600/10 text-amber-600 dark:bg-amber-500/20 dark:text-amber-400 flex items-center justify-center">
                            <Activity className="w-5 h-5" />
                        </div>
                        <div>
                            <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
                                Causal "What-If?" Simulator
                                <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300">
                                    Knowledge Graph Perturbation
                                </span>
                            </h2>
                            <p className="text-xs text-slate-500">
                                Dynamic topological failure cascading: simulate stress ripples across interconnected system entities.
                            </p>
                        </div>
                    </div>
                    <button 
                        onClick={onClose}
                        className="p-2 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-800"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Body */}
                <div className="p-6 overflow-y-auto space-y-6 flex-1">
                    {/* Controls */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-2">
                                Perturbed Graph Entity
                            </label>
                            {availableNodes && availableNodes.length > 0 ? (
                                <select
                                    value={targetNode}
                                    onChange={(e) => setTargetNode(e.target.value)}
                                    className="w-full text-sm rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3.5 py-2.5 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-amber-500"
                                >
                                    {availableNodes.map((n) => (
                                        <option key={n} value={n}>{n}</option>
                                    ))}
                                </select>
                            ) : (
                                <input
                                    type="text"
                                    value={targetNode}
                                    onChange={(e) => setTargetNode(e.target.value)}
                                    placeholder="Enter node name (e.g. Authentication Service)"
                                    className="w-full text-sm rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3.5 py-2.5 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-amber-500"
                                />
                            )}
                        </div>

                        <div>
                            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-2">
                                Perturbation Condition / Scenario
                            </label>
                            <input
                                type="text"
                                value={scenario}
                                onChange={(e) => setScenario(e.target.value)}
                                placeholder="Describe stress condition..."
                                className="w-full text-sm rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3.5 py-2.5 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-amber-500"
                            />
                        </div>
                    </div>

                    {/* Presets */}
                    <div className="space-y-1.5">
                        <span className="text-[11px] text-slate-400 font-mono">Quick Scenarios:</span>
                        <div className="flex flex-wrap gap-2">
                            {PRESET_SCENARIOS.map((s) => (
                                <button
                                    key={s}
                                    type="button"
                                    onClick={() => setScenario(s)}
                                    className={`text-xs px-2.5 py-1 rounded-lg border transition-colors ${
                                        scenario === s 
                                            ? "border-amber-500 bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300 font-medium"
                                            : "border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800"
                                    }`}
                                >
                                    {s}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Run Button */}
                    <button
                        onClick={handleRunSimulation}
                        disabled={loading || !targetNode}
                        className="w-full py-3 rounded-xl bg-amber-600 hover:bg-amber-700 text-white font-semibold text-xs flex items-center justify-center gap-2 shadow-lg shadow-amber-600/20 transition-all disabled:opacity-50"
                    >
                        {loading ? (
                            <>
                                <RefreshCw className="w-4 h-4 animate-spin" />
                                Computing Causal Ripple Matrix across Graph...
                            </>
                        ) : (
                            <>
                                <Zap className="w-4 h-4" />
                                Run "What-If?" Systemic Simulation
                            </>
                        )}
                    </button>

                    {/* Simulation Output */}
                    {simulation && (
                        <div className="space-y-6 pt-2 animate-in fade-in duration-300">
                            {/* Executive Summary */}
                            <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-200 dark:border-amber-900/40 text-xs text-slate-800 dark:text-slate-200 space-y-1">
                                <div className="font-bold flex items-center gap-1.5 text-amber-800 dark:text-amber-300">
                                    <ShieldAlert className="w-4 h-4" />
                                    Executive Systemic Impact:
                                </div>
                                <p className="leading-relaxed">
                                    {simulation.executive_summary}
                                </p>
                            </div>

                            {/* Cascade Chain */}
                            {simulation.cascade_chain && simulation.cascade_chain.length > 0 && (
                                <div className="space-y-2">
                                    <h4 className="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider">
                                        Failure Propagation Sequence
                                    </h4>
                                    <div className="space-y-2">
                                        {simulation.cascade_chain.map((link: any, idx: number) => (
                                            <div key={idx} className="flex items-center gap-2 p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-xs">
                                                <span className="font-bold text-red-600 dark:text-red-400">{link.source}</span>
                                                <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
                                                <span className="font-bold text-amber-600 dark:text-amber-400">{link.target}</span>
                                                <span className="text-slate-500 ml-auto font-mono text-[11px]">{link.impact}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Impacted Nodes Grid */}
                            {simulation.impacted_nodes && (
                                <div className="space-y-2">
                                    <h4 className="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider">
                                        Impacted Nodes & Vulnerability Weights
                                    </h4>
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                        {Object.entries(simulation.impacted_nodes).map(([nodeName, data]: [string, any]) => {
                                            const isCrit = data.risk_level === "CRITICAL";
                                            const isHigh = data.risk_level === "HIGH";
                                            return (
                                                <div 
                                                    key={nodeName} 
                                                    className={`p-3.5 rounded-xl border text-xs space-y-1 ${
                                                        isCrit 
                                                            ? "bg-red-50/50 dark:bg-red-950/20 border-red-200 dark:border-red-900/50" 
                                                            : isHigh 
                                                            ? "bg-amber-50/50 dark:bg-amber-950/20 border-amber-200 dark:border-amber-900/50" 
                                                            : "bg-slate-50 dark:bg-slate-800/40 border-slate-200 dark:border-slate-700"
                                                    }`}
                                                >
                                                    <div className="flex items-center justify-between">
                                                        <span className="font-bold text-slate-900 dark:text-white">{nodeName}</span>
                                                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                                            isCrit 
                                                                ? "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200" 
                                                                : isHigh 
                                                                ? "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200" 
                                                                : "bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-300"
                                                        }`}>
                                                            {data.risk_level} ({(data.failure_probability * 100).toFixed(0)}%)
                                                        </span>
                                                    </div>
                                                    <p className="text-slate-600 dark:text-slate-400 text-[11px]">
                                                        {data.impact}
                                                    </p>
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>
                            )}

                            {/* Mitigations */}
                            {simulation.mitigations && simulation.mitigations.length > 0 && (
                                <div className="p-4 rounded-xl bg-emerald-50/60 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-900/50 space-y-2">
                                    <div className="text-xs font-bold text-emerald-800 dark:text-emerald-300 flex items-center gap-1.5">
                                        <CheckCircle className="w-4 h-4 text-emerald-600" />
                                        Recommended Architectural Mitigations:
                                    </div>
                                    <ul className="list-disc list-inside space-y-1 text-xs text-emerald-700 dark:text-emerald-300">
                                        {simulation.mitigations.map((m: string, idx: number) => (
                                            <li key={idx}>{m}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
