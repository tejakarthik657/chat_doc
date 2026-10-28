"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import dynamic from "next/dynamic";
const PipelineVisualizer = dynamic(
    () => import("@/components/auth/pipeline-visualizer").then((mod) => mod.PipelineVisualizer),
    { ssr: false }
);
import { ArrowRight, Mail } from "lucide-react";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { authService } from "@/services/auth.service";

export default function LoginPage() {
    const router = useRouter();
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState("");

    // Prefetch dashboard in advance so transition is instantaneous (< 30ms)
    useEffect(() => {
        router.prefetch("/dashboard");
    }, [router]);

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

        try {
            await authService.login({ email, password });
            router.push("/dashboard");
        } catch (err: any) {
            setError(getErrorMessage(err, "Invalid email or password"));
            setIsLoading(false);
        }
    };

    return (
        <div className="flex min-h-screen bg-background text-text-primary">
            {/* Left Panel - Form */}
            <div className="w-full md:w-1/2 flex flex-col justify-center px-8 md:px-24 py-12 border-r border-border">
                <div className="mb-2 w-max">
                    <Link href="/" className="font-display text-2xl text-text-primary hover:opacity-80 transition-opacity">NEXUS AI</Link>
                </div>

                <div className="space-y-6 mt-12 max-w-sm w-full mx-auto md:mx-0">
                    <div className="space-y-2">
                        <h1 className="font-display text-4xl">Welcome back.</h1>
                        <p className="font-mono text-sm text-accent">Intelligence You Can Explore and Use.</p>
                    </div>

                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div className="space-y-2">
                            <label className="text-xs font-mono text-text-secondary uppercase">Email</label>
                            <div className="relative">
                                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted h-4 w-4" />
                                <Input name="email" type="email" placeholder="name@company.com" className="pl-9" required />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <div className="flex justify-between">
                                <label className="text-xs font-mono text-text-secondary uppercase">Password</label>
                                <Link href="#" className="text-xs font-mono text-text-muted hover:text-accent transition-colors">Forgot?</Link>
                            </div>
                            <Input name="password" type="password" required />
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
                                    Sign In
                                    <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
                                </>
                            )}
                            {isLoading && "Authenticating..."}
                        </Button>
                    </form>

                    <div className="relative">
                        <div className="absolute inset-0 flex items-center"><span className="w-full border-t border-border" /></div>
                        <div className="relative flex justify-center text-xs uppercase"><span className="bg-background px-2 text-text-muted">Or continue with</span></div>
                    </div>

                    <Button
                        type="button"
                        variant="ghost"
                        onClick={() => {
                            const rawApiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
                            const baseUrl = rawApiUrl.replace(/\/api\/?$/, "");
                            window.location.href = `${baseUrl}/api/auth/google`;
                        }}
                        className="w-full flex items-center justify-center gap-2 border border-slate-200 hover:bg-slate-50 font-medium py-2.5 transition-colors shadow-sm"
                    >
                        <svg className="w-4 h-4" viewBox="0 0 24 24">
                            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
                            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
                        </svg>
                        <span>Continue with Google</span>
                    </Button>

                    <div className="text-center text-sm text-text-secondary mt-6">
                        Don't have an account?{" "}
                        <Link href="/register" className="text-accent hover:underline">Register</Link>
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
