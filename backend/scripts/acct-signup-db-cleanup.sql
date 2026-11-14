select * from public.tenant_signup;

-- Set once per cleanup; everything downstream reads it via current_setting()
SET app.cleanup_tid = '00000000-0000-0000-0000-000000000000';   -- ← the tenant_signup.tenant_id to remove

SELECT ts.tenant_id, ts.signup_state, ts.signup_completed_at, t.name, t.is_active
FROM public.tenant_signup ts JOIN public.tenant t ON t.id = ts.tenant_id
WHERE ts.tenant_id = current_setting('app.cleanup_tid')::uuid;
-- Safe to proceed only if signup_completed_at IS NULL.

SELECT tu.user_id, u.email FROM public.tenant_user tu
JOIN public."user" u ON u.id = tu.user_id
WHERE tu.tenant_id = current_setting('app.cleanup_tid')::uuid;

-- Confirm this is the account you expect, then set the user id:
SET app.cleanup_uid = '00000000-0000-0000-0000-000000000000';   -- single quotes, not backticks

-- All of these must return 0 (completed signups will NOT):
SELECT 'subscription' AS tbl, count(*) FROM public.subscription WHERE tenant_id = current_setting('app.cleanup_tid')::uuid
UNION ALL SELECT 'customer', count(*) FROM public.customer WHERE tenant_id = current_setting('app.cleanup_tid')::uuid
UNION ALL SELECT 'notification_preference', count(*) FROM public.notification_preference WHERE tenant_id = current_setting('app.cleanup_tid')::uuid
UNION ALL SELECT 'tenant_legal_acceptance', count(*) FROM public.tenant_legal_acceptance WHERE tenant_id = current_setting('app.cleanup_tid')::uuid;

BEGIN;
SET LOCAL session_replication_role = 'replica';   -- bypass app guard triggers for this txn only
DELETE FROM public.user_sms_consent_audit WHERE tenant_id = current_setting('app.cleanup_tid')::uuid;
DELETE FROM public.user_endpoint        WHERE user_id   = current_setting('app.cleanup_uid')::uuid;
DELETE FROM public.tenant_legal_acceptance WHERE tenant_id = current_setting('app.cleanup_tid')::uuid;  -- legal-docs acceptances (RESTRICT FK to tenant + user)
DELETE FROM public.tenant_user          WHERE tenant_id = current_setting('app.cleanup_tid')::uuid;
DELETE FROM public.tenant_signup        WHERE tenant_id = current_setting('app.cleanup_tid')::uuid;
DELETE FROM public."user"               WHERE id        = current_setting('app.cleanup_uid')::uuid;
DELETE FROM public.tenant               WHERE id        = current_setting('app.cleanup_tid')::uuid;
COMMIT;