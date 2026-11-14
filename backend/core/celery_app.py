"""
Celery distributed task queue configuration.

This module configures the Celery app for background job processing with:
- Redis broker for local development
- SQS broker fallback for production (optional)
- Task autodiscovery from backend/tasks/
- Celery Beat scheduler for cron jobs
- Worker health monitoring

Design Reference: Task #12 - Celery Setup & Configuration
Gap Reference: Gap #21 in phase-1-4-implementation-gap-analysis.md

Usage:
    # Start worker
    celery -A core.celery_app worker --loglevel=info

    # Start beat scheduler
    celery -A core.celery_app beat --loglevel=info

    # Inspect registered tasks
    celery -A core.celery_app inspect registered
"""

from celery import Celery
from celery.schedules import crontab

from core.config import settings

celery_app = Celery(
    "pilot_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND or settings.CELERY_BROKER_URL,
)

# Configuration
celery_app.conf.update(
    # Broker settings
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
    # Result backend
    result_backend=settings.CELERY_RESULT_BACKEND or settings.CELERY_BROKER_URL,
    result_expires=3600,  # 1 hour
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # Autodiscovery - scan tasks/ directory
    imports=[
        "tasks.test_task",
        "tasks.cleanup_idempotency_keys",
        "tasks.profitability_rollup",
        "tasks.notification_worker",
        "tasks.cleanup_sessions",
        "tasks.quickbooks_token_refresh",
        "tasks.quickbooks_sync",
        "tasks.archive_audit_logs",
        "tasks.calendar_sync",  # Task 1-D-2: Google Calendar sync workers
        "tasks.system_template_notifier",  # A26: System template update notifications
        "tasks.quote_discount_expiry",  # A3: Expire time-limited quote discounts
        "tasks.voice_session_title",  # A11: Ollama-generated session titles (event-driven, no Beat entry)
        "tasks.voice_feedback_export",  # A6: Nightly voice feedback S3 export
        "tasks.notify_etc_variance_owners",  # B3/A16: ETC variance owner notifications
        "tasks.expire_stale_calendar_conflicts",  # B6/A34: Daily auto-expiry of stale calendar conflicts
        "tasks.photo_cleanup_tasks",  # B7b/A41: Weekly orphaned photo upload cleanup
        "tasks.voice_offline_tasks",  # B7b/A42: Offline voice capture processing
        "tasks.auto_expire_qb_conflicts",  # B8/A50: Daily auto-expiry of stale QB conflicts
        "tasks.monitor_sms_quota_thresholds",  # B11/A65: Hourly SMS quota threshold monitor
        "tasks.rollover_sms_quota_periods",  # B11/A65: Daily SMS quota period rollover
        "tasks.mfa_grace_reminders",  # B13/A68: Daily MFA grace period reminder notifications
        "tasks.data_export_pipeline",  # B13/A71: Event-driven data export pipeline
        "tasks.trial_management",  # B14/A73: Trial expiration enforcement
        "tasks.help_corpus",  # B16/A85+A84+A87+A88: Help corpus embedding, session title, feedback email, anonymization
        "tasks.saas_billing_aggregator",  # B19/FIND-101: SaaS metered feature usage aggregation (every 4 hours)
        "tasks.dunning",  # B19/FIND-069: Dunning reminders for overdue invoices (daily 09:00 UTC)
        "tasks.mobile_sync_cleanup",  # B19/FIND-088: Mobile sync event cleanup (daily 3 AM UTC)
        "tasks.quote_expiration_monitor",  # B19/FIND-096: Quote auto-expiry (daily 1 AM UTC)
        "tasks.check_system_template_updates",  # B19/FIND-099: System template update notifications (nightly 2 AM UTC)
        "tasks.recurring_jobs",  # B21: Recurring job generation (Beat: daily 06:00 UTC) + notification dispatch
        "tasks.receipt_ocr",  # B21/FIND-062/A96: Receipt OCR pipeline (event-driven, no Beat entry)
        "tasks.marketing_notifications",  # MKT-B6: Waitlist, contact, newsletter, application email confirmations (event-driven, no Beat entry)
        "tasks.sms_compliance",  # DLC-1: Double opt-in SMS dispatch (event-driven, no Beat entry)
        "tasks.sms_compliance_platform",  # SIGNUP-C: Platform (Pathway C) double opt-in SMS dispatch (event-driven, no Beat entry)
        "tasks.sms_platform_notifications",  # PLATFORM-SMS-B1: Pathway C account-notification SMS (event-driven, no Beat entry)
        "tasks.background_sync_push",  # MOB-B8/Background-Sync-B1: Silent push for background sync (Beat: every 60s)
        "tasks.free_period_notifications",  # C-B6: Free-period notification schedule (Beat: daily 09:00 UTC)
        "tasks.messaging_provisioning",  # C-B9: 10DLC provisioning (provision_brand, provision_campaign, check_otp_timeout)
        "tasks.messaging_recurring",  # C-B10: Recurring carrier fee pass-through (Beat: daily 09:30 UTC)
        "tasks.tenant_site_emails",  # C-B16: tenant-site requirement emails (event-driven, no Beat entry)
        "tasks.login_recording",  # PLP-FIX-10/INV-BUG-17: A72 session-history upsert on every login (event-driven, no Beat entry)
    ],
    # Beat schedule for periodic tasks
    beat_schedule={
        "cleanup-expired-idempotency-keys": {
            "task": "cleanup_expired_idempotency_keys",
            "schedule": crontab(hour=2, minute=0),  # 2 AM daily
        },
        "cleanup-old-failed-keys": {
            "task": "cleanup_old_failed_keys",
            "schedule": crontab(hour=2, minute=30),  # 2:30 AM daily
        },
        "poll-pending-notifications": {
            "task": "poll_pending_notifications",
            "schedule": 30.0,  # every 30 seconds
        },
        "expire-old-sessions": {
            "task": "expire_old_sessions",
            "schedule": crontab(hour=3, minute=0),  # 3:00 AM daily
        },
        "archive-old-sessions": {
            "task": "archive_old_sessions",
            "schedule": crontab(hour=3, minute=30),  # 3:30 AM daily
        },
        "cleanup-orphaned-messages": {
            "task": "cleanup_orphaned_messages",
            "schedule": crontab(hour=4, minute=0),  # 4:00 AM daily
        },
        "refresh-quickbooks-tokens": {
            "task": "refresh_quickbooks_tokens",
            "schedule": 1800.0,  # every 30 minutes (1800 seconds)
        },
        "sync-quickbooks-customers-all-tenants": {
            "task": "sync_all_tenants_customers",
            "schedule": crontab(minute="*/15"),  # every 15 minutes
        },
        "archive-audit-logs": {
            "task": "archive_audit_logs",
            "schedule": crontab(hour=1, minute=0),  # 1:00 AM daily
        },
        # Task 1-D-2: Google Calendar sync workers
        # push_job_to_calendar is triggered on-demand via .delay(); no Beat entry needed.
        "pull-calendar-blocks-all-tenants": {
            "task": "pull_calendar_blocks_all_tenants",
            "schedule": crontab(minute="*/15"),  # every 15 minutes
        },
        # A26: System template update notifications (daily at 6:00 AM UTC)
        "notify-system-template-updates": {
            "task": "notify_system_template_updates",
            "schedule": crontab(hour=6, minute=0),
        },
        # A3: Expire time-limited quote discounts (daily at 7:00 AM UTC)
        "expire-quote-discounts": {
            "task": "expire_quote_discounts",
            "schedule": crontab(hour=7, minute=0),
        },
        # A6: Nightly voice feedback S3 export for Llama fine-tuning (daily at 2:00 AM UTC)
        "export-voice-feedback-to-s3": {
            "task": "export_voice_feedback_to_s3",
            "schedule": crontab(hour=2, minute=0),
        },
        # B3/A16: ETC variance owner notifications — every 15 minutes
        "notify-etc-variance-owners-every-15min": {
            "task": "notify_etc_variance_owners",
            "schedule": crontab(minute="*/15"),
        },
        # B6/A34: Daily auto-expiry of stale calendar conflicts (02:00 UTC)
        "expire-stale-calendar-conflicts": {
            "task": "tasks.expire_stale_calendar_conflicts",
            "schedule": crontab(hour=2, minute=0),
        },
        # B7b/A41: Weekly cleanup of orphaned S3 multipart photo uploads (Sunday 04:00 UTC)
        "cleanup-incomplete-photo-uploads-weekly": {
            "task": "cleanup_incomplete_photo_uploads",
            "schedule": crontab(hour=4, minute=0, day_of_week=0),
        },
        # B7b/A42: Hourly expiry of deferred voice confirmations older than 24h
        "expire-pending-voice-confirmations": {
            "task": "expire_pending_voice_confirmations",
            "schedule": crontab(minute=0),  # every hour at :00
        },
        # B8/A50: Daily auto-expiry of stale QB sync conflicts (03:30 UTC)
        "auto-expire-qb-conflicts": {
            "task": "auto_expire_qb_conflicts_per_tenant",
            "schedule": crontab(hour=3, minute=30),  # 3:30 AM UTC
        },
        # B11/A65: Hourly SMS quota threshold monitor (detect 80%/100% crossings)
        "monitor-sms-quota-thresholds": {
            "task": "monitor_sms_quota_thresholds",
            "schedule": crontab(minute=0),  # every hour at :00
        },
        # B11/A65: Daily SMS quota period rollover (00:05 UTC — create next month's period)
        "rollover-sms-quota-periods": {
            "task": "rollover_sms_quota_periods",
            "schedule": crontab(hour=0, minute=5),  # 00:05 UTC daily
        },
        # B13/A68: Daily MFA grace period reminders (9 AM UTC)
        "notify-mfa-grace-period-reminders": {
            "task": "notify_mfa_grace_period_reminders",
            "schedule": crontab(hour=9, minute=0),  # 9 AM UTC daily
        },
        # B14/A73: Hourly trial expiration enforcement + warning dispatch
        "enforce-trial-expirations-hourly": {
            "task": "enforce_trial_expirations",
            "schedule": crontab(minute=0),  # top of every hour
        },
        # B16/A88: Daily anonymization of help sessions >= 90 days old (3 AM UTC)
        "anonymize-help-sessions-daily": {
            "task": "anonymize_help_sessions",
            "schedule": crontab(hour=3, minute=0),
        },
        # B16/A85: Weekly resync of all help articles (Sunday 2 AM UTC — catch S3 event misses)
        "process-help-articles-weekly-resync": {
            "task": "process_help_article",
            "schedule": crontab(hour=2, minute=0, day_of_week=0),
        },
        # B19/FIND-101: SaaS metered feature usage aggregation (every 4 hours: 00:00, 04:00, 08:00, etc UTC)
        "aggregate-metered-usage-every-4-hours": {
            "task": "saas_billing_aggregator",
            "schedule": crontab(minute=0, hour="*/4"),  # every 4 hours at :00
        },
        # B19/FIND-069 / SD-06B: Dunning reminders for overdue invoices (daily 09:00 UTC)
        "dunning-reminders-daily": {
            "task": "dunning_reminders",
            "schedule": crontab(hour=9, minute=0),  # once daily at 09:00 UTC
        },
        # B19/FIND-088: Mobile sync event cleanup (daily at 3:00 AM UTC)
        "archive-old-mobile-sync-events": {
            "task": "archive_old_mobile_sync_events",
            "schedule": crontab(hour=3, minute=0),  # 3:00 AM UTC daily
        },
        # B19/FIND-096: Quote auto-expiry (daily at 1:00 AM UTC)
        "quote-expiration-monitor": {
            "task": "quote_expiration_monitor",
            "schedule": crontab(hour=1, minute=0),  # 1:00 AM UTC daily
        },
        # B19/FIND-099: System template update notifications (nightly at 2:00 AM UTC)
        "check-system-template-updates": {
            "task": "check_system_template_updates",
            "schedule": crontab(hour=2, minute=0),  # 2:00 AM UTC daily
        },
        # MOB-B8/Background-Sync-B1: Scan all active push tokens and dispatch per-device silent push tasks
        "scan-background-sync-pushes": {
            "task": "tasks.background_sync_push.scan_and_dispatch_background_sync_pushes",
            "schedule": 60.0,  # every 60 seconds
        },
        # B21: Generate recurring job instances for due rules (daily at 06:00 UTC)
        "generate-due-recurring-jobs": {
            "task": "tasks.recurring_jobs.generate_due_recurring_jobs",
            "schedule": crontab(hour=6, minute=0),
        },
        # C-B6: Free-period notification schedule (daily at 09:00 UTC)
        "free-period-notifications-daily": {
            "task": "free_period_notifications",
            "schedule": crontab(hour=9, minute=0),  # 09:00 UTC daily
        },
        # C-B9: 10DLC OTP timeout check (hourly)
        "check-otp-timeout": {
            "task": "check_otp_timeout",
            "schedule": crontab(minute=0),  # hourly at :00
        },
        # C-B10: Recurring carrier fee pass-through (daily 09:30 UTC)
        "create-recurring-carrier-items-daily": {
            "task": "create_recurring_carrier_items",
            "schedule": crontab(hour=9, minute=30),  # 09:30 UTC daily
        },
    },
)

# Task autodiscovery is handled by the imports configuration above
# No need for explicit autodiscover_tasks() call since we're using imports=[]
