"use client";

import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { authService } from "@/services/auth.service";
import type { UserOut } from "@/services/auth.service";

function getErrorMessage(error: unknown): string {
    if (error && typeof error === "object" && "response" in error) {
        const response = (error as { response?: { data?: { detail?: unknown } } }).response;
        if (typeof response?.data?.detail === "string") return response.data.detail;
    }
    return "Your password couldn’t be changed. Please try again.";
}

export function SecuritySection() {
    const [user, setUser] = useState<UserOut | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [currentPassword, setCurrentPassword] = useState("");
    const [newPassword, setNewPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");

    useEffect(() => {
        let mounted = true;
        authService.getMe()
            .then((userData) => {
                if (mounted) setUser(userData);
            })
            .catch(() => {
                if (mounted) setError("Security settings couldn’t be loaded. Refresh and try again.");
            })
            .finally(() => {
                if (mounted) setLoading(false);
            });
        return () => {
            mounted = false;
        };
    }, []);

    const updatePassword = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        setError("");
        setSuccess("");
        if (newPassword !== confirmPassword) {
            setError("The new password and confirmation don’t match.");
            return;
        }
        if (newPassword.length < 8) {
            setError("Your new password must be at least 8 characters.");
            return;
        }

        setSaving(true);
        try {
            await authService.changePassword(currentPassword, newPassword);
            setCurrentPassword("");
            setNewPassword("");
            setConfirmPassword("");
            setSuccess("Your password has been updated.");
        } catch (requestError) {
            setError(getErrorMessage(requestError));
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="space-y-6">
            <div>
                <h2 className="mb-1 font-display text-2xl">Security</h2>
                <p className="text-sm text-text-secondary">Change the password used to sign in to your account.</p>
            </div>

            {loading ? (
                <p className="text-sm text-text-muted" role="status">Loading your security settings…</p>
            ) : user?.auth_provider === "password" ? (
                <Card>
                    <CardContent className="p-5 sm:p-6">
                        <form onSubmit={updatePassword} className="max-w-lg space-y-5">
                            <div className="space-y-2">
                                <label htmlFor="current-password" className="text-xs font-mono uppercase text-text-secondary">
                                    Current password
                                </label>
                                <Input
                                    id="current-password"
                                    type="password"
                                    value={currentPassword}
                                    onChange={(event) => setCurrentPassword(event.target.value)}
                                    autoComplete="current-password"
                                    required
                                />
                            </div>
                            <div className="space-y-2">
                                <label htmlFor="new-password" className="text-xs font-mono uppercase text-text-secondary">
                                    New password
                                </label>
                                <Input
                                    id="new-password"
                                    type="password"
                                    value={newPassword}
                                    onChange={(event) => setNewPassword(event.target.value)}
                                    autoComplete="new-password"
                                    minLength={8}
                                    maxLength={64}
                                    required
                                />
                                <p className="text-xs text-text-muted">Use at least 8 characters.</p>
                            </div>
                            <div className="space-y-2">
                                <label htmlFor="confirm-password" className="text-xs font-mono uppercase text-text-secondary">
                                    Confirm new password
                                </label>
                                <Input
                                    id="confirm-password"
                                    type="password"
                                    value={confirmPassword}
                                    onChange={(event) => setConfirmPassword(event.target.value)}
                                    autoComplete="new-password"
                                    minLength={8}
                                    maxLength={64}
                                    required
                                />
                            </div>

                            {error && <p className="text-sm text-blue-500" role="alert">{error}</p>}
                            {success && <p className="text-sm text-accent-success" role="status">{success}</p>}

                            <div className="flex justify-end border-t border-border pt-4">
                                <Button type="submit" variant="primary" isLoading={saving} disabled={saving}>
                                    Update password
                                </Button>
                            </div>
                        </form>
                    </CardContent>
                </Card>
            ) : user ? (
                <Card>
                    <CardContent className="p-5 text-sm text-text-secondary sm:p-6">
                        This account uses single sign-on. Manage your password with your identity provider.
                    </CardContent>
                </Card>
            ) : (
                <p className="text-sm text-blue-500" role="alert">{error}</p>
            )}
        </div>
    );
}
