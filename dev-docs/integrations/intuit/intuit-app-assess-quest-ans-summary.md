# Intuit App Assessment Questionnaire — Answers & Audit Summary

> **Snapshot note — dated partner submission.** These answers were submitted to Intuit on 2026-07-06 for the production QuickBooks Online API key and are published as submitted. Where they differ from the later, checked documents in [`dev-docs/diligence/`](../../diligence/README.md), the diligence documents are correct. Three known corrections: **ElastiCache was not encrypted at rest** (a single-node cluster; see [Known Limitations](../../diligence/Pilot-Known-Limitations.md) #24) — the "Encryption at rest" row below overstates it; the platform later ran **12** CloudWatch alarms, not 9; and the WebSocket answer below is incomplete — the backend has no WebSocket endpoint, but the frontend includes a WebSocket voice-stream client (`frontend/packages/ui/src/voice/web/useVoiceStream.ts`). "Security team" and "lead architect" mean the author (working with his AI architect agent), supported by automated AWS tooling; this was a solo build with no independent human review.

**App**: Pilot for Trades  
**Company**: Example Holdings, LLC (DBA Pilot for Trades)  
**Submitted**: 2026-07-06  
**Purpose**: Production QuickBooks Online API key application — compliance assessment questionnaire

---

## App Details

| Question | Answer |
|---|---|
| Connect URL (Launch URL) | `https://app.pilotfortrades.com/settings/integrations` |
| Disconnect URL | `https://app.pilotfortrades.com/settings/integrations` |
| Redirect URI (OAuth callback) | `https://api.pilotfortrades.com/api/v1/integrations/callback` |
| Terms of Service | `https://www.pilotfortrades.com/legal/terms` |
| Privacy Policy | `https://www.pilotfortrades.com/legal/privacy` |
| Categories (4 selected) | Invoicing & payments, Project management, Expenses, Customer management |
| Regulated industries | None of the above |
| Generative AI? | Yes |
| AI description | Voice command interface (locally-hosted Llama on private AWS EC2 GPU) classifies field technician voice commands into structured job/scheduling actions; contextual help system (RAG with local Llama + pgvector). Neither feature processes QuickBooks data. OpenAI `text-embedding-3-small` used solely for help documentation corpus embeddings — no customer data, financial data, or QB data sent to OpenAI. |
| QB data used for AI training? | No |
| App built from scratch? | Yes — built from scratch, wrote all code that interacts with Intuit APIs |
| Platforms | Web/SaaS, Web/Browser, Mobile |
| Intuit data interaction | Reads data from Intuit product(s); Writes data to Intuit product(s) |
| Private or public app? | Publicly available |
| Anticipated QBO customers (year 1) | 50–100 |
| QBO user type allowed | Only QuickBooks Online company admin |
| Other platform integrations | Stripe, Telnyx, SendGrid, Google Maps, AWS Cognito, Cloudflare Turnstile |

---

## Authorization & Authentication

| Question | Answer | Technical Basis |
|---|---|---|
| 1. Tested connecting/disconnecting/reconnecting with sandbox? | Yes | Tested during development with QBO sandbox environment |
| 2. How often does app refresh access tokens? | More than once a day | Celery Beat runs scheduled refresh; endpoint proactively refreshes when token is within 5 min of expiry. QBO access tokens expire every 60 min. |
| 3. Does app retry failed auth requests? | No | Errors are surfaced; user prompted to reconnect. No automatic retry-with-backoff for OAuth/auth failures. |
| 4. If auth error, do you ask customers to reconnect? | Yes | When `connection_status` becomes `expired` or `disconnected`, Settings → Integrations page shows disconnected state and prompts owner to reconnect via `/connect` endpoint |
| 5. Used Intuit discovery document for OAuth endpoints? | No | Endpoints hardcoded in `backend/core/config.py`: auth URL `https://appcenter.intuit.com/connect/oauth2`, token URL `https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer` |
| 6a. Handles expired access tokens? | Yes | Token `expires_at` checked; auto-refresh by Celery Beat before expiry |
| 6b. Handles expired refresh tokens? | Yes | Error caught → credential marked `disconnected` → reconnect prompt shown |
| 6c. Handles invalid grant errors? | Yes | Error caught → credential marked `disconnected` → reconnect prompt shown |
| 6d. Handles CSRF errors? | Yes | UUID4 state token generated on `/connect`, validated in `/callback`, 10-minute expiry enforced |
| 7. App relies on OAuth playground or offline tools? | No | Full OAuth 2.0 authorization code flow implemented in backend. No external tooling. |

---

## API Usage

| Question | Answer | Technical Basis |
|---|---|---|
| 1. API categories used | Accounting API only | Syncs customers, invoices, payments, items via QBO Accounting API. Payments API (Intuit Payments) and Payroll API not used. |
| 2. How often does app call APIs per customer? | Daily | Celery background sync; triggered by user actions (invoice creation, QB sync). |
| 3. QBO version compatibility | Simple Start, Essentials, Plus, Advanced | Uses standard Accounting API entities available on all tiers |
| 4. Handles users gaining/losing version features? | Yes | Only core entities used — no tier-specific features. Sync continues regardless of QBO tier. |
| 5. Special features used | Sales tax — US | `external_tax_agency_id` mapped on tax rate versions for US QBO companies. No multicurrency, no non-US tax. |
| 6. Uses webhooks? | Yes | Live webhook handler at `POST /api/v1/webhooks/quickbooks` with Intuit HMAC signature verification (`verify_quickbooks_signature`). Receives customer create/update/delete events. |
| 7. Uses CDC (Change Data Capture)? | No | Uses webhooks for change detection. No CDC polling implemented. |

---

## Error Handling

| Question | Answer | Technical Basis |
|---|---|---|
| 1. Tested API errors including syntax/validation errors? | Yes | Unit tests cover webhook error cases: invalid JSON, invalid signature, tenant not found, API error responses. |
| 2. Captures `intuit_tid` from response headers? | No | Pilot captures its own `X-Request-ID` for internal tracing but does not capture the Intuit-specific `intuit_tid` header. **Improvement added to P2 backlog (Batch QB-H1).** |
| 3. Stores error info in logs for troubleshooting? | Yes | All ECS services log to CloudWatch (structured Python `logging` throughout). CloudWatch log groups retained and accessible. |
| 4. In-app support contact? | Yes | In-app RAG help chat with escalation path to `support@pilotfortrades.com`. Support email surfaced in app help surfaces and footer. |

---

## Security

| Question | Answer | Technical Basis |
|---|---|---|
| 1. Company ever had a security breach requiring notification? | No | Pre-revenue MVP. No security breach has ever occurred. |
| 2. Security team regularly assesses vulnerabilities? | Yes | AWS Security Hub (CIS + AWS Foundational benchmarks) and GuardDuty provide continuous automated security assessment. Architecture security review conducted by lead architect during implementation. |
| 3. Client ID and secret stored securely (not hardcoded)? | Yes | QB credentials stored in AWS Secrets Manager (`pilot/prod/quickbooks`), KMS-encrypted, injected into ECS at runtime via IAM role. Never in source code. Never in browser. |
| 4. App uses multi-factor authentication? | Yes | AWS Cognito with optional MFA (email, SMS, TOTP) configurable per tenant at application layer. |
| 5. App uses CAPTCHA for authentication? | Yes | Cloudflare Turnstile on all public marketing forms (waitlist, contact, careers, newsletter). |
| 6. App uses WebSocket? | No | All real-time features use SSE (Server-Sent Events): dispatch board, notifications, QB conflict updates. WebSocket not implemented. Zero WebSocket references in codebase. |
| 7. Intuit data used by or shown to anyone other than original customer? | No, all Intuit customer data processed by the app is only used for the benefit of the original customer | QB data is tenant-scoped. A tenant's QB data is only accessible to users of that tenant. Never shared cross-tenant or with third parties. |

---

## Infrastructure Security Reference

| Control | Implementation | Status |
|---|---|---|
| TLS | AWS ALB enforces HTTPS on all endpoints; TLS 1.2+ minimum | ✅ Active |
| Encryption at rest | RDS, ElastiCache, S3, EBS — all KMS customer-managed key (`alias/pilot-production`); annual rotation | ✅ Active |
| Secrets management | AWS Secrets Manager, KMS-encrypted, 11 secrets | ✅ Active |
| No long-lived credentials | ECS task roles (IAM), GitHub Actions OIDC — no static access keys | ✅ Active |
| OAuth token encryption | Fernet (AES-128-CBC + HMAC) via `core.encryption` before storage in DB | ✅ Active |
| Audit logging | CloudWatch logs for all ECS services; 9 CloudWatch alarms; GuardDuty; Security Hub | ✅ Active |
| Redis in-transit encryption | Disabled — Redis on private VPC subnet only, no internet exposure | ⚠️ Phase 2 |
| Formal penetration test | Not conducted — pre-revenue; AWS Security Hub active | ⚠️ Pre-revenue |

---

## Known Gaps Logged for Remediation

| Item | Priority | Batch |
|---|---|---|
| Capture `intuit_tid` header from QBO API responses and log to CloudWatch | P2 | QB-H1 |
| Redis in-transit encryption (`rediss://` URLs) | P2 | Infrastructure Phase 2 |
