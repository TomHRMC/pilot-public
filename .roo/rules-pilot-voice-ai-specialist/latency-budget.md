# ⏱️ Latency Budget: Voice AI Performance Rules

> **Design-time agent rule** — written to steer the AI agents during the build and published as last used. Where it differs from the as-built system, [`PROVENANCE.md`](../../PROVENANCE.md) and [`dev-docs/diligence/`](../../dev-docs/diligence/README.md) are correct.

## 1. The North Star Constraint

The end-to-end (E2E) latency for any voice command—from the moment the user stops speaking to the moment they hear a confirmation—must be **< 2 seconds (p95)**.

## 2. Technical Component Breakdown

To achieve the 2-second goal, the following sub-budgets are strictly enforced for the **Whisper + Ollama** pipeline:

| Stage | Process | Target Latency | Max Allowed (p95) |
| --- | --- | --- | --- |
| **Ingress** | Audio Blob Upload (Mobile/Web → FastAPI) | 100ms | 250ms |
| **STT** | Whisper Large-v3 Transcription (GPU) | 300ms | 800ms |
| **NLU** | Ollama Llama 3.1 8B Intent Parsing | 150ms | 400ms |
| **Logic** | Database/API Action Execution | 100ms | 300ms |
| **TTS** | Confirmation Generation (Native Browser/Mobile) | 50ms | 150ms |
| **TOTAL** | **Full Transaction Loop** | **~700ms** | **1900ms** |

## 3. Implementation Guardrails

* **Local Processing**: Always utilize the **g4dn.xlarge** GPU instance; never send customer audio or job data to public cloud AI APIs.
* **Model Preloading**: Both **Whisper Large-v3** and **Ollama Llama 3.1 8B** must be preloaded into GPU memory at service startup to eliminate "cold start" latency.
* **Concurrent Handling**: The FastAPI layer must handle audio processing asynchronously to prevent blocking the event loop during heavy I/O tasks.
* **Optimization**: If latency spikes, the Specialist must first investigate **pgvector HNSW index** performance or model quantization (e.g., 4-bit vs 8-bit) before suggesting hardware upgrades.

## 4. Monitoring & SLOs

* **Tracing**: Every voice transaction must include subsegment instrumentation via **AWS X-Ray** to identify which specific stage (STT, NLU, or Logic) is exceeding its budget.
* **Alerting**: Trigger a **P2 - High (Slack)** alert if Voice AI latency exceeds **2000ms** consistently across 5% of requests.
