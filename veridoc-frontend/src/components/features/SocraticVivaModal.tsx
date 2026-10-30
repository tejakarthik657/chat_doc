"use client";

import React, { useState, useEffect, useRef } from "react";
import { 
    GraduationCap, 
    Mic, 
    MicOff, 
    Volume2, 
    Award, 
    AlertTriangle, 
    CheckCircle2, 
    ArrowRight, 
    RefreshCw, 
    X, 
    Sparkles,
    BookOpen
} from "lucide-react";
import api from "@/lib/api";

interface SocraticVivaModalProps {
    isOpen: boolean;
    onClose: () => void;
    projectId: string;
}

const BLOOM_LEVELS = [
    { id: "Remember", label: "Level 1: Remember", desc: "Recall terms & core facts" },
    { id: "Understand", label: "Level 2: Understand", desc: "Explain mechanisms in own words" },
    { id: "Apply", label: "Level 3: Apply", desc: "Solve real-world scenario" },
    { id: "Analyze", label: "Level 4: Analyze", desc: "Deconstruct trade-offs & edge cases" },
    { id: "Evaluate", label: "Level 5: Evaluate", desc: "Defend or critique architectures" },
    { id: "Create", label: "Level 6: Create", desc: "Synthesize novel mitigations" }
];

export default function SocraticVivaModal({ isOpen, onClose, projectId }: SocraticVivaModalProps) {
    const [topic, setTopic] = useState("");
    const [bloomLevel, setBloomLevel] = useState("Understand");
    const [isGenerating, setIsGenerating] = useState(false);
    const [isEvaluating, setIsEvaluating] = useState(false);
    
    // Viva session state
    const [currentQuestion, setCurrentQuestion] = useState<any>(null);
    const [studentAnswer, setStudentAnswer] = useState("");
    const [evaluation, setEvaluation] = useState<any>(null);

    // Audio & speech state
    const [isListening, setIsListening] = useState(false);
    const [speechSupported, setSpeechSupported] = useState(false);
    const recognitionRef = useRef<any>(null);

    useEffect(() => {
        if (typeof window !== "undefined") {
            const SpeechRec = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
            if (SpeechRec) {
                setSpeechSupported(true);
                const rec = new SpeechRec();
                rec.continuous = true;
                rec.interimResults = true;
                rec.lang = "en-US";
                rec.onresult = (e: any) => {
                    let transcript = "";
                    for (let i = 0; i < e.results.length; i++) {
                        transcript += e.results[i][0].transcript + " ";
                    }
                    setStudentAnswer((prev) => transcript.trim());
                };
                rec.onerror = (e: any) => {
                    console.error("Speech error:", e);
                    setIsListening(false);
                };
                rec.onend = () => {
                    setIsListening(false);
                };
                recognitionRef.current = rec;
            }
        }
    }, []);

    const toggleSpeech = () => {
        if (!recognitionRef.current) return;
        if (isListening) {
            recognitionRef.current.stop();
            setIsListening(false);
        } else {
            try {
                recognitionRef.current.start();
                setIsListening(true);
            } catch (err) {
                console.error(err);
            }
        }
    };

    const speakQuestion = (text: string) => {
        if (typeof window !== "undefined" && "speechSynthesis" in window) {
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = 1.0;
            window.speechSynthesis.speak(utterance);
        }
    };

    const handleStartViva = async (selectedLevel?: string) => {
        setIsGenerating(true);
        setEvaluation(null);
        setStudentAnswer("");
        const lvl = selectedLevel || bloomLevel;
        try {
            const res = await api.post("/features/socratic/start", {
                project_id: projectId,
                topic: topic.trim() || undefined,
                bloom_level: lvl
            });
            setCurrentQuestion(res.data);
            setBloomLevel(res.data.bloom_level || lvl);
            speakQuestion(res.data.question);
        } catch (err) {
            console.error("Failed to start viva:", err);
        } finally {
            setIsGenerating(false);
        }
    };

    const handleEvaluate = async () => {
        if (!studentAnswer.trim() || !currentQuestion) return;
        if (isListening && recognitionRef.current) {
            recognitionRef.current.stop();
            setIsListening(false);
        }
        setIsEvaluating(true);
        try {
            const res = await api.post("/features/socratic/evaluate", {
                question: currentQuestion.question,
                bloom_level: bloomLevel,
                student_answer: studentAnswer.trim(),
                context_snippet: currentQuestion.context_snippet || ""
            });
            setEvaluation(res.data);
        } catch (err) {
            console.error("Failed to evaluate answer:", err);
        } finally {
            setIsEvaluating(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-2 sm:p-4">
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl w-full max-w-4xl max-h-[92dvh] sm:max-h-[90vh] flex flex-col shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
                {/* Header */}
                <div className="flex items-center justify-between px-3.5 sm:px-6 py-3 sm:py-4 border-b border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50 gap-2">
                    <div className="flex items-center gap-2.5 sm:gap-3 min-w-0">
                        <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-indigo-600/10 text-indigo-600 dark:bg-indigo-500/20 dark:text-indigo-400 flex items-center justify-center shrink-0">
                            <GraduationCap className="w-5 h-5" />
                        </div>
                        <div className="min-w-0">
                            <h2 className="text-sm sm:text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2 truncate">
                                <span>The Socratic Viva Master</span>
                                <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300 hidden xs:inline">
                                    Oral Exam
                                </span>
                            </h2>
                            <p className="text-[11px] sm:text-xs text-slate-500 hidden sm:block truncate">
                                Active recall oral examination with adaptive Bloom's Taxonomy and real-time misconception diagnosis.
                            </p>
                        </div>
                    </div>
                    <button 
                        onClick={onClose}
                        className="p-1.5 sm:p-2 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-800 transition-all touch-manipulation active:scale-95 shrink-0"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Content */}
                <div className="p-3.5 sm:p-6 overflow-y-auto space-y-5 sm:space-y-6 flex-1 pb-[max(1rem,env(safe-area-inset-bottom))]">
                    {/* Setup / Configuration */}
                    {!currentQuestion && (
                        <div className="space-y-6">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-2">
                                        Examination Topic (Optional)
                                    </label>
                                    <input 
                                        type="text" 
                                        value={topic}
                                        onChange={(e) => setTopic(e.target.value)}
                                        placeholder="e.g. Distributed Consensus, Auth Architecture, Neural Attention"
                                        className="w-full text-base sm:text-sm rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3.5 py-2.5 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                                    />
                                    <p className="text-[11px] text-slate-400 mt-1">Leave blank to let examiner test the entire project knowledge base.</p>
                                </div>
                                <div>
                                    <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-2">
                                        Starting Bloom's Taxonomy Level
                                    </label>
                                    <select
                                        value={bloomLevel}
                                        onChange={(e) => setBloomLevel(e.target.value)}
                                        className="w-full text-base sm:text-sm rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3.5 py-2.5 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                                    >
                                        {BLOOM_LEVELS.map((lvl) => (
                                            <option key={lvl.id} value={lvl.id}>
                                                {lvl.label} - {lvl.desc}
                                            </option>
                                        ))}
                                    </select>
                                </div>
                            </div>

                            {/* Bloom taxonomy cards */}
                            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                                {BLOOM_LEVELS.map((lvl) => (
                                    <div 
                                        key={lvl.id}
                                        onClick={() => setBloomLevel(lvl.id)}
                                        className={`p-3 rounded-xl border cursor-pointer transition-all ${
                                            bloomLevel === lvl.id 
                                                ? "border-indigo-500 bg-indigo-50/50 dark:bg-indigo-950/30 shadow-sm"
                                                : "border-slate-100 dark:border-slate-800 hover:border-slate-300"
                                        }`}
                                    >
                                        <div className="text-xs font-bold text-slate-800 dark:text-slate-200">{lvl.label}</div>
                                        <div className="text-[11px] text-slate-500 mt-0.5">{lvl.desc}</div>
                                    </div>
                                ))}
                            </div>

                            <button
                                onClick={() => handleStartViva()}
                                disabled={isGenerating}
                                className="w-full py-3.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-sm flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/20 transition-all disabled:opacity-50"
                            >
                                {isGenerating ? (
                                    <>
                                        <RefreshCw className="w-4 h-4 animate-spin" />
                                        Preparing Viva Examination...
                                    </>
                                ) : (
                                    <>
                                        <Sparkles className="w-4 h-4" />
                                        Begin Oral Viva Examination
                                    </>
                                )}
                            </button>
                        </div>
                    )}

                    {/* Active Question & Oral Response Interface */}
                    {currentQuestion && (
                        <div className="space-y-6">
                            {/* Question Card */}
                            <div className="p-5 rounded-2xl bg-gradient-to-br from-indigo-500/10 via-purple-500/5 to-transparent border border-indigo-200 dark:border-indigo-800/50 relative">
                                <div className="flex items-center justify-between mb-3">
                                    <div className="flex items-center gap-2">
                                        <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-indigo-600 text-white">
                                            {currentQuestion.bloom_level || bloomLevel}
                                        </span>
                                        <span className="text-xs font-mono text-slate-500">
                                            Topic: {currentQuestion.topic || "Core Architecture"}
                                        </span>
                                    </div>
                                    <button 
                                        onClick={() => speakQuestion(currentQuestion.question)}
                                        title="Speak Question"
                                        className="p-1.5 rounded-lg bg-indigo-50 hover:bg-indigo-100 dark:bg-slate-800 dark:hover:bg-slate-700 text-indigo-600 dark:text-indigo-400"
                                    >
                                        <Volume2 className="w-4 h-4" />
                                    </button>
                                </div>
                                <h3 className="text-base md:text-lg font-semibold text-slate-900 dark:text-white leading-relaxed">
                                    "{currentQuestion.question}"
                                </h3>
                                {currentQuestion.key_concepts && (
                                    <div className="flex flex-wrap gap-1.5 mt-3">
                                        {currentQuestion.key_concepts.map((kc: string, i: number) => (
                                            <span key={i} className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                                                #{kc}
                                            </span>
                                        ))}
                                    </div>
                                )}
                            </div>

                            {/* Spoken Answer Input Area */}
                            <div className="space-y-3">
                                <div className="flex items-center justify-between">
                                    <label className="text-xs font-semibold uppercase text-slate-700 dark:text-slate-300 flex items-center gap-2">
                                        Your Spoken Oral Response:
                                        {isListening && (
                                            <span className="flex items-center gap-1 text-red-500 text-xs font-normal animate-pulse">
                                                <span className="w-2 h-2 rounded-full bg-red-500"></span> Recording Voice...
                                            </span>
                                        )}
                                    </label>
                                    <div className="flex items-center gap-2">
                                        {speechSupported && (
                                            <button
                                                type="button"
                                                onClick={toggleSpeech}
                                                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                                                    isListening 
                                                        ? "bg-red-500 hover:bg-red-600 text-white" 
                                                        : "bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200"
                                                }`}
                                            >
                                                {isListening ? <MicOff className="w-3.5 h-3.5" /> : <Mic className="w-3.5 h-3.5" />}
                                                {isListening ? "Stop Recording" : "Speak Answer"}
                                            </button>
                                        )}
                                    </div>
                                </div>

                                <textarea
                                    value={studentAnswer}
                                    onChange={(e) => setStudentAnswer(e.target.value)}
                                    rows={4}
                                    placeholder="Speak your answer using the microphone, or type your oral explanation here..."
                                    className="w-full text-base sm:text-sm rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-3.5 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                                />

                                <div className="flex items-center justify-between">
                                    <button
                                        onClick={() => handleStartViva()}
                                        className="text-xs text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 flex items-center gap-1"
                                    >
                                        <RefreshCw className="w-3 h-3" /> Change Question
                                    </button>

                                    <button
                                        onClick={handleEvaluate}
                                        disabled={isEvaluating || !studentAnswer.trim()}
                                        className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold flex items-center gap-2 shadow-md disabled:opacity-50 transition-all"
                                    >
                                        {isEvaluating ? (
                                            <>
                                                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                                                Evaluating Viva Answer...
                                            </>
                                        ) : (
                                            <>
                                                <Award className="w-3.5 h-3.5" />
                                                Submit Oral Response
                                            </>
                                        )}
                                    </button>
                                </div>
                            </div>

                            {/* Evaluation Report */}
                            {evaluation && (
                                <div className="p-5 rounded-2xl bg-slate-50 dark:bg-slate-800/70 border border-slate-200 dark:border-slate-700 space-y-4 animate-in fade-in duration-300">
                                    <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-700 pb-3">
                                        <div className="flex items-center gap-2">
                                            <div className={`px-2.5 py-1 rounded-full text-xs font-bold ${
                                                evaluation.overall_score >= 80 
                                                    ? "bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-300"
                                                    : evaluation.overall_score >= 60
                                                    ? "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300"
                                                    : "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300"
                                            }`}>
                                                {evaluation.verdict || "Assessment Complete"}
                                            </div>
                                            <span className="text-xs font-mono text-slate-500">
                                                Overall Score: <strong className="text-slate-900 dark:text-white font-sans text-sm">{evaluation.overall_score}%</strong>
                                            </span>
                                        </div>

                                        <button
                                            onClick={() => handleStartViva(evaluation.suggested_next_level)}
                                            className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium flex items-center gap-1.5 shadow-sm"
                                        >
                                            Next Question ({evaluation.suggested_next_level || "Advance"})
                                            <ArrowRight className="w-3 h-3" />
                                        </button>
                                    </div>

                                    {/* 3 Metrics */}
                                    <div className="grid grid-cols-3 gap-3">
                                        <div className="p-3 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-center">
                                            <div className="text-[11px] text-slate-500 font-medium uppercase tracking-wider">Accuracy</div>
                                            <div className="text-lg font-bold text-slate-900 dark:text-white mt-1">{evaluation.accuracy_score ?? 80}%</div>
                                        </div>
                                        <div className="p-3 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-center">
                                            <div className="text-[11px] text-slate-500 font-medium uppercase tracking-wider">Terminology</div>
                                            <div className="text-lg font-bold text-slate-900 dark:text-white mt-1">{evaluation.terminology_score ?? 75}%</div>
                                        </div>
                                        <div className="p-3 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-center">
                                            <div className="text-[11px] text-slate-500 font-medium uppercase tracking-wider">Conceptual Depth</div>
                                            <div className="text-lg font-bold text-slate-900 dark:text-white mt-1">{evaluation.depth_score ?? 85}%</div>
                                        </div>
                                    </div>

                                    {/* Critique */}
                                    {evaluation.critique && (
                                        <div className="p-3.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
                                            <div className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1 flex items-center gap-1.5">
                                                <GraduationCap className="w-4 h-4 text-indigo-500" />
                                                Examiner Critique:
                                            </div>
                                            <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                                                {evaluation.critique}
                                            </p>
                                        </div>
                                    )}

                                    {/* Misconceptions */}
                                    {evaluation.misconceptions && evaluation.misconceptions.length > 0 && (
                                        <div className="p-3.5 rounded-xl bg-red-50/60 dark:bg-red-950/20 border border-red-200 dark:border-red-900/50 space-y-2">
                                            <div className="text-xs font-semibold text-red-700 dark:text-red-400 flex items-center gap-1.5">
                                                <AlertTriangle className="w-4 h-4 text-red-500" />
                                                Diagnosed Misconceptions:
                                            </div>
                                            <ul className="list-disc list-inside space-y-1 text-xs text-red-600 dark:text-red-300">
                                                {evaluation.misconceptions.map((m: string, idx: number) => (
                                                    <li key={idx}>{m}</li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}

                                    {/* Ground Truth Citation */}
                                    {evaluation.ground_truth_citation && (
                                        <div className="p-3 rounded-xl bg-indigo-50/50 dark:bg-indigo-950/20 border border-indigo-100 dark:border-indigo-900/40 text-xs">
                                            <span className="font-semibold text-indigo-700 dark:text-indigo-400 flex items-center gap-1 mb-1">
                                                <BookOpen className="w-3.5 h-3.5" /> Ground Truth Source Citation:
                                            </span>
                                            <p className="italic text-slate-600 dark:text-slate-300">
                                                "{evaluation.ground_truth_citation}"
                                            </p>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
