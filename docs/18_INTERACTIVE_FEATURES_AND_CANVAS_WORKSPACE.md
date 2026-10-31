# 18. Interactive Features & Canvas Workspace

## 1. Canvas Workspace Architecture (`components/canvas/CanvasWorkspace.tsx`)

- **Split Screen Layout**: Renders side-by-side with chat and document previews.
- **Editable Markdown Canvas**: Allows live document editing, notes aggregation, and one-click export to `.md` or `.pdf`.
- **Integrated Python Runner**: Sends code blocks directly to `/api/features/execute-code` for execution in an isolated sandbox.

---

## 2. Advanced AI Intelligence Modals (`components/features/`)

```mermaid
graph TD
    UI["Dashboard Interface"] --> F1["Truth Lattice Modal (TruthLatticeModal.tsx)"]
    UI --> F2["Socratic Viva Modal (SocraticVivaModal.tsx)"]
    UI --> F3["What-If Simulator (WhatIfSimulatorModal.tsx)"]
    UI --> F4["Living Code Sandbox (LivingCodeSandbox.tsx)"]

    F1 -->|Audit| DUAL_MODEL["Adversarial Dual-Model Hallucination Check"]
    F2 -->|Examine| SOCRATIC["Multi-Turn Adaptive Student Examination"]
    F3 -->|Simulate| COUNTERFACT["Counterfactual Parameter Stress Testing"]
    F4 -->|Execute| SANDBOX["Sandboxed Python Execution (/execute-code)"]
```
