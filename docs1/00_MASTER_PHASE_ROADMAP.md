# Master Phase Roadmap: VeriDoc Synapse Engineering Architecture

Welcome to **`docs1/`** — the comprehensive, end-to-end full-stack engineering curriculum for **VeriDoc Synapse (ActionMesh Platform)**.

While the `docs/` folder contains specific architectural chapters (deep dives into FastEmbed, RRF, PyMuPDF, etc.), **`docs1/` maps the entire project across the 10 standard phases of modern software engineering**, covering all **80 sub-disciplines** and adapting them directly to this codebase.

---

## The 10 Engineering Phases & Document Index

| Phase | Master Document | Scope & Sub-Disciplines Covered |
| :--- | :--- | :--- |
| **Phase 1** | **[`01_PRODUCT_AND_REQUIREMENTS_ENGINEERING.md`](./01_PRODUCT_AND_REQUIREMENTS_ENGINEERING.md)** | Product Vision, Target Users, \$32B Veeva Market, Functional/Non-Functional Requirements, Bounded Contexts, User Stories. |
| **Phase 2** | **[`02_ARCHITECTURE_AND_SYSTEM_DESIGN.md`](./02_ARCHITECTURE_AND_SYSTEM_DESIGN.md)** | Hexagonal Ports & Adapters, High-Level/Low-Level Design, Class Diagrams, Distributed Modes, Topography. |
| **Phase 3** | **[`03_UI_UX_AND_FRONTEND_ENGINEERING.md`](./03_UI_UX_AND_FRONTEND_ENGINEERING.md)** | Next.js 16 App Router, React 19 RSC/Client split, Token Buffer (65% DOM reduction), Accessibility. |
| **Phase 4** | **[`04_BACKEND_ENGINEERING.md`](./04_BACKEND_ENGINEERING.md)** | FastAPI Layered Core, Dependency Injection, Business Rules, REST/JSON-RPC 2.0, SSE Streaming, Async Tasks. |
| **Phase 5** | **[`05_DATABASE_AND_DATA_ENGINEERING.md`](./05_DATABASE_AND_DATA_ENGINEERING.md)** | Polyglot Storage (MongoDB + Qdrant + SQLite EHR), Motor connection pooling, Indexes, ACID vs Eventual consistency. |
| **Phase 6** | **[`06_AI_AND_MACHINE_LEARNING_ENGINEERING.md`](./06_AI_AND_MACHINE_LEARNING_ENGINEERING.md)** | RAG v2, FastEmbed ONNX (< 60MB RAM), RRF ($k=60$), Cross-Encoder, CRAG Grader, Inbound/Outbound MCP, 3500 Tokens. |
| **Phase 7** | **[`07_SECURITY_ENGINEERING.md`](./07_SECURITY_ENGINEERING.md)** | OWASP Top 10, AST SQL Injection Guardrails, SecurityHeaders, BCrypt, Stateless JWT, HIPAA & 21 CFR Part 11. |
| **Phase 8** | **[`08_TESTING_AND_QUALITY_ENGINEERING.md`](./08_TESTING_AND_QUALITY_ENGINEERING.md)** | Unit Testing, Integration Harness (`test_phase3_mcp.py`, `test_phase4_5_6.py`), E2E Journeys, Hallucination Benchmarks. |
| **Phase 9** | **[`09_DEVOPS_AND_INFRASTRUCTURE_ENGINEERING.md`](./09_DEVOPS_AND_INFRASTRUCTURE_ENGINEERING.md)** | Git Branching, Minimal Dockerfile (< 250MB), CI/CD Automation, Vercel Edge + Render, Blue-Green Deployments. |
| **Phase 10** | **[`10_MONITORING_RELIABILITY_AND_OPERATIONS.md`](./10_MONITORING_RELIABILITY_AND_OPERATIONS.md)** | `/health` Uptime, Structured JSON Logging, Correlation IDs, RED Metrics, 20s Circuit Breakers, `malloc_trim(0)`. |
