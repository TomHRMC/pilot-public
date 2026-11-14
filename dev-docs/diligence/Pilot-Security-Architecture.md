# Security Architecture — as designed

*How security was architected into this build. It's here as capability evidence — proof I design for the parts that are expensive to get wrong — not as a readiness claim: the technical design follows the **SOC 2 security criteria — built to the controls, not audited, with no organizational controls behind it.** Nothing here is certified, and the system never carried real user data. Implemented vs. aspirational is marked throughout.*

---

## Identity & access
- **AWS Cognito** user pools as the identity provider — password storage, reset, and lockout are Cognito's responsibility, not the app's (`core/auth.py`, `services/cognito_mfa_client.py`, `services/tenant_signup.py`).
- **MFA** — a genuine Amplify v6 enrollment flow (TOTP / SMS / email + recovery codes), wired on both web and mobile.
- **JWT with JWKS signature validation + key rotation** at the API boundary — the RS256 signature and expiry are verified against the Cognito user pool's JWKS (rotating keys). The `iss`, `aud` and `token_use` claims are not yet checked; adding them is a small hardening change (the audience check is already flagged in `core/auth.py`; see Honest gaps).
- **Server-authoritative RBAC** — permission checks as dependency injection (`Depends(require_permission("quotes.create"))`), **~350 permission-check call-sites**, across roles (owner / office-staff / accountant / technician). Authorization is enforced in code, not implied by a role column.
- **Tenant isolation** — `tenant_id` on every tenant-owned table; tenant-scoped routes filter on the caller's `tenant_id` (a final code read found a few route groups that don't — Known Limitations #27; public, webhook and signed-link routes are scoped by their own token or signature); with a dedicated isolation suite and cross-tenant IDOR tests. *Note (implemented, with a known hardening item):* isolation is **application/query-layer, Postgres RLS not enabled** — see `Pilot-Known-Limitations.md`.

## Secrets management
- **No secrets in source.** `.env` and `.env.*` are git-ignored (only `.env.example` is tracked); runtime secrets are supplied via environment / AWS at deploy time.
- **CI uses GitHub OIDC role assumption — no long-lived cloud keys stored** in the pipeline.
- The public snapshot was **scrubbed clean-room** (placeholders for every credential, fresh git history) — see `PROVENANCE.md`.
- **AI-agent database access was read-only.** `.roo/mcp.json` gives the agents query access to the dev database and to the (customer-free) AWS database through a dedicated `mcp_readonly` role. The AWS connection runs over an SSH tunnel through the bastion to a localhost port; `sslmode=no-verify` applies to that localhost tunnel endpoint. Auto-approval (`alwaysAllow: ["query"]`) covers read-only queries, so through MCP the agents could only read. Outside MCP, the agents ran tests and seed scripts against the local dev database like any developer process.

## Data protection
- **In transit:** TLS 1.2+ (TLS 1.3 preferred) at the ALB; HTTPS throughout.
- **At rest:** RDS storage encryption + KMS and Multi-AZ are declared in Terraform (`infrastructure/terraform/`); S3 for object storage.
- **Field/token encryption:** a Fernet-based encryption utility (`core/encryption.py`) for sensitive stored values (e.g. integration tokens).

## Application hardening
- **Rate limiting** (`core/rate_limit.py`, applied to three public route groups; not global — Known Limitations #28) and **idempotency middleware** (`core/idempotency.py`) on the request path.
- **Bot/abuse protection:** Cloudflare **Turnstile**, server-side verified (`core/turnstile.py`).
- **Input validation** via pervasive Pydantic models; **RFC-7807** structured error responses designed not to leak internals (one known exception: invalid-token errors echo the JWT library's message — see `Pilot-Known-Limitations.md`).
- **Audit event logging** wired across the route layer.
- **Dual-endpoint `/test` pattern** — secured routes are paired with an env-gated test twin (about 330 twins for about 340 secured operations at hibernation), disabled by default **and** only honored in dev/qa, double-blocked in production.

## Supply chain
- **Backend dependencies 100% pinned** (`==`); frontend versions locked via `pnpm-lock.yaml`.
- **Trivy secret scanning** of the source tree in the production CI workflow (`.github/workflows/deploy-production.yml`); container builds to ECR. Container-image and dependency-vulnerability scanning are **not yet** in the pipeline.

## Threat model (summary)
| Risk | Primary mitigation |
|---|---|
| Cross-tenant data access | `tenant_id` scoping on tenant-scoped routes (exceptions: Known Limitations #27) + isolation suite + IDOR tests (RLS is the additive next layer) |
| Auth bypass / token forgery | Cognito + JWKS signature validation + rotation; server-authoritative RBAC |
| Secret exposure | No secrets in code; OIDC CI; clean-room scrub of the public snapshot |
| Injection | ORM-parameterized queries + Pydantic validation at the boundary |
| Abuse / credential stuffing | Cognito lockout; Turnstile and rate limits on some public routes (Known Limitations #28) |
| Tampered audit trail | Audit tables in place; tamper-evident hash-chain designed (not yet populated — disclosed) |

## Honest gaps (disclosed, not hidden)
- **Not audited.** Built to the SOC 2 security criteria; no auditor, no attestation, no organizational controls.
- **No human penetration test, and no image or dependency-vulnerability scanning in CI** — Trivy secret scanning only.
- **JWT `iss`, `aud` and `token_use` claims not checked** — the RS256 signature and expiry are verified against this user pool's JWKS; adding the claim checks is a small hardening change (the audience check is already flagged in `core/auth.py`).
- **No SIEM or application-level runtime monitoring** — GuardDuty and Security Hub are defined in Terraform; nothing aggregates or pages beyond alarm email.
- **Redis is not encrypted (at rest or in transit) and has no auth token** — a single-node ElastiCache cluster in a private subnet (Known Limitations #24).
- **Admin access is an IP-allowlisted SSH bastion in a public subnet** — SSM Session Manager is the planned replacement.
- **DB-enforced RLS not enabled** — isolation is tested at the app layer; RLS is an additive migration.
- **Authorization and hardening gaps from a final code read** — a few route groups don't check the caller's tenant, and several defaults fail open when a secret is missing (Known Limitations #27 and #28). Small, testable fixes that belong before any release.

## What this demonstrates
The security-relevant decisions that are expensive to retrofit — a real IdP with MFA, signature-validated tokens, enforced RBAC, tenant scoping, encryption in transit and at rest for the database and storage (Redis excepted, Known Limitations #24), no secrets in code, pinned dependencies and a secret-scanned supply chain — were made correctly from the start (with the route-level gaps listed in Known Limitations #27 and #28). Knowing precisely which controls are *built* versus *attested* is the distinction a security-literate architect is expected to draw, and it's drawn here on purpose.
