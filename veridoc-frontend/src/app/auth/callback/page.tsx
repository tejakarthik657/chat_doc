"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2, AlertCircle, CheckCircle2 } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

function GoogleAuthCallbackContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
    const [errorMessage, setErrorMessage] = useState("");

    useEffect(() => {
        const token = searchParams.get("token");
        const error = searchParams.get("error");

        if (error) {
            setStatus("error");
            setErrorMessage(error === "access_denied" ? "Google login was cancelled or denied." : `Authentication failed (${error}).`);
            return;
        }

        if (token) {
            try {
                localStorage.setItem("token", token);
                setStatus("success");
                // Brief pause so user sees confirmation before instant transition
                setTimeout(() => {
                    window.location.href = "/dashboard";
                }, 400);
            } catch (err: any) {
                setStatus("error");
                setErrorMessage("Failed to store local session. Please try logging in again.");
            }
        } else {
            setStatus("error");
            setErrorMessage("No authentication token received from Google callback.");
        }
    }, [searchParams, router]);

    return (
        <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
            <div className="max-w-md w-full bg-slate-900 border border-slate-800 rounded-xl p-8 shadow-2xl text-center space-y-6">
                <div className="flex justify-center">
                    <div className="w-12 h-12 rounded-full bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
                        {status === "loading" && <Loader2 className="w-6 h-6 text-indigo-400 animate-spin" />}
                        {status === "success" && <CheckCircle2 className="w-6 h-6 text-emerald-400" />}
                        {status === "error" && <AlertCircle className="w-6 h-6 text-rose-400" />}
                    </div>
                </div>

                <div className="space-y-2">
                    <h2 className="text-xl font-bold text-white tracking-tight">
                        {status === "loading" && "Authenticating with Google..."}
                        {status === "success" && "Authentication Successful!"}
                        {status === "error" && "Google Login Failed"}
                    </h2>
                    <p className="text-xs font-mono text-slate-400">
                        {status === "loading" && "Securing token and initializing your personal knowledge workspace..."}
                        {status === "success" && "Redirecting to your dashboard..."}
                        {status === "error" && errorMessage}
                    </p>
                </div>

                {status === "error" && (
                    <div className="pt-2">
                        <Link href="/login">
                            <Button className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-mono text-xs">
                                Return to Login
                            </Button>
                        </Link>
                    </div>
                )}
            </div>
        </div>
    );
}

export default function GoogleAuthCallbackPage() {
    return (
        <Suspense fallback={
            <div className="min-h-screen bg-slate-950 flex items-center justify-center">
                <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
            </div>
        }>
            <GoogleAuthCallbackContent />
        </Suspense>
    );
}
