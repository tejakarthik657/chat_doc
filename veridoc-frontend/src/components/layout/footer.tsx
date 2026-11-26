import Link from "next/link";
import { ArrowUpRight, Sparkles } from "lucide-react";

export function Footer() {
    return (
        <footer className="border-t border-[#E2DED5] bg-[#F0EDE5]">
            <div className="mx-auto flex max-w-7xl flex-col gap-8 px-4 py-10 sm:px-6 md:flex-row md:items-center md:justify-between md:py-12">
                <div className="max-w-md">
                    <Link href="/" className="inline-flex items-center gap-2 font-display text-2xl text-[#252F2A]">
                        <Sparkles size={19} className="text-[#B65D43]" />
                        Threadwell
                    </Link>
                    <p className="mt-3 text-sm leading-6 text-[#59645D]">
                        A thoughtful place to keep what you learn—and find the connections when you need them.
                    </p>
                </div>

                <nav aria-label="Footer navigation" className="flex flex-wrap gap-x-6 gap-y-3 text-sm text-[#59645D]">
                    <Link href="#how-it-works" className="transition-colors hover:text-[#252F2A]">How it works</Link>
                    <Link href="#features" className="transition-colors hover:text-[#252F2A]">Features</Link>
                    <Link href="/login" className="transition-colors hover:text-[#252F2A]">Sign in</Link>
                    <Link href="/register" className="inline-flex items-center gap-1 text-[#A34F38] hover:text-[#7E3D2B]">
                        Make your space <ArrowUpRight size={14} />
                    </Link>
                </nav>
            </div>
            <div className="border-t border-[#E2DED5] px-4 py-4 text-center text-xs text-[#7B847D] sm:px-6">
                Keep what matters. Find the thread.
            </div>
        </footer>
    );
}
