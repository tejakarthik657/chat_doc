# 14. Cloud Multi-Provider Failover

## 1. Multi-Tier Failover Hierarchy

```mermaid
graph TD
    REQ["Incoming User Query"] --> TIER1["Tier 1: Qwen 2.5 27B (qwen/qwen3.8-27b on Groq)"]
    TIER1 -->|Error / Timeout| TIER2["Tier 2: GPT OSS 120B (openai/gpt-oss-120b on Groq)"]
    TIER2 -->|Error / Timeout| TIER3["Tier 3: GPT OSS 20B (openai/gpt-oss-20b on Groq)"]
    TIER3 -->|Pool Exhausted / Down| TIER4["Tier 4: Google Gemini 1.5 Flash (Direct REST API)"]
    TIER4 -->|Quota Exceeded| TIER5["Tier 5: OpenRouter Free Tier (Meta-Llama)"]
    TIER5 -->|Offline / Fatal| TIER6["Tier 6: Grounded Abstention Message"]
```

---

## 2. Zero-RAM REST Fallback Implementation (`core/llm_cloud_fallback.py`)

- **Google Gemini 1.5 Flash**: Invoked directly via lightweight `httpx.Client(timeout=20.0)` calls to `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent`.
- **Zero Local Footprint**: Requires no local GPU, PyTorch, or CTransformers model weights, preserving the strict 512MB RAM container ceiling.
