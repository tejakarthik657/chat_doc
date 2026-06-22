import { X, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";

export function SourcePanel({ page, onClose }: { page: number, onClose: () => void }) {
    return (
        <div className="flex flex-col h-full bg-surface border-l border-border shadow-xl">
            <div className="p-4 border-b border-border flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <span className="font-mono text-xs text-text-muted">SOURCE</span>
                    <span className="bg-amber-500/10 text-amber-700 border border-amber-500/20 px-1.5 py-0.5 rounded text-xs font-mono">[PAGE {page}]</span>
                </div>
                <Button variant="ghost" size="icon" onClick={onClose} className="h-6 w-6">
                    <X size={14} />
                </Button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 font-mono text-xs leading-relaxed text-text-secondary">
                <div className="mb-4 p-2 bg-blue-500/10 border border-blue-500/20 rounded text-blue-400 text-[10px] uppercase">
                    Retrieved via Semantic Search (0.92)
                </div>

                <p className="mb-4">
                    ...The <span className="bg-amber-500/20 text-text-primary px-1">recommended dosage for adults is 50mg twice daily</span>. This standard was established following the phase III clinical trials (N=2400) which demonstrated efficacy...
                </p>
                <p>
                    Patients with renal impairment (GFR &lt; 30) should receive a reduced dose of 25mg daily. Monitoring of creatinine levels is required every 2 weeks...
                </p>

                <div className="my-6 border-t border-border" />

                <div className="text-text-muted opacity-50">
                    [Rest of page content...]
                </div>
            </div>

            <div className="p-4 border-t border-border">
                <Button variant="ghost" className="w-full text-xs h-8">
                    <ExternalLink size={12} className="mr-2" /> View Full Page
                </Button>
            </div>
        </div>
    );
}
