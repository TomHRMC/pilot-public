> **📦 ARCHIVED 2026-08-20 — CONTENT RESCUED & SUPERSEDED.** The durable design content (the 11-function NEC calculation surface, the standard function return-shape contract, the NEC answer format + AHJ-verification language) was folded into `dev-docs/architecture-design/mvp-arch.md` **§6.8.1** on 2026-08-20 before archiving. The "Recommended solution design" model/serving notes below (Parakeet / Qwen / GPT-OSS / vLLM) were exploratory and are **not** the shipped stack — the product runs Whisper Large-v3 + local Llama via Ollama on the `g4dn.xlarge` GPU per `mvp-arch.md` §6 and `.roo/rules-pilot-architect/infrastructure-constraints.md`. Archived per Tom's decision. **Frozen reference — do not update.**

---

# NEC Calculation Functions

calculate_conductor_ampacity()
apply_temperature_correction()
apply_adjustment_factors()
calculate_voltage_drop()
size_equipment_grounding_conductor()
size_grounding_electrode_conductor()
calculate_box_fill()
calculate_raceway_fill()
calculate_motor_branch_circuit()
calculate_transformer_overcurrent_protection()
calculate_service_or_feeder_load()

## Function Returns

Each function returns:
{
  "inputs": {},
  "formula": "",
  "intermediate_steps": [],
  "result": {},
  "source_references": [],
  "assumptions": [],
  "warnings": []
}

## Answer Formats

NEC questions answer format:

Applicable edition and jurisdiction
Question classification
Relevant NEC provisions
Known inputs
Assumptions
Calculation
Result
Compliance interpretation
Exceptions or alternatives
Items requiring AHJ confirmation
Sources

### Answer Example

Based on the 2023 NEC and the supplied conditions, the calculated minimum conductor size is X. This conclusion depends on 75°C terminations, copper conductors, no local amendment, and the stated number of current-carrying conductors. Verify the adopted edition and interpretation with the local AHJ.

## Recommended solution design:

Speech:
  NVIDIA Parakeet TDT 0.6B v2

General help chat:
  Qwen 3 14B or 30B-A3B

Technical reasoning:
  GPT-OSS 20B

Visual manuals:
  Qwen3-VL 8B

Serving:
  Ollama initially
  vLLM when concurrency becomes important

RAG:
  PostgreSQL + pgvector or Qdrant
  BM25/OpenSearch
  reranker
  document metadata database

Calculations:
  Python service with validated electrical formulas