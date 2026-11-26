"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2, AlertCircle, CheckCircle2, Link2 } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast-provider";

function GoogleAuthCallbackContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const showToast = useToast();
    const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
    const [errorMessage, setErrorMessage] = useState("");

    useEffect(() => {
        let redirectTimer: ReturnType<typeof setTimeout> | null = null;
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
                const isNewUser = searchParams.get("welcome") === "1";
                showToast({
                    title: isNewUser ? "Welcome to Threadwell" : "Welcome back",
                    message: isNewUser ? "Your space is ready. Let’s make it yours." : "Your space is ready when you are.",
                    tone: "success",
                });
                redirectTimer = setTimeout(() => router.replace("/dashboard"), 800);
            } catch {
                setStatus("error");
                setErrorMessage("Failed to store local session. Please try logging in again.");
            }
        } else {
            setStatus("error");
            setErrorMessage("No authentication token received from Google callback.");
        }
        return () => {
            if (redirectTimer) clearTimeout(redirectTimer);
        };
    }, [searchParams, router, showToast]);

    return (
        <main className="flex min-h-screen items-center justify-center bg-background px-5 py-12">
            <section className="w-full max-w-md rounded-2xl border border-border bg-surface p-8 text-center shadow-[0_24px_72px_-36px_rgba(15,23,42,0.32)] sm:p-10">
                <div className="mb-8 flex justify-center">
                    <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-blue-200 bg-blue-50 text-blue-800">
                        {status === "loading" && <Loader2 className="h-6 w-6 animate-spin text-blue-700" />}
                        {status === "success" && <CheckCircle2 className="h-6 w-6 text-blue-700" />}
                        {status === "error" && <AlertCircle className="h-6 w-6 text-blue-900" />}
                    </div>
                </div>

                <div className="space-y-3">
                    <div className="flex items-center justify-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-blue-700">
                        <Link2 size={14} />
                        Threadwell
                    </div>
                    <h1 className="font-display text-3xl tracking-tight text-text-primary">
                        {status === "loading" && "Opening your space"}
                        {status === "success" && "You’re signed in"}
                        {status === "error" && "We couldn’t sign you in"}
                    </h1>
                    <p className="text-sm leading-6 text-text-secondary">
                        {status === "loading" && "Checking your sign-in and preparing your saved sources."}
                        {status === "success" && "Taking you to your saved sources."}
                        {status === "error" && errorMessage}
                    </p>
                </div>

                {status === "error" && (
                    <div className="mt-7">
                        <Link href="/login">
                            <Button className="w-full">
                                Return to sign in
                            </Button>
                        </Link>
                    </div>
                )}
            </section>
        </main>
    );
}

export default function GoogleAuthCallbackPage() {
    return (
        <Suspense fallback={
            <div className="flex min-h-screen items-center justify-center bg-background">
                <div className="flex items-center gap-3 rounded-xl border border-border bg-surface px-5 py-4 text-sm text-text-secondary shadow-sm">
                    <Loader2 className="h-5 w-5 animate-spin text-blue-700" />
                    Preparing your sign-in…
                </div>
            </div>
        }>
            <GoogleAuthCallbackContent />
        </Suspense>
    );
}
