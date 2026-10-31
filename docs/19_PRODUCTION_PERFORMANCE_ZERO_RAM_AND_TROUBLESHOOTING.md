# 19. Production Performance, Zero-RAM & Troubleshooting

## 1. Zero-RAM Architecture on Render 512MB RAM Instances

```
[Linux Kernel cgroups: 512MB Memory Limit]
                  │
                  ▼
1. Decoupled Binary Storage:
   - PDFs stream directly to Cloudinary CDN
   - Zero raw file bytes stored in local filesystem or Python heap
                  │
                  ▼
2. Vector Store Offloading:
   - Dense embeddings stored externally in Qdrant Cloud
   - FastEmbed runs quantized ONNX models (< 60MB RAM)
                  │
                  ▼
3. Kernel Memory Compaction:
   - Python's gc.collect() reclaims garbage-collected references
   - ctypes.CDLL('libc.so.6').malloc_trim(0) forces glibc to return
     unmapped heap memory back to the Linux OS
                  │
                  ▼
[Result: Steady-State Baseline < 180MB RAM | Peak Load < 340MB RAM]
```

---

## 2. Six Production War Stories & Architectural Resolutions

1. **The 512MB RAM Container Crash (OOM SIGKILL)**:
   - *Cause*: Concurrent PDF parsing and in-memory embeddings exceeded 650MB.
   - *Fix*: Decoupled binary storage to Cloudinary and invoked `malloc_trim(0)` after every batch.
2. **Google OAuth 502 Bad Gateway during Cold Starts**:
   - *Cause*: Dormant backend instances took 25–40s to spin up, timing out OAuth redirects.
   - *Fix*: Added background health warmup pings on login/register pages (`navigator.sendBeacon` / Axios).
3. **429 Rate Limit Avalanche on Groq LPU**:
   - *Cause*: Burst multi-chunk queries exhausted the 30 RPM limit on a single key.
   - *Fix*: Implemented a 10-key dynamic round-robin pool with 20s cooldown key-hopping.
4. **Autonomous Crawler Network Deadlock**:
   - *Cause*: Slow-loading institutional PDFs hung worker threads for 45s.
   - *Fix*: Enforced an 8.0s download timeout, 15MB file cap, and 25-page extraction limit.
5. **Wildcard Route Masking Bug in FastAPI**:
   - *Cause*: Parameterized route `@router.post("/{doc_id}")` shadowed static `@router.post("/general")`.
   - *Fix*: Reordered routes so `/general` is evaluated first.
6. **The 800-Token Response Truncation**:
   - *Cause*: Hardcoded `max_tokens=800` caused long tabular answers to stop mid-sentence.
   - *Fix*: Elevated token budgets to 3500 tokens across all inference handlers.
