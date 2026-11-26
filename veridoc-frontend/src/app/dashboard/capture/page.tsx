import { CaptureAnything } from "@/components/capture/capture-anything";

export default function CapturePage() {
    return (
        <div className="mx-auto flex min-h-[calc(100vh-60px)] max-w-5xl flex-col justify-center p-4 sm:p-6 md:p-8">
            <div className="mb-6 sm:mb-8">
                <p className="mb-2 font-mono text-xs uppercase tracking-[0.18em] text-accent">Your searchable space starts here</p>
                <h1 className="font-display text-2xl sm:text-3xl md:text-4xl">Capture Anything</h1>
                <p className="mt-2 max-w-2xl text-sm text-text-secondary">
                    No setup or sorting first. Add a source once, then ask questions across what you’ve saved.
                </p>
            </div>
            <CaptureAnything />
        </div>
    );
}
