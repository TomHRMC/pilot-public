# 🧪 SLO Verification: Performance & Reliability Testing

> **Design-time agent rule** — written to steer the AI agents during the build and published as last used. Where it differs from the as-built system, [`PROVENANCE.md`](../../PROVENANCE.md) and [`dev-docs/diligence/`](../../dev-docs/diligence/README.md) are correct.

## 1. Automated Performance Gates

The Test Engineer must implement automated benchmarks that fail the build if the following **p95 latency** thresholds are exceeded:

* **Standard API Latency**: Must be **< 500ms** for 95% of requests under a simulated load of 10 concurrent users.
* **Voice AI E2E Latency**: Must be **< 2.0 seconds** for 95% of test samples (Audio → Transcription → Intent → Action).
* **Database Query Performance**: Any query exceeding **1.0 second** must be flagged in the logs as a slow query and investigated for missing indexes.

## 2. QuickBooks Sync Integrity Tests

To meet the **99% sync success rate** and **zero duplicate data** mandates, the following integration tests are required:

* **Idempotency Verification**: Submit the same `POST` request three times with the same `X-Idempotency-Key` and verify that only one record exists in the database/QuickBooks.
* **Bi-Directional Conflict Simulation**: Modify a customer record in both Pilot for Trades and QuickBooks simultaneously, then verify that the system correctly triggers the **Conflict Resolution UI**.
* **Token Rotation Recovery**: Simulate an expired OAuth token during a background sync task and verify that the system successfully refreshes the token via **Secrets Manager** and retries the task.

## 3. Voice Recognition Accuracy (Trade-Specific)

The Test Engineer must maintain a "Trade Lexicon Test Set" of 100+ audio samples to verify voice recognition targets:

* **Accuracy Target**: Must achieve **> 95% accuracy** on electrical terminology (e.g., "THHN," "200 amp service," "voltage drop").
* **Noise Resiliency**: Verify that intent classification still succeeds in environments with **70dB of simulated construction background noise**.
* **Multi-Turn Resolution**: Test sequences like "Create quote for Tom" followed by "Add it to his job" to ensure the `conversation_sessions` context is correctly utilized.

## 4. Availability & Security Gates

* **SLO Uptime**: Verify that the infrastructure (Multi-AZ RDS, ECS Fargate) can withstand a single AZ failure without dropping below the **99.9% availability** target.
* **Auth Verification**: Ensure all `/v1/test` unauthenticated endpoints are strictly disabled when `TEST_ENDPOINT_ENABLED` is `false`.
* **GDPR Compliance**: Verify the "Right to Deletion" by executing a user deletion and confirming all PII is scrubbed from the `Companies`, `Users`, and `Audit Logs` tables.

## 5. Deployment Verification (Blue-Green)

* **Rollback Speed**: Execute a failed deployment in a staging environment and verify that the ALB traffic shift allows a **full rollback to the "Blue" version in < 2 minutes**.
* **Health Check Reliability**: Ensure the ECS health checks correctly identify a "zombie" container (running process but failing API calls) and prevent it from receiving production traffic.
