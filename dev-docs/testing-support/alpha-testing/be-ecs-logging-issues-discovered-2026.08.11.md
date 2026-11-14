# Cloudwatch Logs Issues

After pushing a new API, worker and beat app, then deploying each one, noted the events below for the worker and api that we need to investigate and address.

## pilot celery worker
No older events at this moment. 
Retry
2026-08-11T17:10:19.220Z
/usr/local/lib/python3.14/site-packages/celery/platforms.py: SecurityWarning: You're running the worker with superuser privileges: this is
2026-08-11T17:10:19.220Z
absolutely not recommended!
2026-08-11T17:10:19.220Z
Please specify a different user using the --uid option.
2026-08-11T17:10:19.220Z
User information: uid=0 euid=0 gid=0 egid=0
2026-08-11T17:10:19.220Z
warnings.warn(SecurityWarning(ROOT_DISCOURAGED.format(
2026-08-11T17:10:19.628Z
2026-08-11T17:10:19.628Z
-------------- celery@ip-10-0-11-119.ec2.internal v5.4.0 (opalescent)
2026-08-11T17:10:19.628Z
--- ***** -----
2026-08-11T17:10:19.628Z
-- ******* ---- Linux-6.1.176-x86_64-with-glibc2.41 2026-08-11 17:10:19
2026-08-11T17:10:19.628Z
- *** --- * ---
2026-08-11T17:10:19.628Z
- ** ---------- [config]
2026-08-11T17:10:19.628Z
- ** ---------- .> app: pilot_worker:0x7fb0374834d0
2026-08-11T17:10:19.628Z
- ** ---------- .> transport: redis://pilot-production.xxx.cache.amazonaws.com:6379/1
2026-08-11T17:10:19.628Z
- ** ---------- .> results: redis://pilot-production.xxx.cache.amazonaws.com:6379/2
2026-08-11T17:10:19.628Z
- *** --- * --- .> concurrency: 2 (prefork)
2026-08-11T17:10:19.628Z
-- ******* ---- .> task events: OFF (enable -E to monitor tasks in this worker)
2026-08-11T17:10:19.628Z
--- ***** -----
2026-08-11T17:10:19.628Z
-------------- [queues]
2026-08-11T17:10:19.628Z
.> celery exchange=celery(direct) key=celery
2026-08-11T17:10:19.628Z
2026-08-11T17:10:19.628Z
[tasks]
2026-08-11T17:10:19.628Z
. anonymize_help_sessions
2026-08-11T17:10:19.628Z
. archive_audit_logs
2026-08-11T17:10:19.628Z
. archive_old_mobile_sync_events
2026-08-11T17:10:19.628Z
. archive_old_sessions
2026-08-11T17:10:19.628Z
. audit_archive_stats
2026-08-11T17:10:19.628Z
. auto_expire_qb_conflicts_per_tenant
2026-08-11T17:10:19.628Z
. calculate_job_profitability
2026-08-11T17:10:19.628Z
. check_otp_timeout
2026-08-11T17:10:19.628Z
. check_system_template_updates
2026-08-11T17:10:19.628Z
. cleanup_expired_idempotency_keys
2026-08-11T17:10:19.628Z
. cleanup_incomplete_photo_uploads
2026-08-11T17:10:19.628Z
. cleanup_old_failed_keys
2026-08-11T17:10:19.628Z
. cleanup_orphaned_messages
2026-08-11T17:10:19.628Z
. create_recurring_carrier_items
2026-08-11T17:10:19.628Z
. dunning_reminders
2026-08-11T17:10:19.628Z
. enforce_trial_expirations
2026-08-11T17:10:19.628Z
. expire_old_sessions
2026-08-11T17:10:19.628Z
. expire_pending_voice_confirmations
2026-08-11T17:10:19.628Z
. expire_quote_discounts
2026-08-11T17:10:19.628Z
. export_voice_feedback_to_s3
2026-08-11T17:10:19.628Z
. free_period_notifications
2026-08-11T17:10:19.628Z
. generate_help_session_title
2026-08-11T17:10:19.628Z
. generate_session_title
2026-08-11T17:10:19.628Z
. monitor_sms_quota_thresholds
2026-08-11T17:10:19.628Z
. notify_etc_variance_owners
2026-08-11T17:10:19.628Z
. notify_mfa_grace_period_reminders
2026-08-11T17:10:19.628Z
. notify_system_template_updates
2026-08-11T17:10:19.628Z
. poll_pending_notifications
2026-08-11T17:10:19.628Z
. process_data_export
2026-08-11T17:10:19.628Z
. process_help_article
2026-08-11T17:10:19.628Z
. process_voice_audio_async
2026-08-11T17:10:19.628Z
. provision_brand
2026-08-11T17:10:19.628Z
. provision_campaign
2026-08-11T17:10:19.628Z
. pull_calendar_blocks
2026-08-11T17:10:19.628Z
. pull_calendar_blocks_all_tenants
2026-08-11T17:10:19.628Z
. push_job_to_calendar
2026-08-11T17:10:19.628Z
. quote_expiration_monitor
2026-08-11T17:10:19.628Z
. receipt_ocr.process_receipt_ocr
2026-08-11T17:10:19.628Z
. refresh_quickbooks_tokens
2026-08-11T17:10:19.628Z
. rollover_sms_quota_periods
2026-08-11T17:10:19.628Z
. saas_billing_aggregator
2026-08-11T17:10:19.628Z
. send_application_confirmation
2026-08-11T17:10:19.628Z
. send_contact_confirmation
2026-08-11T17:10:19.628Z
. send_double_optin_sms
2026-08-11T17:10:19.628Z
. send_feedback_email
2026-08-11T17:10:19.628Z
. send_newsletter_confirmation
2026-08-11T17:10:19.628Z
. send_notification
2026-08-11T17:10:19.628Z
. send_platform_account_notification_sms
2026-08-11T17:10:19.628Z
. send_platform_double_optin_sms
2026-08-11T17:10:19.628Z
. send_waitlist_confirmation
2026-08-11T17:10:19.628Z
. sync_all_tenants_customers
2026-08-11T17:10:19.628Z
. sync_customer_to_qb
2026-08-11T17:10:19.628Z
. sync_invoice_to_qb
2026-08-11T17:10:19.628Z
. sync_payment_to_qb
2026-08-11T17:10:19.628Z
. sync_quickbooks_customers
2026-08-11T17:10:19.628Z
. sync_quickbooks_entity
2026-08-11T17:10:19.628Z
. tasks.background_sync_push.scan_and_dispatch_background_sync_pushes
2026-08-11T17:10:19.628Z
. tasks.background_sync_push.send_background_sync_push
2026-08-11T17:10:19.628Z
. tasks.expire_stale_calendar_conflicts
2026-08-11T17:10:19.628Z
. tasks.recurring_jobs.enqueue_recurring_job_notification
2026-08-11T17:10:19.628Z
. tasks.recurring_jobs.generate_due_recurring_jobs
2026-08-11T17:10:19.628Z
. tasks.test_task.add_numbers
2026-08-11T17:10:22.097Z
[2026-08-11 17:10:22,094: INFO/MainProcess] Connected to redis://pilot-production.xxx.cache.amazonaws.com:6379/1
2026-08-11T17:10:22.205Z
[2026-08-11 17:10:22,204: INFO/MainProcess] mingle: searching for neighbors
2026-08-11T17:10:23.310Z
[2026-08-11 17:10:23,310: INFO/MainProcess] mingle: sync with 1 nodes
2026-08-11T17:10:23.310Z
[2026-08-11 17:10:23,310: INFO/MainProcess] mingle: sync complete
2026-08-11T17:10:23.626Z
[2026-08-11 17:10:23,626: INFO/MainProcess] celery@ip-10-0-11-119.ec2.internal ready.
2026-08-11T17:11:26.122Z
[2026-08-11 17:11:26,122: INFO/MainProcess] Task poll_pending_notifications[aea742ee-a340-464c-a95d-3b8d560a14f5] received

## pilot api

Timestamp
	
Message

There are older events to load. 
Load more.
2026-08-11T17:15:06.090Z
INFO: 203.0.113.15:0 - "GET /api/v1/users/me/permissions HTTP/1.1" 404 Not Found
2026-08-11T17:15:06.503Z
INFO: 203.0.113.15:0 - "GET /api/v1/subscription-tiers HTTP/1.1" 307 Temporary Redirect
2026-08-11T17:15:06.548Z
INFO: 203.0.113.15:0 - "GET /api/v1/subscription-tiers/ HTTP/1.1" 401 Unauthorized
2026-08-11T17:15:07.578Z
INFO: 203.0.113.15:0 - "GET /api/v1/subscription-tiers HTTP/1.1" 307 Temporary Redirect
2026-08-11T17:15:07.610Z
INFO: 203.0.113.15:0 - "GET /api/v1/subscription-tiers/ HTTP/1.1" 401 Unauthorized
2026-08-11T17:15:12.502Z
INFO: 10.0.1.5:62138 - "GET /api/v1/health/celery HTTP/1.1" 200 OK
2026-08-11T17:15:12.510Z
INFO: 10.0.2.12:47312 - "GET /api/v1/health/celery HTTP/1.1" 200 OK
2026-08-11T17:15:42.507Z
INFO: 10.0.1.5:10404 - "GET /api/v1/health/celery HTTP/1.1" 200 OK
2026-08-11T17:15:42.526Z
INFO: 10.0.2.12:23060 - "GET /api/v1/health/celery HTTP/1.1" 200 OK
2026-08-11T17:16:12.528Z
INFO: 10.0.2.12:57668 - "GET /api/v1/health/celery HTTP/1.1" 200 OK
2026-08-11T17:16:12.530Z
INFO: 10.0.1.5:24102 - "GET /api/v1/health/celery HTTP/1.1" 200 OK
2026-08-11T17:16:32.814Z
INFO: 203.0.113.15:0 - "OPTIONS /api/v1/users/me/permissions HTTP/1.1" 200 OK
2026-08-11T17:16:33.973Z
INFO: 203.0.113.15:0 - "GET /api/v1/users/me/permissions HTTP/1.1" 200 OK
2026-08-11T17:16:34.126Z
INFO: 203.0.113.15:0 - "OPTIONS /api/v1/signup HTTP/1.1" 200 OK
2026-08-11T17:16:34.174Z
INFO: 203.0.113.15:0 - "POST /api/v1/signup HTTP/1.1" 307 Temporary Redirect
2026-08-11T17:16:34.210Z
INFO: 203.0.113.15:0 - "OPTIONS /api/v1/signup/ HTTP/1.1" 200 OK
2026-08-11T17:16:34.290Z
INFO: 203.0.113.15:0 - "POST /api/v1/signup/ HTTP/1.1" 201 Created
2026-08-11T17:16:34.402Z
INFO: 203.0.113.15:0 - "OPTIONS /api/v1/signup/00000000-0000-0000-0000-0000000000b1/state HTTP/1.1" 200 OK
2026-08-11T17:16:34.426Z
INFO: 203.0.113.15:0 - "OPTIONS /api/v1/signup/00000000-0000-0000-0000-0000000000b1/legal/required HTTP/1.1" 200 OK
2026-08-11T17:16:34.482Z
INFO: 203.0.113.15:0 - "GET /api/v1/signup/00000000-0000-0000-0000-0000000000b1/state HTTP/1.1" 200 OK
2026-08-11T17:16:34.530Z
INFO: 203.0.113.15:0 - "GET /api/v1/signup/00000000-0000-0000-0000-0000000000b1/legal/required HTTP/1.1" 200 OK
2026-08-11T17:16:40.230Z
INFO: 203.0.113.15:0 - "OPTIONS /api/v1/signup/00000000-0000-0000-0000-0000000000b1/legal/accept HTTP/1.1" 200 OK
2026-08-11T17:16:40.291Z
INFO: 203.0.113.15:0 - "POST /api/v1/signup/00000000-0000-0000-0000-0000000000b1/legal/accept HTTP/1.1" 201 Created
2026-08-11T17:16:40.344Z
INFO: 203.0.113.15:0 - "POST /api/v1/signup/00000000-0000-0000-0000-0000000000b1/legal/accept HTTP/1.1" 201 Created
2026-08-11T17:16:40.403Z
INFO: 203.0.113.15:0 - "POST /api/v1/signup/00000000-0000-0000-0000-0000000000b1/legal/accept HTTP/1.1" 201 Created
2026-08-11T17:16:40.454Z
INFO: 203.0.113.15:0 - "OPTIONS /api/v1/signup/00000000-0000-0000-0000-0000000000b1/step2 HTTP/1.1" 200 OK
2026-08-11T17:16:40.521Z
INFO: 203.0.113.15:0 - "PUT /api/v1/signup/00000000-0000-0000-0000-0000000000b1/step2 HTTP/1.1" 200 OK
2026-08-11T17:16:40.630Z
INFO: 203.0.113.15:0 - "GET /api/v1/signup/00000000-0000-0000-0000-0000000000b1/state HTTP/1.1" 200 OK
2026-08-11T17:16:42.541Z
INFO: 10.0.2.12:2140 - "GET /api/v1/health/celery HTTP/1.1" 200 OK
2026-08-11T17:16:42.560Z
INFO: 10.0.1.5:34214 - "GET /api/v1/health/celery HTTP/1.1" 200 OK
2026-08-11T17:16:46.983Z
INFO: 203.0.113.15:0 - "OPTIONS /api/v1/signup/00000000-0000-0000-0000-0000000000b1/phone/consent HTTP/1.1" 200 OK
2026-08-11T17:16:47.077Z
INFO: 203.0.113.15:0 - "POST /api/v1/signup/00000000-0000-0000-0000-0000000000b1/phone/consent HTTP/1.1" 201 Created
2026-08-11T17:16:47.119Z
INFO: 203.0.113.15:0 - "OPTIONS /api/v1/signup/00000000-0000-0000-0000-0000000000b1/phone/send-optin HTTP/1.1" 200 OK
2026-08-11T17:16:47.277Z
INFO: 203.0.113.15:0 - "POST /api/v1/signup/00000000-0000-0000-0000-0000000000b1/phone/send-optin HTTP/1.1" 200 OK
2026-08-11T17:16:47.319Z
INFO: 203.0.113.15:0 - "OPTIONS /api/v1/signup/00000000-0000-0000-0000-0000000000b1/step3 HTTP/1.1" 200 OK
2026-08-11T17:16:47.388Z
INFO: 203.0.113.15:0 - "PUT /api/v1/signup/00000000-0000-0000-0000-0000000000b1/step3 HTTP/1.1" 200 OK
2026-08-11T17:16:50.450Z
INFO: 203.0.113.15:0 - "GET /api/v1/signup/00000000-0000-0000-0000-0000000000b1/state HTTP/1.1" 200 OK
2026-08-11T17:16:53.444Z
INFO: 203.0.113.15:0 - "GET /api/v1/signup/00000000-0000-0000-0000-0000000000b1/state HTTP/1.1" 200 OK
2026-08-11T17:16:56.445Z
INFO: 203.0.113.15:0 - "GET /api/v1/signup/00000000-0000-0000-0000-0000000000b1/state HTTP/1.1" 200 OK
2026-08-11T17:16:59.564Z
INFO: 203.0.113.15:0 - "GET /api/v1/signup/00000000-0000-0000-0000-0000000000b1/state HTTP/1.1" 200 OK
2026-08-11T17:17:11.064Z
INFO: 203.0.113.30:0 - "POST /api/v1/webhooks/sms/telnyx-inbound HTTP/1.1" 200 OK
2026-08-11T17:17:11.066Z
INFO: 203.0.113.31:0 - "POST /api/v1/webhooks/sms/telnyx-inbound HTTP/1.1" 200 OK
2026-08-11T17:17:11.170Z
INFO: 203.0.113.15:0 - "GET /api/v1/signup/00000000-0000-0000-0000-0000000000b1/state HTTP/1.1" 200 OK
2026-08-11T17:17:11.369Z
INFO: 203.0.113.15:0 - "GET /api/v1/signup/00000000-0000-0000-0000-0000000000b1/state HTTP/1.1" 200 OK
2026-08-11T17:17:11.962Z
INFO: 203.0.113.30:0 - "POST /api/v1/webhooks/sms/telnyx-inbound HTTP/1.1" 200 OK
2026-08-11T17:17:12.159Z
INFO: 203.0.113.15:0 - "GET /api/v1/signup/00000000-0000-0000-0000-0000000000b1/state HTTP/1.1" 200 OK
2026-08-11T17:17:12.366Z
INFO: 203.0.113.15:0 - "GET /api/v1/signup/00000000-0000-0000-0000-0000000000b1/state HTTP/1.1" 200 OK
2026-08-11T17:17:12.869Z
INFO: 10.0.2.12:15468 - "GET /api/v1/health/celery HTTP/1.1" 200 OK
2026-08-11T17:17:13.162Z
INFO: 10.0.1.5:7970 - "GET /api/v1/health/celery HTTP/1.1" 200 OK
2026-08-11T17:17:13.177Z
ERROR: Exception in ASGI application
2026-08-11T17:17:13.177Z
+ Exception Group Traceback (most recent call last):
2026-08-11T17:17:13.177Z
| File "/usr/local/lib/python3.14/site-packages/starlette/_utils.py", line 81, in collapse_excgroups
2026-08-11T17:17:13.177Z
| yield
2026-08-11T17:17:13.177Z
| File "/usr/local/lib/python3.14/site-packages/starlette/middleware/base.py", line 192, in __call__
2026-08-11T17:17:13.177Z
| async with anyio.create_task_group() as task_group:
2026-08-11T17:17:13.177Z
| ~~~~~~~~~~~~~~~~~~~~~~~^^
2026-08-11T17:17:13.177Z
| File "/usr/local/lib/python3.14/site-packages/anyio/_backends/_asyncio.py", line 783, in __aexit__
2026-08-11T17:17:13.177Z
| raise BaseExceptionGroup(
2026-08-11T17:17:13.177Z
| "unhandled errors in a TaskGroup", self._exceptions
2026-08-11T17:17:13.177Z
| ) from None
2026-08-11T17:17:13.177Z
| ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
2026-08-11T17:17:13.177Z
+-+---------------- 1 ----------------
2026-08-11T17:17:13.177Z
| Traceback (most recent call last):
2026-08-11T17:17:13.177Z
| File "/usr/local/lib/python3.14/site-packages/uvicorn/protocols/http/httptools_impl.py", line 416, in run_asgi
2026-08-11T17:17:13.177Z
| result = await app( # type: ignore[func-returns-value]
2026-08-11T17:17:13.177Z
| ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-08-11T17:17:13.177Z
| self.scope, self.receive, self.send
2026-08-11T17:17:13.177Z
| ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-08-11T17:17:13.177Z
| )
2026-08-11T17:17:13.177Z
| ^
2026-08-11T17:17:13.177Z
| File "/usr/local/lib/python3.14/site-packages/uvicorn/middleware/proxy_headers.py", line 60, in __call__
2026-08-11T17:17:13.177Z
| return await self.app(scope, receive, send)
2026-08-11T17:17:13.177Z
| ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-08-11T17:17:13.177Z
| File "/usr/local/lib/python3.14/site-packages/fastapi/applications.py", line 1160, in __call__
2026-08-11T17:17:13.177Z
| await super().__call__(scope, receive, send)
2026-08-11T17:17:13.177Z
| File "/usr/local/lib/python3.14/site-packages/starlette/applications.py", line 107, in __call__
2026-08-11T17:17:13.177Z
| await self.middleware_stack(scope, receive, send)
2026-08-11T17:17:13.177Z
| File "/usr/local/lib/python3.14/site-packages/starlette/middleware/errors.py", line 186, in __call__
2026-08-11T17:17:13.177Z
| raise exc
2026-08-11T17:17:13.177Z
| File "/usr/local/lib/python3.14/site-packages/starlette/middleware/errors.py", line 164, in __call__
2026-08-11T17:17:13.177Z
| await self.app(scope, receive, _send)
2026-08-11T17:17:13.177Z
| File "/usr/local/lib/python3.14/site-packages/starlette/middleware/base.py", line 191, in __call__
2026-08-11T17:17:13.177Z
| with recv_stream, send_stream, collapse_excgroups():
2026-08-11T17:17:13.177Z
| ~~~~~~~~~~~~~~~~~~^^
2026-08-11T17:17:13.177Z
| File "/usr/local/lib/python3.14/contextlib.py", line 162, in __exit__
2026-08-11T17:17:13.177Z
| self.gen.throw(value)
2026-08-11T17:17:13.177Z
| ~~~~~~~~~~~~~~^^^^^^^
2026-08-11T17:17:13.177Z
| File "/usr/local/lib/python3.14/site-packages/starlette/_utils.py", line 87, in collapse_excgroups
2026-08-11T17:17:13.177Z
| raise exc
2026-08-11T17:17:13.177Z
| File "/usr/local/lib/python3.14/site-packages/starlette/middleware/base.py", line 193, in __call__
2026-08-11T17:17:13.177Z
| response = await self.dispatch_func(request, call_next)
2026-08-11T17:17:13.177Z
| ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-08-11T17:17:13.177Z
| File "/app/app/main.py", line 472, in impersonation_audit_middleware
2026-08-11T17:17:13.177Z
| response = await call_next(request)
2026-08-11T17:17:13.177Z
| ^^^^^^^^^^^^^^^^^^^^^^^^
2026-08-11T17:17:13.177Z
| File "/usr/local/lib/python3.14/site-packages/starlette/middleware/base.py", line 168, in call_next
2026-08-11T17:17:13.177Z
| raise app_exc from app_exc.__cause__ or app_exc.__context__
2026-08-11T17:17:13.177Z
| File "/usr/local/lib/python3.14/site-packages/starlette/middleware/base.py", line 144, in coro
2026-08-11T17:17:13.177Z
| await self.app(scope, receive_or_disconnect, send_no_error)
2026-08-11T17:17:13.177Z
| File "/usr/local/lib/python3.14/site-packages/starlette/middleware/cors.py", line 87, in __call__
2026-08-11T17:17:13.177Z
| await self.app(scope, receive, send)
2026-08-11T17:17:13.177Z
| File "/usr/local/lib/python3.14/site-packages/starlette/middleware/base.py", line 191, in __call__
2026-08-11T17:17:13.177Z
| with recv_stream, send_stream, collapse_excgroups():
2026-08-11T17:17:13.177Z
| ~~~~~~~~~~~~~~~~~~^^
2026-08-11T17:17:13.177Z
| File "/usr/local/lib/python3.14/contextlib.py", line 162, in __exit__
2026-08-11T17:17:13.177Z
| self.gen.throw(value)
2026-08-11T17:17:13.177Z
| ~~~~~~~~~~~~~~^^^^^^^
2026-08-11T17:17:13.177Z
| File "/usr/local/lib/python3.14/site-packages/starlette/_utils.py", line 87, in collapse_excgroups
2026-08-11T17:17:13.177Z
| raise exc
2026-08-11T17:17:13.177Z
| File "/usr/local/lib/python3.14/site-packages/starlette/middleware/base.py", line 193, in __call__
2026-08-11T17:17:13.177Z
| response = await self.dispatch_func(request, call_next)
2026-08-11T17:17:13.177Z
| ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-08-11T17:17:13.177Z
| File "/app/core/idempotency.py", line 107, in idempotency_middleware
2026-08-11T17:17:13.177Z
| return await call_next(request)
2026-08-11T17:17:13.177Z
| ^^^^^^^^^^^^^^^^^^^^^^^^
2026-08-11T17:17:13.177Z
| File "/usr/local/lib/python3.14/site-packages/starlette/middleware/base.py", line 168, in call_next
2026-08-11T17:17:13.177Z
| raise app_exc from app_exc.__cause__ or app_exc.__context__
2026-08-11T17:17:13.177Z
| File "/usr/local/lib/python3.14/site-packages/starlette/middleware/base.py", line 144, in coro
2026-08-11T17:17:13.177Z
| await self.app(scope, receive_or_disconnect, send_no_error)
2026-08-11T17:17:13.177Z
| File "/usr/local/lib/python3.14/site-packages/starlette/middleware/base.py", line 191, in __call__
2026-08-11T17:17:13.177Z
| with recv_stream, send_stream, collapse_excgroups():
2026-08-11T17:17:13.177Z
| ~~~~~~~~~~~~~~~~~~^^
2026-08-11T17:17:13.177Z
| File "/usr/local/lib/python3.14/contextlib.py", line 162, in __exit__
2026-08-11T17:17:13.177Z
| self.gen.throw(value)
2026-08-11T17:17:13.177Z
| ~~~~~~~~~~~~~~^^^^^^^
2026-08-11T17:17:13.177Z
| File "/usr/local/lib/python3.14/site-packages/starlette/_utils.py", line 87, in collapse_excgroups
2026-08-11T17:17:13.177Z
| raise exc
2026-08-11T17:17:13.177Z
| File "/usr/local/lib/python3.14/site-packages/starlette/middleware/base.py", line 193, in __call__
2026-08-11T17:17:13.177Z
| response = await self.dispatch_func(request, call_next)
2026-08-11T17:17:13.177Z
| ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-08-11T17:17:13.177Z
| File "/app/core/middleware.py", line 93, in dispatch
2026-08-11T17:17:13.177Z
| response = await call_next(request)
2026-08-11T17:17:13.177Z
| ^^^^^^^^^^^^^^^^^^^^^^^^
2026-08-11T17:17:13.177Z
| File "/usr/local/lib/python3.14/site-packages/starlette/middleware/base.py", line 168, in call_next
2026-08-11T17:17:13.177Z
| raise app_exc from app_exc.__cause__ or app_exc.__context__
2026-08-11T17:17:13.177Z
| File "/usr/local/lib/python3.14/site-packages/starlette/middleware/base.py", line 144, in coro
2026-08-11T17:17:13.177Z
| await self.app(scope, receive_or_disconnect, send_no_error)
2026-08-11T17:17:13.177Z
| File "/usr/local/lib/python3.14/site-packages/starlette/middleware/exceptions.py", line 63, in __call__
2026-08-11T17:17:13.177Z
| await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
2026-08-11T17:17:13.177Z
| File "/usr/local/lib/python3.14/site-packages/starlette/_exception_handler.py", line 53, in wrapped_app
2026-08-11T17:17:13.177Z
| raise exc
2026-08-11T17:17:13.177Z
| File "/usr/local/lib/python3.14/site-packages/starlette/_exception_handler.py", line 42, in wrapped_app
2026-08-11T17:17:13.177Z
| await app(scope, receive, sender)
2026-08-11T17:17:13.177Z
| File "/usr/local/lib/python3.14/site-packages/fastapi/middleware/asyncexitstack.py", line 18, in __call__
2026-08-11T17:17:13.177Z
| await self.app(scope, receive, send)
2026-08-11T17:17:13.177Z
| File "/usr/local/lib/python3.14/site-packages/starlette/routing.py", line 716, in __call__
2026-08-11T17:17:13.177Z
| await self.middleware_stack(scope, receive, send)
2026-08-11T17:17:13.177Z
| File "/usr/local/lib/python3.14/site-packages/starlette/routing.py", line 736, in app
2026-08-11T17:17:13.177Z
| await route.handle(scope, receive, send)
2026-08-11T17:17:13.177Z
| File "/usr/local/lib/python3.14/site-packages/starlette/routing.py", line 290, in handle
2026-08-11T17:17:13.177Z
| await self.app(scope, receive, send)
2026-08-11T17:17:13.177Z
| File "/usr/local/lib/python3.14/site-packages/fastapi/routing.py", line 130, in app
2026-08-11T17:17:13.177Z
| await wrap_app_handling_exceptions(app, request)(scope, receive, send)
2026-08-11T17:17:13.177Z
| File "/usr/local/lib/python3.14/site-packages/starlette/_exception_handler.py", line 53, in wrapped_app
2026-08-11T17:17:13.177Z
| raise exc
2026-08-11T17:17:13.177Z
| File "/usr/local/lib/python3.14/site-packages/starlette/_exception_handler.py", line 42, in wrapped_app
2026-08-11T17:17:13.177Z
| await app(scope, receive, sender)
2026-08-11T17:17:13.177Z
| File "/usr/local/lib/python3.14/site-packages/fastapi/routing.py", line 116, in app
2026-08-11T17:17:13.177Z
| response = await f(request)
2026-08-11T17:17:13.177Z
| ^^^^^^^^^^^^^^^^
2026-08-11T17:17:13.177Z
| File "/usr/local/lib/python3.14/site-packages/fastapi/routing.py", line 670, in app
2026-08-11T17:17:13.177Z
| raw_response = await run_endpoint_function(
2026-08-11T17:17:13.177Z
| ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-08-11T17:17:13.177Z
| ...<3 lines>...
2026-08-11T17:17:13.177Z
| )
2026-08-11T17:17:13.177Z
| ^
2026-08-11T17:17:13.177Z
| File "/usr/local/lib/python3.14/site-packages/fastapi/routing.py", line 324, in run_endpoint_function
2026-08-11T17:17:13.177Z
| return await dependant.call(**values)
2026-08-11T17:17:13.177Z
| ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-08-11T17:17:13.177Z
| File "/app/api/routes/webhooks_sms.py", line 549, in telnyx_inbound_sms
2026-08-11T17:17:13.177Z
| payload_bytes = await request.body()
2026-08-11T17:17:13.177Z
| ^^^^^^^^^^^^^^^^^^^^
2026-08-11T17:17:13.177Z
| File "/usr/local/lib/python3.14/site-packages/starlette/requests.py", line 251, in body
2026-08-11T17:17:13.177Z
| async for chunk in self.stream():
2026-08-11T17:17:13.177Z
| chunks.append(chunk)
2026-08-11T17:17:13.177Z
| File "/usr/local/lib/python3.14/site-packages/starlette/requests.py", line 245, in stream
2026-08-11T17:17:13.177Z
| raise ClientDisconnect()
2026-08-11T17:17:13.177Z
| starlette.requests.ClientDisconnect
2026-08-11T17:17:13.177Z
+------------------------------------
2026-08-11T17:17:13.177Z
The above exception was the direct cause of the following exception:
2026-08-11T17:17:13.177Z
Traceback (most recent call last):
2026-08-11T17:17:13.177Z
File "/usr/local/lib/python3.14/site-packages/uvicorn/protocols/http/httptools_impl.py", line 416, in run_asgi
2026-08-11T17:17:13.177Z
result = await app( # type: ignore[func-returns-value]
2026-08-11T17:17:13.177Z
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-08-11T17:17:13.177Z
self.scope, self.receive, self.send
2026-08-11T17:17:13.177Z
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-08-11T17:17:13.177Z
)
2026-08-11T17:17:13.177Z
^
2026-08-11T17:17:13.177Z
File "/usr/local/lib/python3.14/site-packages/uvicorn/middleware/proxy_headers.py", line 60, in __call__
2026-08-11T17:17:13.177Z
return await self.app(scope, receive, send)
2026-08-11T17:17:13.177Z
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-08-11T17:17:13.177Z
File "/usr/local/lib/python3.14/site-packages/fastapi/applications.py", line 1160, in __call__
2026-08-11T17:17:13.177Z
await super().__call__(scope, receive, send)
2026-08-11T17:17:13.177Z
File "/usr/local/lib/python3.14/site-packages/starlette/applications.py", line 107, in __call__
2026-08-11T17:17:13.177Z
await self.middleware_stack(scope, receive, send)
2026-08-11T17:17:13.177Z
File "/usr/local/lib/python3.14/site-packages/starlette/middleware/errors.py", line 186, in __call__
2026-08-11T17:17:13.177Z
raise exc
2026-08-11T17:17:13.177Z
File "/usr/local/lib/python3.14/site-packages/starlette/middleware/errors.py", line 164, in __call__
2026-08-11T17:17:13.177Z
await self.app(scope, receive, _send)
2026-08-11T17:17:13.177Z
File "/usr/local/lib/python3.14/site-packages/starlette/middleware/base.py", line 191, in __call__
2026-08-11T17:17:13.177Z
with recv_stream, send_stream, collapse_excgroups():
2026-08-11T17:17:13.177Z
~~~~~~~~~~~~~~~~~~^^
2026-08-11T17:17:13.177Z
File "/usr/local/lib/python3.14/contextlib.py", line 162, in __exit__
2026-08-11T17:17:13.177Z
self.gen.throw(value)
2026-08-11T17:17:13.177Z
~~~~~~~~~~~~~~^^^^^^^
2026-08-11T17:17:13.177Z
File "/usr/local/lib/python3.14/site-packages/starlette/_utils.py", line 87, in collapse_excgroups
2026-08-11T17:17:13.177Z
raise exc
2026-08-11T17:17:13.177Z
File "/usr/local/lib/python3.14/site-packages/starlette/middleware/base.py", line 193, in __call__
2026-08-11T17:17:13.177Z
response = await self.dispatch_func(request, call_next)
2026-08-11T17:17:13.177Z
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-08-11T17:17:13.177Z
File "/app/app/main.py", line 472, in impersonation_audit_middleware
2026-08-11T17:17:13.177Z
response = await call_next(request)
2026-08-11T17:17:13.177Z
^^^^^^^^^^^^^^^^^^^^^^^^
2026-08-11T17:17:13.177Z
File "/usr/local/lib/python3.14/site-packages/starlette/middleware/base.py", line 168, in call_next
2026-08-11T17:17:13.177Z
raise app_exc from app_exc.__cause__ or app_exc.__context__
2026-08-11T17:17:13.177Z
File "/usr/local/lib/python3.14/site-packages/starlette/middleware/base.py", line 144, in coro
2026-08-11T17:17:13.177Z
await self.app(scope, receive_or_disconnect, send_no_error)
2026-08-11T17:17:13.177Z
File "/usr/local/lib/python3.14/site-packages/starlette/middleware/cors.py", line 87, in __call__
2026-08-11T17:17:13.177Z
await self.app(scope, receive, send)
2026-08-11T17:17:13.177Z
File "/usr/local/lib/python3.14/site-packages/starlette/middleware/base.py", line 191, in __call__
2026-08-11T17:17:13.177Z
with recv_stream, send_stream, collapse_excgroups():
2026-08-11T17:17:13.177Z
~~~~~~~~~~~~~~~~~~^^
2026-08-11T17:17:13.177Z
File "/usr/local/lib/python3.14/contextlib.py", line 162, in __exit__
2026-08-11T17:17:13.177Z
self.gen.throw(value)
2026-08-11T17:17:13.177Z
~~~~~~~~~~~~~~^^^^^^^
2026-08-11T17:17:13.177Z
File "/usr/local/lib/python3.14/site-packages/starlette/_utils.py", line 87, in collapse_excgroups
2026-08-11T17:17:13.177Z
raise exc
2026-08-11T17:17:13.177Z
File "/usr/local/lib/python3.14/site-packages/starlette/middleware/base.py", line 193, in __call__
2026-08-11T17:17:13.177Z
response = await self.dispatch_func(request, call_next)
2026-08-11T17:17:13.177Z
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-08-11T17:17:13.177Z
File "/app/core/idempotency.py", line 107, in idempotency_middleware
2026-08-11T17:17:13.177Z
return await call_next(request)
2026-08-11T17:17:13.177Z
^^^^^^^^^^^^^^^^^^^^^^^^
2026-08-11T17:17:13.177Z
File "/usr/local/lib/python3.14/site-packages/starlette/middleware/base.py", line 168, in call_next
2026-08-11T17:17:13.177Z
raise app_exc from app_exc.__cause__ or app_exc.__context__
2026-08-11T17:17:13.177Z
File "/usr/local/lib/python3.14/site-packages/starlette/middleware/base.py", line 144, in coro
2026-08-11T17:17:13.178Z
await self.app(scope, receive_or_disconnect, send_no_error)
2026-08-11T17:17:13.178Z
File "/usr/local/lib/python3.14/site-packages/starlette/middleware/base.py", line 191, in __call__
2026-08-11T17:17:13.178Z
with recv_stream, send_stream, collapse_excgroups():
2026-08-11T17:17:13.178Z
~~~~~~~~~~~~~~~~~~^^
2026-08-11T17:17:13.178Z
File "/usr/local/lib/python3.14/contextlib.py", line 162, in __exit__
2026-08-11T17:17:13.178Z
self.gen.throw(value)
2026-08-11T17:17:13.178Z
~~~~~~~~~~~~~~^^^^^^^
2026-08-11T17:17:13.178Z
File "/usr/local/lib/python3.14/site-packages/starlette/_utils.py", line 87, in collapse_excgroups
2026-08-11T17:17:13.178Z
raise exc
2026-08-11T17:17:13.178Z
File "/usr/local/lib/python3.14/site-packages/starlette/middleware/base.py", line 193, in __call__
2026-08-11T17:17:13.178Z
response = await self.dispatch_func(request, call_next)
2026-08-11T17:17:13.178Z
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-08-11T17:17:13.178Z
File "/app/core/middleware.py", line 93, in dispatch
2026-08-11T17:17:13.178Z
response = await call_next(request)
2026-08-11T17:17:13.178Z
^^^^^^^^^^^^^^^^^^^^^^^^
2026-08-11T17:17:13.178Z
File "/usr/local/lib/python3.14/site-packages/starlette/middleware/base.py", line 168, in call_next
2026-08-11T17:17:13.178Z
raise app_exc from app_exc.__cause__ or app_exc.__context__
2026-08-11T17:17:13.178Z
File "/usr/local/lib/python3.14/site-packages/starlette/middleware/base.py", line 144, in coro
2026-08-11T17:17:13.178Z
await self.app(scope, receive_or_disconnect, send_no_error)
2026-08-11T17:17:13.178Z
File "/usr/local/lib/python3.14/site-packages/starlette/middleware/exceptions.py", line 63, in __call__
2026-08-11T17:17:13.178Z
await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
2026-08-11T17:17:13.178Z
File "/usr/local/lib/python3.14/site-packages/starlette/_exception_handler.py", line 53, in wrapped_app
2026-08-11T17:17:13.178Z
raise exc
2026-08-11T17:17:13.178Z
File "/usr/local/lib/python3.14/site-packages/starlette/_exception_handler.py", line 42, in wrapped_app
2026-08-11T17:17:13.178Z
await app(scope, receive, sender)
2026-08-11T17:17:13.178Z
File "/usr/local/lib/python3.14/site-packages/fastapi/middleware/asyncexitstack.py", line 18, in __call__
2026-08-11T17:17:13.178Z
await self.app(scope, receive, send)
2026-08-11T17:17:13.178Z
File "/usr/local/lib/python3.14/site-packages/starlette/routing.py", line 716, in __call__
2026-08-11T17:17:13.178Z
await self.middleware_stack(scope, receive, send)
2026-08-11T17:17:13.178Z
File "/usr/local/lib/python3.14/site-packages/starlette/routing.py", line 736, in app
2026-08-11T17:17:13.178Z
await route.handle(scope, receive, send)
2026-08-11T17:17:13.178Z
File "/usr/local/lib/python3.14/site-packages/starlette/routing.py", line 290, in handle
2026-08-11T17:17:13.178Z
await self.app(scope, receive, send)
2026-08-11T17:17:13.178Z
File "/usr/local/lib/python3.14/site-packages/fastapi/routing.py", line 130, in app
2026-08-11T17:17:13.178Z
await wrap_app_handling_exceptions(app, request)(scope, receive, send)
2026-08-11T17:17:13.178Z
File "/usr/local/lib/python3.14/site-packages/starlette/_exception_handler.py", line 53, in wrapped_app
2026-08-11T17:17:13.178Z
raise exc
2026-08-11T17:17:13.178Z
File "/usr/local/lib/python3.14/site-packages/starlette/_exception_handler.py", line 42, in wrapped_app
2026-08-11T17:17:13.178Z
await app(scope, receive, sender)
2026-08-11T17:17:13.178Z
File "/usr/local/lib/python3.14/site-packages/fastapi/routing.py", line 116, in app
2026-08-11T17:17:13.178Z
response = await f(request)
2026-08-11T17:17:13.178Z
^^^^^^^^^^^^^^^^
2026-08-11T17:17:13.178Z
File "/usr/local/lib/python3.14/site-packages/fastapi/routing.py", line 670, in app
2026-08-11T17:17:13.178Z
raw_response = await run_endpoint_function(
2026-08-11T17:17:13.178Z
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-08-11T17:17:13.178Z
...<3 lines>...
2026-08-11T17:17:13.178Z
)
2026-08-11T17:17:13.178Z
^
2026-08-11T17:17:13.178Z
File "/usr/local/lib/python3.14/site-packages/fastapi/routing.py", line 324, in run_endpoint_function
2026-08-11T17:17:13.178Z
return await dependant.call(**values)
2026-08-11T17:17:13.178Z
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-08-11T17:17:13.178Z
File "/app/api/routes/webhooks_sms.py", line 549, in telnyx_inbound_sms
2026-08-11T17:17:13.178Z
payload_bytes = await request.body()
2026-08-11T17:17:13.178Z
^^^^^^^^^^^^^^^^^^^^
2026-08-11T17:17:13.178Z
File "/usr/local/lib/python3.14/site-packages/starlette/requests.py", line 251, in body
2026-08-11T17:17:13.178Z
async for chunk in self.stream():
2026-08-11T17:17:13.178Z
chunks.append(chunk)
2026-08-11T17:17:13.178Z
File "/usr/local/lib/python3.14/site-packages/starlette/requests.py", line 245, in stream
2026-08-11T17:17:13.178Z
raise ClientDisconnect()
2026-08-11T17:17:13.178Z
starlette.requests.ClientDisconnect
2026-08-11T17:17:14.476Z
INFO: 203.0.113.15:0 - "GET /api/v1/signup/00000000-0000-0000-0000-0000000000b1/state HTTP/1.1" 200 OK
2026-08-11T17:17:16.088Z
INFO: 203.0.113.15:0 - "OPTIONS /api/v1/subscription-tiers HTTP/1.1" 200 OK
2026-08-11T17:17:16.103Z
INFO: 203.0.113.15:0 - "GET /api/v1/signup/00000000-0000-0000-0000-0000000000b1/state HTTP/1.1" 200 OK
2026-08-11T17:17:16.137Z
INFO: 203.0.113.15:0 - "GET /api/v1/subscription-tiers HTTP/1.1" 307 Temporary Redirect
2026-08-11T17:17:16.171Z
INFO: 203.0.113.15:0 - "OPTIONS /api/v1/subscription-tiers/ HTTP/1.1" 200 OK
2026-08-11T17:17:16.224Z
INFO: 203.0.113.15:0 - "GET /api/v1/subscription-tiers/ HTTP/1.1" 200 OK
2026-08-11T17:17:16.264Z
INFO: 203.0.113.33:0 - "POST /api/v1/webhooks/sms/telnyx-inbound HTTP/1.1" 200 OK
2026-08-11T17:17:16.804Z
INFO: 203.0.113.32:0 - "POST /api/v1/webhooks/sms/telnyx-inbound HTTP/1.1" 200 OK
