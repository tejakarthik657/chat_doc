"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function SecuritySection() {
    return (
        <div className="space-y-6">
            <div>
                <h2 className="font-display text-2xl mb-1">Security</h2>
                <p className="text-text-secondary text-sm">Update your password and security settings.</p>
            </div>

            <div className="space-y-4 max-w-md">
                <div className="space-y-2">
                    <label className="text-xs font-mono text-text-secondary uppercase">Current Password</label>
                    <Input type="password" />
                </div>
                <div className="space-y-2">
                    <label className="text-xs font-mono text-text-secondary uppercase">New Password</label>
                    <Input type="password" />
                </div>
                <div className="space-y-2">
                    <label className="text-xs font-mono text-text-secondary uppercase">Confirm Password</label>
                    <Input type="password" />
                </div>
            </div>

            <div className="flex justify-end pt-4 border-t border-border mt-8">
                <Button variant="primary">Update Password</Button>
            </div>

            <div className="mt-12 pt-8 border-t border-red-500/20">
                <h3 className="font-display text-lg text-red-500 mb-2">Danger Zone</h3>
                <p className="text-sm text-text-muted mb-4">Permanently delete your account and all data.</p>
                <Button variant="danger">Delete Account</Button>
            </div>
        </div>
    );
}
