"use client";

import React, { useState } from "react";
import { 
    Play, 
    CheckCircle2, 
    XCircle, 
    AlertTriangle, 
    Clock, 
    Code2, 
    Terminal, 
    RefreshCw, 
    Sliders 
} from "lucide-react";
import api from "@/lib/api";

interface LivingCodeSandboxProps {
    initialCode?: string;
    initialTests?: string;
    title?: string;
}

export default function LivingCodeSandbox({
    initialCode = "def calculate_risk(metric_a, metric_b):\n    return round((metric_a * 0.4) + (metric_b * 0.6), 2)\n\nprint('Calculated Risk Score:', calculate_risk(85.0, 92.5))",
    initialTests = "assert calculate_risk(10, 20) == 16.0\nassert calculate_risk(0, 0) == 0.0\nassert calculate_risk(100, 100) == 100.0",
    title = "Living Code Twin Sandbox"
}: LivingCodeSandboxProps) {
    const [code, setCode] = useState(initialCode);
    const [tests, setTests] = useState(initialTests);
    const [showTests, setShowTests] = useState(false);
    const [isRunning, setIsRunning] = useState(false);
    const [result, setResult] = useState<any>(null);

    const handleRun = async () => {
        setIsRunning(true);
        try {
            const res = await api.post("/features/execute-code", {
                code: code,
                test_cases: showTests && tests.trim() ? tests.trim() : undefined,
                timeout: 5
            });
            setResult(res.data);
        } catch (err: any) {
            console.error("Code execution failed:", err);
            setResult({
                stdout: "",
                stderr: err.response?.data?.detail || "Execution failed.",
                returncode: 1,
                status: "ERROR",
                tests_total: 0,
                tests_passed: 0,
                duration_ms: 0
            });
        } finally {
            setIsRunning(false);
        }
    };

    return (
        <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 overflow-hidden shadow-sm space-y-0">
            {/* Toolbar */}
            <div className="flex items-center justify-between px-4 py-3 bg-slate-50 dark:bg-slate-800/60 border-b border-slate-200 dark:border-slate-800">
                <div className="flex items-center gap-2">
                    <Code2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                    <span className="text-xs font-bold text-slate-800 dark:text-slate-200">{title}</span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300">
                        AST Verified
                    </span>
                </div>

                <div className="flex items-center gap-2">
                    <button
                        type="button"
                        onClick={() => setShowTests(!showTests)}
                        className={`px-2.5 py-1 rounded-lg text-xs font-medium border transition-colors ${
                            showTests 
                                ? "bg-indigo-50 border-indigo-200 text-indigo-700 dark:bg-indigo-950 dark:border-indigo-800 dark:text-indigo-300"
                                : "border-slate-200 text-slate-600 dark:border-slate-700 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
                        }`}
                    >
                        {showTests ? "Hide Unit Tests" : "Add Unit Assertions"}
                    </button>

                    <button
                        onClick={handleRun}
                        disabled={isRunning}
                        className="px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold flex items-center gap-1.5 shadow-sm transition-all disabled:opacity-50"
                    >
                        {isRunning ? (
                            <>
                                <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Running...
                            </>
                        ) : (
                            <>
                                <Play className="w-3.5 h-3.5 fill-white" /> Run Sandbox
                            </>
                        )}
                    </button>
                </div>
            </div>

            {/* Code Input */}
            <div className="p-4 space-y-3">
                <div>
                    <label className="text-[10px] font-mono uppercase text-slate-400 block mb-1">
                        Python Execution Sandbox
                    </label>
                    <textarea
                        value={code}
                        onChange={(e) => setCode(e.target.value)}
                        rows={6}
                        className="w-full font-mono text-xs p-3 rounded-xl bg-slate-950 text-emerald-400 border border-slate-800 focus:outline-none focus:ring-1 focus:ring-emerald-500 leading-relaxed"
                    />
                </div>

                {showTests && (
                    <div className="space-y-1">
                        <label className="text-[10px] font-mono uppercase text-indigo-500 font-semibold block">
                            Automated Assertions / Test Cases
                        </label>
                        <textarea
                            value={tests}
                            onChange={(e) => setTests(e.target.value)}
                            rows={3}
                            placeholder="assert func(x) == expected"
                            className="w-full font-mono text-xs p-3 rounded-xl bg-slate-950 text-indigo-300 border border-indigo-900/40 focus:outline-none focus:ring-1 focus:ring-indigo-500 leading-relaxed"
                        />
                    </div>
                )}
            </div>

            {/* Results / Telemetry */}
            {result && (
                <div className="border-t border-slate-200 dark:border-slate-800 p-4 bg-slate-50/70 dark:bg-slate-950/40 space-y-3 animate-in fade-in duration-200">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <span className={`flex items-center gap-1 text-xs font-bold px-2.5 py-0.5 rounded-full ${
                                result.status === "PASSED"
                                    ? "bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-300"
                                    : "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300"
                            }`}>
                                {result.status === "PASSED" ? (
                                    <CheckCircle2 className="w-3.5 h-3.5" />
                                ) : (
                                    <XCircle className="w-3.5 h-3.5" />
                                )}
                                {result.status}
                            </span>

                            {result.tests_total > 0 && (
                                <span className="text-xs font-mono text-slate-600 dark:text-slate-400">
                                    Tests: <strong className="text-slate-900 dark:text-white">{result.tests_passed}/{result.tests_total} Passed</strong>
                                </span>
                            )}
                        </div>

                        <span className="text-xs font-mono text-slate-400 flex items-center gap-1">
                            <Clock className="w-3.5 h-3.5" /> {result.duration_ms}ms
                        </span>
                    </div>

                    {/* Stdout / Stderr console */}
                    <div className="bg-slate-950 text-slate-200 p-3 rounded-xl font-mono text-xs overflow-x-auto space-y-1">
                        <div className="flex items-center gap-1.5 text-[10px] text-slate-400 border-b border-slate-800 pb-1 mb-1">
                            <Terminal className="w-3 h-3" /> Console Output
                        </div>
                        {result.stdout && (
                            <pre className="text-emerald-400 whitespace-pre-wrap">{result.stdout}</pre>
                        )}
                        {result.stderr && (
                            <pre className="text-red-400 whitespace-pre-wrap">{result.stderr}</pre>
                        )}
                        {!result.stdout && !result.stderr && (
                            <span className="text-slate-500 italic">Program finished with return code {result.returncode} (No output).</span>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
