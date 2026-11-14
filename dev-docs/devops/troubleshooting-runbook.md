# Troubleshooting Runbook — Pilot for Trades

**Version**: 1.0
**Date**: 2026-08-27
**Author**: Pilot Python Engineer (TEST-UPLIFT-1A)
**Purpose**: Symptom → likely cause → diagnostic steps → fix. Bounded to the 10 sections below (design §G Q8). Append a row per incident; cross-link INT-H1 dev-ref docs as they land.

**Maintenance note**: This is a living document. When a new incident class is diagnosed, append a row to the relevant section table. Cross-link any INT-H1 dev-ref doc that lands for the same symptom. Do not add new top-level sections without Architect sign-off (design §G Q8 bounds the scope).

**Related docs**:
- [`aws-ops-runbook.md`](aws-ops-runbook.md) — §19.6 (deploy checklist), §19.7 (image hygiene), §16 (rollback)
- [`aws-env-mgmt-ops-plan.md`](aws-env-mgmt-ops-plan.md) — §3 (env-var inventory), §9 (testing matrix)
- [`aws-cognito-prod-setup.md`](aws-cognito-prod-setup.md) — Cognito auth/MFA

---

## 1. Deploy Drift

| Symptom | Likely Cause | Diagnostic | Fix |
|---|---|---|---|
| New code not live after deploy | Task def revision not updated; `:latest` tag points at old image | `aws ecs describe-tasks` — compare running task's image digest vs ECR image digest; check `revision` vs latest task-def revision | Update service to latest task-def revision; `aws ecs update-service --force-new-deployment` |
| Service running old env vars | Task def env vars not updated after TF apply | `aws ecs describe-task-definition` — compare env vars vs `infrastructure/terraform/modules/compute/main.tf` | Apply TF; update service to new task-def revision |
| `:latest` rollback corollary | `:latest` tag overwritten by a different build | Check ECR image push history; compare digests | Pin to specific image digest; see §16 rollback procedures |
| Local image tag stale vs ECR | Local `pilot-celery_worker:latest` points at old May 19 build; ECR has the clean Aug 27 rebuild | `docker images` — compare local image ID/created date vs ECR image ID | `docker pull` from ECR or rebuild locally; verify with `./admin-tools/check_image_hygiene.sh` (TEST-UPLIFT-1A, resolved 2026-08-27) |

**Cross-ref**: [`aws-ops-runbook.md`](aws-ops-runbook.md) §19.6 (deploy canary — revision vs image-digest parity).

---

## 2. Cognito Auth / MFA

| Symptom | Likely Cause | Diagnostic | Fix |
|---|---|---|---|
| Login fails silently | Cognito User Pool misconfigured; JWKS URL wrong | Check `COGNITO_REGION` + `COGNITO_USER_POOL_ID` in task def; verify JWKS endpoint reachable from ECS | Correct env vars; redeploy |
| MFA lockout | User exceeded `lockout_threshold` (5 attempts) | Check Cognito logs; `password_policy.lockout_threshold` | Wait `lockout_duration_minutes` (30 min) or admin-reset in Cognito console |
| SMS MFA not delivered | Telnyx 10DLC not provisioned; SMS carrier in mock mode | Check `SMS_CARRIER` + `TELNYX_10DLC_MOCK` in task def (must be `telnyx` / `false` in prod) | Provision 10DLC campaign; set env vars explicitly |
| MFA enrollment fails in dev | `MFA_COGNITO_MOCK=true` (code default) but dev pool has MFA Disabled | Check `MFA_COGNITO_MOCK` env var | Set `MFA_COGNITO_MOCK=false` only against prod pool; dev pool needs MFA Enabled first |

**Cross-ref**: [`aws-cognito-prod-setup.md`](aws-cognito-prod-setup.md).

---

## 3. Stripe (Subscriptions + Connect)

| Symptom | Likely Cause | Diagnostic | Fix |
|---|---|---|---|
| Webhook events not received | Stripe webhook endpoint URL wrong or secret mismatch | Check Stripe dashboard webhook endpoint URL + signing secret vs `STRIPE_WEBHOOK_SECRET` in Secrets Manager | Update webhook endpoint; rotate secret; redeploy |
| Test/live key mismatch | `STRIPE_SECRET_KEY` points at test mode but `STRIPE_PUBLISHABLE_KEY` at live | Compare key prefixes (`sk_test_` vs `sk_live_`) in Secrets Manager | Correct the key in Secrets Manager; redeploy |
| Seed price-ID convergence failure | `_env_profiles.py` price-ID registry mismatch with Stripe | Check `stripe_ids.test.json` / `stripe_ids.live.json` vs `subscription_tier.stripe_price_id_*` columns | Re-run `seed_prod_db.py --stripe-mode <mode>` to converge |
| Stripe Connect onboarding fails | `STRIPE_CONNECT_*` env vars missing | Check task def for Connect-related env vars | Add env vars; redeploy |
| Subscription status not updating | Webhook handler not processing `invoice.paid` / `customer.subscription.updated` | Check `stripe_webhook_event_processed` table for dedup; check worker logs for handler errors | Fix handler; replay webhook event from Stripe dashboard |

**Cross-ref**: [`_env_profiles.py`](../../backend/migrations/scripts/_env_profiles.py) price-ID registry; `pilot-operations.md` _(private)_ (tier→plan→ppfv cascade).

---

## 4. QuickBooks Sync

| Symptom | Likely Cause | Diagnostic | Fix |
|---|---|---|---|
| Token refresh fails | QuickBooks OAuth token expired; refresh token invalid | Check `integration_credential` table for `quickbooks` provider; verify `expires_at` | Re-authorize via OAuth flow (`/api/v1/integrations/quickbooks/callback`) |
| Sync conflict queue stuck | `integration_sync_conflict` rows in `pending` state | Query `integration_sync_conflict` WHERE `status = 'pending'`; check `auto_expire_qb_conflicts` Beat task | Review conflicts; resolve or let auto-expire (3:30 AM UTC daily) |
| `intuit_tid` missing | QB realm ID not stored | Check `integration_credential.realm_id` | Re-authorize OAuth flow to capture realm ID |
| Customer sync not running | `sync_all_tenants_customers` Beat task failing | Check worker logs for `sync_all_tenants_customers` errors | Fix sync service; verify QB connection |

**Cross-ref**: [`aws-ops-runbook.md`](aws-ops-runbook.md) §Database Operations.

---

## 5. Telnyx + SMS Delivery

| Symptom | Likely Cause | Diagnostic | Fix |
|---|---|---|---|
| 10DLC status stuck | Campaign not approved; `tenant_phone_number.status = 'provisioning_failed'` | Check Telnyx dashboard for campaign status; query `tenant_phone_number` table | Re-provision campaign; check `messaging_provisioning` task logs |
| TFN verification pending | Toll-free number not verified | Check Telnyx dashboard for TFN verification status | Submit verification; wait for carrier approval |
| SMS quota exceeded | `sms_quota_period` usage > cap | Query `sms_quota_period` for current period; check `monitor_sms_quota_thresholds` alerts | Upgrade tier or wait for period rollover (00:05 UTC daily) |
| Inbound SMS not processed | Telnyx webhook URL wrong or signature verification failing | Check Telnyx webhook endpoint URL; verify `telnyx-signature-ed25519` header | Update webhook URL; verify public key configuration |
| SMS sent in mock mode | `SMS_CARRIER=mock` or `TELNYX_10DLC_MOCK=true` in prod | Check task def env vars | Set `SMS_CARRIER=telnyx` + `TELNYX_10DLC_MOCK=false` explicitly; redeploy |

**Cross-ref**: [`aws-env-mgmt-ops-plan.md`](aws-env-mgmt-ops-plan.md) §3 (env-var inventory).

---

## 6. SSE (Server-Sent Events)

| Symptom | Likely Cause | Diagnostic | Fix |
|---|---|---|---|
| SSE connection rejected | Missing or invalid JWT in `?token=` query param | Check client-side SSE URL includes `?token=<JWT>` | Ensure frontend passes valid JWT in SSE connection URL |
| SSE connection limit hit | Thread-per-connection model; too many concurrent connections | Check ECS task CPU/memory utilization; count active SSE connections | Scale out (more tasks); reduce polling frequency |
| SSE events not received | Event source disconnected; heartbeat not firing | Check browser EventSource connection state; verify server-side heartbeat interval | Reconnect client; verify `sse_heartbeat_interval` setting |

---

## 7. GPU / Voice Pipeline

| Symptom | Likely Cause | Diagnostic | Fix |
|---|---|---|---|
| Whisper/Ollama unreachable from ECS | GPU instance not running; security group blocking | Check EC2 GPU instance status; verify `sg-gpu` allows ECS task SG inbound | Start GPU instance; verify security group rules |
| Voice transcription p95 > 2.5s | Whisper model overloaded; GPU instance undersized | Check CloudWatch `voice.transcription.p95` metric; GPU utilization | Scale GPU instance; check `scaling-logic.md` §4 for p95 trigger |
| Voice intent classification fails | Ollama model not loaded; `parse_intent` returns empty | Check Ollama container logs; verify model name in config | Restart Ollama; verify `OLLAMA_MODEL` env var |
| Voice session title not generated | `voice_session_title` Celery task not registered | Check worker logs for `generate_session_title` task; verify `tasks.voice_session_title` in `celery_app.conf.imports` | Add to imports list (see §9 Celery below) |

**Cross-ref**: `scaling-logic.md` §4 (p95 latency trigger = 2.5s).

---

## 8. Maps Cache

| Symptom | Likely Cause | Diagnostic | Fix |
|---|---|---|---|
| Maps costs spiking | `MAP_CACHE_ENABLED=false` in prod (code default OFF) | Check task def env vars for `MAP_CACHE_ENABLED`; verify it's `true` | Set `MAP_CACHE_ENABLED=true` + `MAP_CACHE_TTL_SECONDS=86400` in TF; apply at next deploy window |
| Drive-time results not cached | Redis unavailable; cache key mismatch | Check `map_service.cache HIT/MISS` logs; verify Redis connectivity from ECS | Verify `REDIS_URL` in task def; check Redis endpoint reachability |
| Cache hit ratio low | TTL too short; coordinate precision too high | Check `get_cache_hit_ratio()` metric; verify `MAP_CACHE_TTL_SECONDS` | Increase TTL; verify 4-decimal coordinate rounding in `_make_cache_key` |

**Cross-ref**: TEST-UPLIFT-1A Task 4 (TF diff prepared 2026-08-27 — Tom/DevOps applies); [`aws-env-mgmt-ops-plan.md`](aws-env-mgmt-ops-plan.md) §3.

---

## 9. Celery

| Symptom | Likely Cause | Diagnostic | Fix |
|---|---|---|---|
| Task never runs | Module not in `celery_app.conf.imports` (worker only imports listed modules) | Run `python -m pytest tests/domains/platform_infrastructure/test_celery_registration.py` | Add module to `imports` list in [`celery_app.py`](../../backend/core/celery_app.py) |
| Beat task not firing | `beat_schedule` entry missing or schedule wrong | Check `celery_app.conf.beat_schedule` for the task name; verify `crontab` schedule | Add/fix beat_schedule entry; restart beat container |
| Event-driven task queued but not executed | Module in imports but task name mismatch | Check worker logs for `NotRegistered` error; verify `@celery_app.task` name matches beat_schedule `task` field | Fix task name; redeploy worker |
| Task runs twice | Beat + event-driven both firing | Check if task is in both `beat_schedule` AND called via `.delay()` | Remove from beat_schedule (event-driven tasks don't need Beat) |

**Cross-ref**: TEST-UPLIFT-1A Task 1 (registration guard — `tasks.tenant_site_emails` was missing, fixed 2026-08-27).

---

## 10. Seed Env Guards

| Symptom | Likely Cause | Diagnostic | Fix |
|---|---|---|---|
| Seed script refuses to run | `assert_target_compatible` guard triggered — DB host not in `allowed_db_host_patterns` | Check `DATABASE_URL` host vs `_env_profiles.py` allowed patterns for the env | Use the correct host spelling (e.g. `localhost:5433` or `127.0.0.1:5433` for prod tunnel) |
| Seed script targets wrong DB | `forbidden_db_host_patterns` guard not catching the dev DB | Check if the forbidden pattern matches the URL | Verify `forbidden_db_host_patterns` includes `:5432/pilot_dev` for prod profile |
| `127.0.0.1:5433` rejected for prod | Old guard only accepted `localhost:5433` spelling | Check `_env_profiles.py` `allowed_db_host_patterns` includes `127.0.0.1:5433` | Update guard (TEST-UPLIFT-1A Task 2 — fixed 2026-08-27) |
| `NotNullViolation` on seed insert | Append-only table column NOT NULL with no server default (e.g. `pricebook_item_version.created_at`) | Check `information_schema.columns` for `is_nullable=NO` + `column_default IS NULL` | Run the §7.6 per-tenant seed write-path proof before shipping; fix seed script to set the column explicitly |

**Cross-ref**: TEST-UPLIFT-1A Task 2 (host-guard IP spelling); Task 6 (seed write-path proof — `pricebook_item_version.created_at` root cause); [`README-seed-data.md`](../../backend/README-seed-data.md) §7.6.
