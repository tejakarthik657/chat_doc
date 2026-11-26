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
    return "Your profile couldn’t be updated. Please try again.";
}

export function ProfileSection() {
    const [user, setUser] = useState<UserOut | null>(null);
    const [name, setName] = useState("");
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");

    useEffect(() => {
        let mounted = true;
        authService.getMe()
            .then((userData) => {
                if (!mounted) return;
                setUser(userData);
                setName(userData.name || userData.email.split("@")[0]);
            })
            .catch(() => {
                if (mounted) setError("Your profile couldn’t be loaded. Refresh and try again.");
            })
            .finally(() => {
                if (mounted) setLoading(false);
            });
        return () => {
            mounted = false;
        };
    }, []);

    const saveProfile = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        const normalizedName = name.trim();
        if (!normalizedName) {
            setError("Display name cannot be empty.");
            return;
        }

        setSaving(true);
        setError("");
        setSuccess("");
        try {
            const updatedUser = await authService.updateProfile(normalizedName);
            setUser(updatedUser);
            setName(updatedUser.name || normalizedName);
            setSuccess("Your display name has been saved.");
        } catch (requestError) {
            setError(getErrorMessage(requestError));
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="space-y-6">
            <div>
                <h2 className="mb-1 font-display text-2xl">Profile</h2>
                <p className="text-sm text-text-secondary">Manage the name and account details shown in Threadwell.</p>
            </div>

            {loading ? (
                <p className="text-sm text-text-muted" role="status">Loading your profile…</p>
            ) : user ? (
                <Card>
                    <CardContent className="space-y-6 p-5 sm:p-6">
                        <form onSubmit={saveProfile} className="space-y-5">
                            <div className="flex items-center gap-4">
                                <div
                                    className="flex h-14 w-14 items-center justify-center rounded-full bg-accent/10 font-display text-xl text-accent"
                                    aria-hidden="true"
                                >
                                    {(name.trim() || user.email).slice(0, 1).toUpperCase()}
                                </div>
                                <div>
                                    <p className="font-medium text-text-primary">{name || "Your profile"}</p>
                                    <p className="text-xs text-text-muted">Your initials are used as your profile mark.</p>
                                </div>
                            </div>

                            <div className="grid gap-5 sm:grid-cols-2">
                                <div className="space-y-2">
                                    <label htmlFor="profile-name" className="text-xs font-mono uppercase text-text-secondary">
                                        Display name
                                    </label>
                                    <Input
                                        id="profile-name"
                                        value={name}
                                        onChange={(event) => setName(event.target.value)}
                                        maxLength={80}
                                        autoComplete="name"
                                        required
                                    />
                                </div>
                                <div className="space-y-2">
                                    <label htmlFor="profile-email" className="text-xs font-mono uppercase text-text-secondary">
                                        Email
                                    </label>
                                    <Input id="profile-email" value={user.email} disabled />
                                    <p className="text-xs text-text-muted">Email changes aren’t available in account settings.</p>
                                </div>
                            </div>

                            {error && <p className="text-sm text-red-500" role="alert">{error}</p>}
                            {success && <p className="text-sm text-accent-success" role="status">{success}</p>}

                            <div className="flex justify-end border-t border-border pt-4">
                                <Button type="submit" variant="primary" isLoading={saving} disabled={saving || !name.trim()}>
                                    Save profile
                                </Button>
                            </div>
                        </form>
                    </CardContent>
                </Card>
            ) : (
                <p className="text-sm text-red-500" role="alert">{error}</p>
            )}
        </div>
    );
}
