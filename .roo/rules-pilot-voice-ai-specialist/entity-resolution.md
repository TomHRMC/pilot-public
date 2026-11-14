# 🧠 Entity Resolution: Multi-Turn Context Rules

> **Design-time agent rule** — written to steer the AI agents during the build and published as last used. Where it differs from the as-built system, [`PROVENANCE.md`](../../PROVENANCE.md) and [`dev-docs/diligence/`](../../dev-docs/diligence/README.md) are correct.

## 1. Context Persistence Mandate

The Voice AI Specialist must ensure the system maintains state across multiple voice exchanges. Every incoming voice command must be evaluated against the active session to resolve ambiguous references.

## 2. Session Management Logic

Before processing an intent, the system must perform the following lookup in the PostgreSQL database:

* **Active Session Check**: Always query the `conversation_sessions` table for an existing `session_id` before creating a new record.
* **TTL (Time-to-Live)**: Sessions should be considered "active" if the last message was within 15 minutes.
* **Context Retrieval**: Fetch the last 5 messages from `conversation_messages` to build the context string for the Ollama Llama 3.1 8B model.

## 3. Pronoun & Reference Resolution

The Specialist must configure the Ollama prompt to resolve specific electrical and business entities:

| Pronoun/Reference | Resolution Logic | Example Flow |
| --- | --- | --- |
| **"Him" / "Her"** | Map to the `customer_id` identified in the current or previous turn. | "Create quote for Tom" → "Send it to **him**". |
| **"It" / "The Quote"** | Map to the `quote_id` currently being modified in the session. | "Add a panel" → "What is the total for **it**?". |
| **"That" / "The Item"** | Map to the last mentioned `line_item` or `material_id`. | "Add 100ft of wire" → "Actually, make **that** 200ft". |
| **"The Job"** | Map to the active `job_id` if the user is currently navigating the jobs dashboard. | "Open the Johnson job" → "Add an expense to **it**". |

## 4. Vector-Based Similarity Search

For complex resolutions where direct mapping fails, use `pgvector` to find relevant context:

* **HNSW Indexing**: Perform a cosine similarity search (`<=>`) on the `conversation_messages` embeddings to find the most relevant prior entities.
* **Limit**: Restrict similarity searches to the `session_id` to prevent cross-tenant or cross-session "hallucinations".

## 5. Voice Personalization Consistency

* **Voice ID Persistence**: Once a user selects a voice (e.g., "Alloy" or "Onyx"), that `voice_id` must be stored in `user_preferences` and used for all multi-turn confirmations to maintain a consistent persona.
* **Confirmation Loop**: Every resolution of a pronoun must be verbally confirmed (e.g., "Got it, sending the quote to **Tom Johnson**") to ensure accuracy.
