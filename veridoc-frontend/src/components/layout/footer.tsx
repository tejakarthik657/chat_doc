import { Github, Twitter } from "lucide-react";
import Link from "next/link";

export function Footer() {
    return (
        <footer className="border-t border-border bg-background pt-16 pb-8">
            <div className="max-w-7xl mx-auto px-6 grid grid-cols-1 md:grid-cols-4 gap-12 mb-16">
                <div className="col-span-1 md:col-span-2 space-y-4">
                    <Link href="/" className="font-display text-2xl text-text-primary">DevFrames Synapse</Link>
                    <p className="text-text-muted text-sm max-w-xs">
                        DevFrames Synapse is a high-fidelity document intelligence platform for corporate, academic, and governance entities.
                    </p>
                </div>

                <div className="space-y-4">
                    <h4 className="font-mono text-sm text-text-primary uppercase tracking-wider">Product</h4>
                    <ul className="space-y-2 text-sm text-text-secondary">
                        <li><Link href="#" className="hover:text-accent transition-colors">Features</Link></li>
                        <li><Link href="#" className="hover:text-accent transition-colors">Pricing</Link></li>
                        <li><Link href="#" className="hover:text-accent transition-colors">API</Link></li>
                    </ul>
                </div>

                <div className="space-y-4">
                    <h4 className="font-mono text-sm text-text-primary uppercase tracking-wider">Company</h4>
                    <ul className="space-y-2 text-sm text-text-secondary">
                        <li><Link href="#" className="hover:text-accent transition-colors">About</Link></li>
                        <li><Link href="#" className="hover:text-accent transition-colors">Blog</Link></li>
                        <li><Link href="#" className="hover:text-accent transition-colors">Privacy</Link></li>
                    </ul>
                </div>
            </div>

            <div className="max-w-7xl mx-auto px-6 pt-8 border-t border-border flex flex-col md:flex-row justify-between items-center gap-4">
                <div className="font-mono text-xs text-text-muted">
                    RETRIEVAL &gt; GENERATION // SOURCES OR SILENCE
                </div>

                <div className="flex gap-4">
                    <Link href="#" className="text-text-muted hover:text-text-primary transition-colors"><Github size={16} /></Link>
                    <Link href="#" className="text-text-muted hover:text-text-primary transition-colors"><Twitter size={16} /></Link>
                </div>
            </div>
        </footer>
    );
}
