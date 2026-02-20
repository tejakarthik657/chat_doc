import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { User } from "lucide-react";
import { authService } from "@/services/auth.service";

export function ProfileSection() {
    const [user, setUser] = useState<{ email: string } | null>(null);

    useEffect(() => {
        const loadUser = async () => {
            try {
                const userData = await authService.getMe();
                setUser(userData);
            } catch (error) {
                console.error("Failed to load profile:", error);
            }
        };
        loadUser();
    }, []);

    return (
        <div className="space-y-6">
            <div>
                <h2 className="font-display text-2xl mb-1">Profile</h2>
                <p className="text-text-secondary text-sm">Manage your account information.</p>
            </div>

            <div className="flex items-center gap-6 mb-8">
                <div className="h-24 w-24 bg-surface-high rounded-lg flex items-center justify-center text-text-muted border border-border">
                    <User size={40} />
                </div>
                <div>
                    <Button variant="ghost" size="sm" className="mb-2">Change Photo</Button>
                    <p className="text-xs text-text-muted">JPG or PNG, max 2MB.</p>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                    <label className="text-xs font-mono text-text-secondary uppercase">Display Name</label>
                    <Input defaultValue={user?.email.split('@')[0] || "User"} />
                </div>
                <div className="space-y-2">
                    <label className="text-xs font-mono text-text-secondary uppercase">Email</label>
                    <Input defaultValue={user?.email || "loading..."} disabled className="opacity-70" />
                </div>
            </div>

            <div className="flex justify-end pt-4">
                <Button variant="primary">Save Changes</Button>
            </div>
        </div>
    );
}
