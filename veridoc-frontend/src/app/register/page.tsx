"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import dynamic from "next/dynamic";
const PipelineVisualizer = dynamic(
    () => import("@/components/auth/pipeline-visualizer").then((mod) => mod.PipelineVisualizer),
    { ssr: false }
);
import { ArrowRight, User, Mail } from "lucide-react";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { authService } from "@/services/auth.service";

export default function RegisterPage() {
    const router = useRouter();
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState("");

    const getErrorMessage = (err: any, fallback: string) => {
        const detail = err?.response?.data?.detail ?? err?.message;
        if (typeof detail === "string") return detail;
        if (Array.isArray(detail)) {
            return detail.map((item) => item?.msg ?? String(item)).join(", ");
        }
        if (detail && typeof detail === "object") {
            return detail.msg ?? JSON.stringify(detail);
        }
        return fallback;
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);
        setError("");

        const formData = new FormData(e.target as HTMLFormElement);
        const email = formData.get("email") as string;
        const password = formData.get("password") as string;

        if (password.length > 64) {
            setError("Password too long (max 64 characters)");
            setIsLoading(false);
            return;
        }

        try {
            await authService.register({ email, password });
            router.push("/onboarding");
        } catch (err: any) {
            setError(getErrorMessage(err, "Registration failed"));
            setIsLoading(false);
        }
    };

    return (
        <div className="flex min-h-screen bg-background text-text-primary">
            {/* Left Panel - Form */}
            <div className="w-full md:w-1/2 flex flex-col justify-center px-8 md:px-24 py-12 border-r border-border">
                <div className="mb-2 w-max">
                    <Link href="/" className="font-display text-2xl text-text-primary hover:opacity-80 transition-opacity">DevFrames Synapse</Link>
                </div>

                <div className="space-y-6 mt-12 max-w-sm w-full mx-auto md:mx-0">
                    <div className="space-y-2">
                        <h1 className="font-display text-4xl">Start with a document.</h1>
                        <p className="font-mono text-sm text-accent">Create your document intelligence account.</p>
                    </div>

                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div className="space-y-2">
                            <label className="text-xs font-mono text-text-secondary uppercase">Full Name</label>
                            <div className="relative">
                                <User className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted h-4 w-4" />
                                <Input type="text" placeholder="Dr. Sarah Connor" className="pl-9" required />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <label className="text-xs font-mono text-text-secondary uppercase">Email</label>
                            <div className="relative">
                                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted h-4 w-4" />
                                <Input name="email" type="email" placeholder="name@company.com" className="pl-9" required />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <label className="text-xs font-mono text-text-secondary uppercase">Password</label>
                            <Input name="password" type="password" required maxLength={64} />
                            <div className="h-1 w-full bg-surface-high rounded-full overflow-hidden mt-2">
                                <div className="h-full bg-red-500 w-[20%]" />
                            </div>
                            <p className="text-[10px] text-text-muted text-right">Weak password</p>
                        </div>

                        {error && (
                            <div className="text-xs text-red-500 bg-red-500/10 p-2 rounded border border-red-500/20 text-center">
                                {error}
                            </div>
                        )}

                        <Button
                            type="submit"
                            variant="primary"
                            className="w-full group"
                            isLoading={isLoading}
                        >
                            {!isLoading && (
                                <>
                                    Create Account
                                    <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
                                </>
                            )}
                            {isLoading && "Creating..."}
                        </Button>
                    </form>

                    <div className="text-center text-sm text-text-secondary mt-6">
                        Already have an account?{" "}
                        <Link href="/login" className="text-accent hover:underline">Sign In</Link>
                    </div>
                </div>
            </div>

            {/* Right Panel - Visualization */}
            <div className="hidden md:block w-1/2 relative bg-slate-50">
                <PipelineVisualizer />
            </div>
        </div>
    );
}
