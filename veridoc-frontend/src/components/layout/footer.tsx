import Link from "next/link";
import { ArrowUpRight, Link2 } from "lucide-react";

export function Footer() {
    return (
        <footer className="border-t border-[#e2e8f0] bg-[#f1f5f9]">
            <div className="mx-auto flex max-w-7xl flex-col gap-8 px-4 py-10 sm:px-6 md:flex-row md:items-center md:justify-between md:py-12">
                <div className="max-w-md">
                    <Link href="/" className="inline-flex items-center gap-2 font-display text-2xl text-[#0f172a]">
                        <Link2 size={19} className="text-[#1d4ed8]" />
                        Threadwell
                    </Link>
                    <p className="mt-3 text-sm leading-6 text-[#334155]">
                        A thoughtful place to keep what you learn—and find the connections when you need them.
                    </p>
                </div>

                <nav aria-label="Footer navigation" className="flex flex-wrap gap-x-6 gap-y-3 text-sm text-[#334155]">
                    <Link href="#how-it-works" className="transition-colors hover:text-[#0f172a]">How it works</Link>
                    <Link href="#features" className="transition-colors hover:text-[#0f172a]">Features</Link>
                    <Link href="/login" className="transition-colors hover:text-[#0f172a]">Sign in</Link>
                    <Link href="/register" className="inline-flex items-center gap-1 text-[#1e40af] hover:text-[#1e40af]">
                        Make your space <ArrowUpRight size={14} />
                    </Link>
                </nav>
            </div>
            <div className="border-t border-[#e2e8f0] px-4 py-4 text-center text-xs text-[#64748b] sm:px-6">
                Keep what matters. Find the thread.
            </div>
        </footer>
    );
}
