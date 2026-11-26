"use client";

import Link from "next/link";
import { ArrowDown, ArrowUpRight, FileText, Image, Mic2, Globe2, Link2 } from "lucide-react";
import { Button } from "@/components/ui/button";

const NAV_LINKS = [
    { label: "How it works", href: "#how-it-works" },
    { label: "What you can save", href: "#features" },
];

const sourceTypes = [
    { label: "PDFs & notes", icon: FileText },
    { label: "Images", icon: Image },
    { label: "Audio", icon: Mic2 },
    { label: "Web & video captions", icon: Globe2 },
];

export function Hero() {
    return (
        <section className="relative isolate min-h-screen overflow-hidden bg-[#f8fafc] px-4 pb-16 pt-24 text-[#0f172a] sm:px-8 sm:pt-28 lg:px-12">
            <div className="pointer-events-none absolute -right-36 -top-40 -z-10 h-[34rem] w-[34rem] rounded-full bg-[#dbeafe]/60 blur-3xl" />
            <div className="pointer-events-none absolute -bottom-48 -left-40 -z-10 h-[30rem] w-[30rem] rounded-full bg-[#dbeafe]/70 blur-3xl" />

            <nav className="absolute inset-x-0 top-0 z-20 flex items-center justify-between border-b border-[#cbd5e1]/70 bg-[#f8fafc]/85 px-4 py-4 backdrop-blur-md sm:px-8 lg:px-12">
                <Link href="/" className="flex items-center gap-3" aria-label="Threadwell home">
                    <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#0b1d36] text-[#f8fafc]">
                        <Link2 size={18} />
                    </span>
                    <span className="font-display text-xl font-semibold tracking-tight sm:text-2xl">Threadwell</span>
                </Link>

                <ul className="hidden items-center gap-8 md:flex">
                    {NAV_LINKS.map((link) => (
                        <li key={link.href}>
                            <a href={link.href} className="text-sm text-[#334155] transition-colors hover:text-[#0f172a]">
                                {link.label}
                            </a>
                        </li>
                    ))}
                </ul>

                <div className="flex items-center gap-2 sm:gap-4">
                    <Link href="/login" className="hidden text-sm text-[#334155] hover:text-[#0f172a] sm:inline">
                        Sign in
                    </Link>
                    <Link href="/register">
                        <Button size="sm" className="rounded-full bg-[#1d4ed8] px-4 text-white hover:bg-[#1d4ed8]">
                            Start free <ArrowUpRight size={15} className="ml-1" />
                        </Button>
                    </Link>
                </div>
            </nav>

            <div className="mx-auto grid min-h-[calc(100vh-7rem)] max-w-7xl items-center gap-12 py-12 lg:grid-cols-[1.05fr,0.95fr] lg:gap-16">
                <div className="max-w-2xl">
                    <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-[#cbd5e1] bg-white/70 px-3 py-1.5 text-xs font-medium text-[#334155]">
                        <span className="h-2 w-2 rounded-full bg-[#1d4ed8]" />
                        A calmer home for everything you learn
                    </div>

                    <h1 className="font-display text-5xl leading-[0.98] tracking-tight sm:text-6xl md:text-7xl lg:text-[5.5rem]">
                        Keep what matters.
                        <span className="mt-2 block italic text-[#1d4ed8]">Find the thread.</span>
                    </h1>

                    <p className="mt-7 max-w-xl text-base leading-7 text-[#334155] sm:text-lg sm:leading-8">
                        Bring your notes, documents, images, audio, and links together. Ask across what you save—and follow every useful answer back to its source.
                    </p>

                    <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                        <Link href="/register">
                            <Button size="lg" className="h-12 w-full rounded-full bg-[#0b1d36] px-6 text-white hover:bg-[#163b72] sm:w-auto">
                                Make your space <ArrowUpRight size={17} className="ml-2" />
                            </Button>
                        </Link>
                        <a href="#how-it-works">
                            <Button size="lg" variant="outline" className="h-12 w-full rounded-full border-[#cbd5e1] bg-white/50 px-6 text-[#0f172a] hover:bg-white sm:w-auto">
                                See how it works <ArrowDown size={16} className="ml-2" />
                            </Button>
                        </a>
                    </div>

                    <div className="mt-9 flex flex-wrap gap-x-5 gap-y-3">
                        {sourceTypes.map(({ label, icon: Icon }) => (
                            <span key={label} className="inline-flex items-center gap-2 text-xs text-[#475569]">
                                <Icon size={14} className="text-[#1d4ed8]" />
                                {label}
                            </span>
                        ))}
                    </div>
                </div>

                <div className="relative mx-auto w-full max-w-xl">
                    <div className="absolute -left-5 top-12 hidden h-24 w-24 rounded-full border border-[#1d4ed8]/20 sm:block" />
                    <div className="absolute -bottom-5 right-7 hidden h-20 w-20 rounded-full bg-[#dbeafe]/80 sm:block" />
                    <div className="relative rounded-[2rem] border border-[#e2e8f0] bg-white/75 p-3 shadow-[0_28px_80px_-36px_rgba(15,23,42,0.16)] backdrop-blur">
                        <div className="rounded-[1.5rem] border border-[#e2e8f0] bg-[#ffffff] p-5 sm:p-7">
                            <div className="flex items-center justify-between border-b border-[#e2e8f0] pb-4">
                                <div>
                                    <p className="text-xs font-medium uppercase tracking-[0.14em] text-[#64748b]">A sample space</p>
                                    <h2 className="mt-1 font-display text-2xl">Weekend ideas</h2>
                                </div>
                                <span className="rounded-full bg-[#eff6ff] px-3 py-1 text-xs text-[#1d4ed8]">3 sources</span>
                            </div>

                            <div className="mt-5 flex flex-wrap gap-2">
                                {["My note", "Trail guide", "Recipe"].map((source) => (
                                    <span key={source} className="rounded-full border border-[#e2e8f0] bg-white px-3 py-1.5 text-xs text-[#334155]">
                                        {source}
                                    </span>
                                ))}
                            </div>

                            <div className="mt-6 ml-auto max-w-[90%] rounded-2xl rounded-br-md bg-[#f1f5f9] px-4 py-3 text-sm text-[#1e293b]">
                                What should I remember before the trip?
                            </div>

                            <div className="mt-3 max-w-[96%] rounded-2xl rounded-bl-md border border-[#bfdbfe] bg-[#eff6ff] p-4">
                                <p className="text-sm leading-6 text-[#1e293b]">
                                    Pack water and a light layer. The trail guide mentions a refill point halfway through, and your note says the morning can be cool.
                                </p>
                                <div className="mt-4 flex flex-wrap gap-2 border-t border-[#dbeafe] pt-3">
                                    <span className="rounded-full bg-white px-2.5 py-1 text-[11px] text-[#1e40af]">Trail guide</span>
                                    <span className="rounded-full bg-white px-2.5 py-1 text-[11px] text-[#1e40af]">My note</span>
                                </div>
                            </div>

                            <p className="mt-5 text-center text-xs text-[#64748b]">
                                A small example of separate sources, brought into context.
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </section>
    );
}
