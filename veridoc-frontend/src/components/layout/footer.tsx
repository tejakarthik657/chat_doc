import { Github, Twitter } from "lucide-react";
import Link from "next/link";

export function Footer() {
    return (
        <footer className="border-t border-border bg-background pt-12 sm:pt-16 pb-8">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-8 sm:gap-12 mb-12 sm:mb-16">
                <div className="col-span-1 sm:col-span-2 space-y-4">
                    <Link href="/" className="font-display text-2xl text-text-primary">DevFrames Synapse</Link>
                    <p className="text-text-muted text-sm max-w-xs leading-relaxed">
                        DevFrames Synapse is a high-fidelity document intelligence platform for corporate, academic, and governance entities.
                    </p>
                </div>

                <div className="space-y-4">
                    <h4 className="font-mono text-sm text-text-primary uppercase tracking-wider">Product</h4>
                    <ul className="space-y-2 text-sm text-text-secondary">
                        <li><Link href="#" className="hover:text-accent transition-colors py-1 inline-block">Features</Link></li>
                        <li><Link href="#" className="hover:text-accent transition-colors py-1 inline-block">Pricing</Link></li>
                        <li><Link href="#" className="hover:text-accent transition-colors py-1 inline-block">API</Link></li>
                    </ul>
                </div>

                <div className="space-y-4">
                    <h4 className="font-mono text-sm text-text-primary uppercase tracking-wider">Company</h4>
                    <ul className="space-y-2 text-sm text-text-secondary">
                        <li><Link href="#" className="hover:text-accent transition-colors py-1 inline-block">About</Link></li>
                        <li><Link href="#" className="hover:text-accent transition-colors py-1 inline-block">Blog</Link></li>
                        <li><Link href="#" className="hover:text-accent transition-colors py-1 inline-block">Privacy</Link></li>
                    </ul>
                </div>
            </div>

            <div className="max-w-7xl mx-auto px-4 sm:px-6 pt-6 sm:pt-8 border-t border-border flex flex-col sm:flex-row justify-between items-center gap-4 text-center sm:text-left">
                <div className="font-mono text-[11px] sm:text-xs text-text-muted">
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
