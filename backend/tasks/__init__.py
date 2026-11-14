"""
Background tasks for Pilot for Trades.

This package contains Celery tasks for asynchronous processing:
- cleanup_idempotency_keys: Cleanup expired idempotency keys (Task #12)
- test_task: Simple test task for verification (Task #12)
- login_recording: A72 session-history upsert on every login (PLP-FIX-10/INV-BUG-17)

Future tasks:
- profitability_rollup: Calculate job profitability (Task #13)
- notification_outbox: Send email/SMS notifications (Task #14)
- session_expiration: Archive old conversation sessions (Task #15)

Task Reference: Task #12 - Celery Setup & Configuration
"""
