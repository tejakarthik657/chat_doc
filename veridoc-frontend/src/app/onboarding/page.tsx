"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { UploadDropzone } from "@/components/upload/upload-dropzone";
import { ChatInterface } from "@/components/chat/chat-interface";
import { ArrowRight, Check, FileText, Upload, MessageSquare } from "lucide-react";
import Link from "next/link";

export default function OnboardingPage() {
    const [step, setStep] = useState(1);

    const nextStep = () => setStep(s => Math.min(s + 1, 3));

    return (
        <div className="min-h-screen bg-background text-text-primary flex flex-col">
            {/* Progress Header */}
            <div className="h-[60px] flex items-center justify-center border-b border-border bg-background/50 backdrop-blur fixed top-0 w-full z-10">
                <div className="flex items-center gap-4">
                    {[1, 2, 3].map(i => (
                        <div key={i} className="flex items-center">
                            <div className={`h-8 w-8 rounded-full flex items-center justify-center font-mono text-sm border transition-colors ${step === i ? "bg-accent text-black border-accent" :
                                    step > i ? "bg-accent/20 text-accent border-accent" :
                                        "bg-surface-high text-text-muted border-border"
                                }`}>
                                {step > i ? <Check size={16} /> : i}
                            </div>
                            {i < 3 && <div className={`w-12 h-px mx-2 ${step > i ? "bg-accent" : "bg-border"}`} />}
                        </div>
                    ))}
                </div>
            </div>

            <div className="flex-1 pt-[60px] flex items-center justify-center p-8">
                <AnimatePresence mode="wait">
                    {step === 1 && (
                        <motion.div
                            key="step1"
                            initial={{ opacity: 0, x: 20 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: -20 }}
                            className="max-w-4xl w-full grid grid-cols-1 md:grid-cols-2 gap-12 items-center"
                        >
                            <div className="space-y-6">
                                <div className="h-20 w-20 bg-surface-high border border-border rounded-2xl flex items-center justify-center text-accent mb-8">
                                    <FileText size={40} />
                                </div>
                                <h1 className="font-display text-5xl">The document doesn't lie.</h1>
                                <p className="text-text-secondary text-lg leading-relaxed">
                                    Unlike chatbots that guess, DevFrames Synapse grounds every answer in your specific file.
                                    If the answer isn't there, we tell you. No hallucinations.
                                </p>
                                <Button variant="primary" size="lg" onClick={nextStep} className="mt-4">
                                    Let's Get Started <ArrowRight className="ml-2" />
                                </Button>
                            </div>

                            <Card className="p-6 bg-surface-high/20 border-border/50 backdrop-blur relative overflow-hidden">
                                <div className="absolute inset-0 bg-gradient-to-br from-accent/5 to-transparent pointer-events-none" />
                                {/* Mock Chat Bubble */}
                                <div className="space-y-4">
                                    <div className="flex justify-end">
                                        <div className="bg-surface text-text-primary px-4 py-3 rounded-lg max-w-[80%] text-sm rounded-tr-none">
                                            What is the coverage limit?
                                        </div>
                                    </div>
                                    <div className="flex justify-start">
                                        <div className="bg-accent/10 text-text-primary px-4 py-3 rounded-lg max-w-[90%] text-sm rounded-tl-none border border-accent/20">
                                            The coverage limit is <span className="font-bold text-accent">$2,000,000</span> per occurrence.
                                            <div className="mt-2 flex gap-2">
                                                <span className="text-[10px] bg-amber-500/10 text-amber-500 border border-amber-500/20 px-1.5 py-0.5 rounded font-mono">[p.4] Policy Declaration</span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </Card>
                        </motion.div>
                    )}

                    {step === 2 && (
                        <motion.div
                            key="step2"
                            initial={{ opacity: 0, x: 20 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: -20 }}
                            className="max-w-3xl w-full text-center space-y-8"
                        >
                            <div className="space-y-2">
                                <h1 className="font-display text-4xl">Upload your first document.</h1>
                                <p className="text-text-secondary">Contracts, research papers, manuals. Any PDF with text.</p>
                            </div>

                            <UploadDropzone />

                            <div className="pt-8">
                                <button onClick={nextStep} className="text-sm text-text-muted hover:text-text-primary hover:underline">
                                    Skip for now, I'll use a sample doc
                                </button>
                            </div>
                        </motion.div>
                    )}

                    {step === 3 && (
                        <motion.div
                            key="step3"
                            initial={{ opacity: 0, x: 20 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: -20 }}
                            className="max-w-5xl w-full h-[600px] border border-border rounded-xl overflow-hidden bg-background shadow-2xl flex flex-col md:flex-row"
                        >
                            <div className="w-full md:w-1/3 bg-surface p-8 border-r border-border flex flex-col justify-center space-y-6">
                                <div className="h-12 w-12 bg-accent/10 border border-accent/20 rounded-lg flex items-center justify-center text-accent">
                                    <MessageSquare size={24} />
                                </div>
                                <h2 className="font-display text-3xl">Ask away.</h2>
                                <p className="text-text-secondary text-sm">
                                    Try asking specific questions. DevFrames Synapse will search, rerank, and cite the exact source page.
                                </p>

                                <div className="space-y-2 pt-4">
                                    <div className="text-xs font-mono text-text-muted uppercase">Try asking:</div>
                                    <div className="p-2 bg-background border border-border rounded text-sm text-text-secondary hover:text-accent cursor-pointer transition-colors">
                                        "Summarize the key risks."
                                    </div>
                                    <div className="p-2 bg-background border border-border rounded text-sm text-text-secondary hover:text-accent cursor-pointer transition-colors">
                                        "What are the payment terms?"
                                    </div>
                                </div>

                                <Link href="/dashboard" className="mt-auto">
                                    <Button variant="primary" className="w-full">
                                        Go to Dashboard <ArrowRight className="ml-2" size={16} />
                                    </Button>
                                </Link>
                            </div>

                            <div className="flex-1 bg-background relative">
                                <div className="absolute inset-0 pointer-events-none z-10 bg-gradient-to-t from-background via-transparent to-transparent opacity-50" />
                                <ChatInterface docId="onboarding" onCitationClick={() => { }} />
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>

            <div className="fixed bottom-6 left-6">
                <Link href="/dashboard" className="text-xs font-mono text-text-muted hover:text-text-primary transition-colors">
                    Skip setup →
                </Link>
            </div>
        </div>
    );
}
