import os
import sys

# Ensure the backend directory is in the path so we can import from api
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from slowapi.errors import RateLimitExceeded
from sqlmodel import Session

from api.routes import (
    account_security,
    addresses,
    admin_tenants,
    audit,
    auth,
    billing_payment_contact,
    calendar_conflicts,
    calendar_integration,
    catalog,
    cohort_dashboard,
    communications,
    communications_threads,
    contacts,
    customers,
    dashboard,
    health,
    integrations,
    invoices,
    job_expense_categories,
    job_recurrence_rules,
    job_types,
    jobs,
    labor_rates,
    marketing,
    markups,
    messaging_provisioning,
    messaging_quote,
    mobile_push,
    mobile_push_permission,
    mobile_sync,
    notification_categories,
    notification_preferences,
    notification_sse,
    onboarding_checklist,
    operator_tenants,
    owner_escalations,
    payment_schedules,
    photos,
    public_charter,
    public_invoices,
    public_quotes,
    public_short_redirect,
    public_tenant_sites,
    qco_line_types,
    quote_templates,
    quotes,
    reports,
    roles,
    scheduling,
    signup,
    sites,
    sms_quota,
    stripe_connect,
    subscription_tiers,
    sync_status,
    team_invites,
    tenant_10dlc_profile,
    tenant_email_branding,
    tenant_phone_numbers,
    tenant_site,
    tenant_subscription,
    user_color,
    user_preferences,
    user_profile,
    voice,
    voice_feedback,
    voice_persona,
    voice_sessions,
    webhooks,
    webhooks_sms,
    webhooks_stripe,
)
from api.routes import nec as nec_routes
from api.routes import settings as settings_routes
from api.routes.help import (
    admin_help_router,
    feedback_router,
)
from api.routes.help import (
    router as help_router,
)
from api.routes.integrations import sync_dashboard_router
from app.models.system import AuditEvent
from core.config import settings as _settings
from core.datetime_utils import safe_now_utc
from core.db import engine
from core.idempotency import idempotency_middleware
from core.middleware import RequestIDMiddleware
from core.rate_limit import limiter, rate_limit_error_handler

# /docs, /redoc, and /openapi.json are disabled in production.
# They remain enabled in dev and qa for internal developer testing.
_is_production = _settings.ENVIRONMENT == "production"
app = FastAPI(
    title="Pilot for Trades API",
    docs_url=None if _is_production else "/docs",
    redoc_url=None if _is_production else "/redoc",
    openapi_url=None if _is_production else "/openapi.json",
)

# Add rate limiter to app state (required by Slowapi)
app.state.limiter = limiter

# Register rate limit exception handler (RFC 7807 format)
app.add_exception_handler(RateLimitExceeded, rate_limit_error_handler)

# Add middleware (order matters: RequestID first, then Idempotency)
app.add_middleware(RequestIDMiddleware)
app.middleware("http")(idempotency_middleware)

app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["webhooks"])
app.include_router(
    webhooks_sms.router,
    prefix="/api/v1/webhooks",
    tags=["webhooks"],
)  # B11/A59: Telnyx inbound SMS webhook receiver (public, signature-verified)
app.include_router(
    webhooks_stripe.router,
    prefix="/api/v1/webhooks",
    tags=["webhooks"],
)  # B14/A76: Stripe webhook handler (public, signature-verified, dedup via stripe_webhook_event_processed)
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(health.router, prefix="/api/v1", tags=["health"])  # Task #12
app.include_router(audit.router, prefix="/api/v1", tags=["audit"])  # Task #20
app.include_router(customers.router, prefix="/api/v1/customers", tags=["customers"])
app.include_router(sites.router, prefix="/api/v1/sites", tags=["sites"])
app.include_router(
    contacts.router, prefix="/api/v1/contacts", tags=["contacts"]
)  # Gap #6, #8
app.include_router(
    addresses.router, prefix="/api/v1/addresses", tags=["addresses"]
)  # Gap #6, #7
app.include_router(catalog.router, prefix="/api/v1/catalog", tags=["catalog"])
app.include_router(
    job_expense_categories.router,
    prefix="/api/v1/job-expense-categories",
    tags=["job-expense-categories"],
)  # B17/A8: Job expense category lookup (mobile dynamic categories)
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["jobs"])
app.include_router(
    job_types.router, prefix="/api/v1/job-types", tags=["job-types"]
)  # CLASS-B1: Job type lookup (platform defaults + tenant overrides, read-only)
app.include_router(
    job_recurrence_rules.router,
    prefix="/api/v1/job-recurrence-rules",
    tags=["job-recurrence-rules"],
)  # B21: Recurring job rule CRUD — creates first job on POST, Beat task handles subsequent
app.include_router(invoices.router, prefix="/api/v1/invoices", tags=["invoices"])
app.include_router(
    payment_schedules.router,
    prefix="/api/v1/payment-schedules",
    tags=["payment-schedules"],
)  # BILLING-B1: Progress billing schedule orchestration (9 endpoints + /test twins)
app.include_router(quotes.router, prefix="/api/v1/quotes", tags=["quotes"])
app.include_router(
    qco_line_types.router,
    prefix="/api/v1/qco-line-types",
    tags=["quotes"],
)  # PLP-FIX-2: QCO line-type lookup (platform defaults + tenant overrides, read-only)
app.include_router(
    quote_templates.router,
    prefix="/api/v1/quote-templates",
    tags=["quote-templates"],
)  # A25: Quote Template CRUD, fork, disable, from-template
app.include_router(voice.router, prefix="/api/v1/voice", tags=["voice"])
app.include_router(
    voice_sessions.router, prefix="/api/v1/voice/sessions", tags=["voice"]
)  # A9, A12: Session listing and message retrieval
app.include_router(
    voice_feedback.router, prefix="/api/v1/voice", tags=["voice"]
)  # A6: Voice AI feedback loop (POST/GET feedback, GET transcripts)
app.include_router(
    user_preferences.router, prefix="/api/v1/users", tags=["users"]
)  # A7: Field mode preference endpoint (PATCH/GET /users/me/preferences)
app.include_router(
    user_color.router, prefix="/api/v1/users", tags=["users"]
)  # B3/A18: Tech display color PATCH endpoint
app.include_router(
    user_profile.router, prefix="/api/v1/users", tags=["users"]
)  # FIND-066 (B20, Task 11): User profile PATCH endpoint + SMS MFA invalidation
app.include_router(
    account_security.router, prefix="/api/v1/users", tags=["account-security"]
)  # B13: Session history, MFA status/enrollment, session revoke, data exports
app.include_router(
    integrations.router, prefix="/api/v1", tags=["integrations"]
)  # Task #16
app.include_router(
    sync_dashboard_router, prefix="/api/v1", tags=["integrations"]
)  # Task 1-E-4: QB Sync Conflict Notification Wiring
app.include_router(roles.router)  # Task #21: RBAC role management
app.include_router(
    team_invites.router
)  # TEAM-INVITE-1: Team invite CRUD + public token validation
app.include_router(
    admin_tenants.router,
    prefix="/api/v1/admin/tenants",
    tags=["admin-tenants"],
)  # Task 1-E-1: Admin Tenant Feature Override API
app.include_router(
    scheduling.router,
    prefix="/api/v1/scheduling",
    tags=["scheduling"],
)  # Task 1-B-1: Tech Availability CRUD
app.include_router(
    calendar_integration.router,
    prefix="/api/v1",
    tags=["integrations"],
)  # Task 1-D-1: Google Calendar OAuth Flow
app.include_router(
    calendar_conflicts.router,
    prefix="/api/v1",
    tags=["integrations"],
)  # B6/A32-A33: Calendar Conflict Resolution (list, detail, resolve)
app.include_router(
    communications.router,
    prefix="/api/v1/communications",
    tags=["communications"],
)  # B4/A4/A21/A23: Templated customer comms send + preview endpoints
app.include_router(
    communications.customers_router,
    prefix="/api/v1/customers",
    tags=["communications"],
)  # B4/A8: Customer communication history endpoint
app.include_router(
    reports.router,
    prefix="/api/v1/reports",
    tags=["reports"],
)  # B5/A5: 6 report endpoints (profitability, revenue, ar-aging, tech-productivity, tax-liability, voice-analytics)
app.include_router(
    dashboard.router,
    prefix="/api/v1/dashboard",
    tags=["dashboard"],
)  # B5/A5: Dashboard widget CRUD (list, create, update, delete)
app.include_router(
    mobile_sync.router,
    prefix="/api/v1/mobile-sync",
    tags=["mobile-sync"],
)  # B7a/A38: Sync queue state endpoint (owner/admin view of tech sync state)
app.include_router(
    photos.router,
    prefix="/api/v1/photos",
    tags=["photos"],
)  # B7b/A41: Resumable photo upload pipeline (S3 multipart)
app.include_router(
    owner_escalations.router,
    prefix="/api/v1/owner",
    tags=["owner-escalations"],
)  # B7b/A46: Owner escalation routing for mobile sync conflicts
app.include_router(
    mobile_push.router,
    prefix="/api/v1/mobile",
    tags=["mobile"],
)  # B8/A51: Push token registry + sync session telemetry
app.include_router(
    mobile_push_permission.router,
    prefix="/api/v1/users",
    tags=["mobile"],
)  # B14/A78: Mobile push permission state (PUT/GET per device)
app.include_router(
    settings_routes.router,
    prefix="/api/v1/settings",
    tags=["settings"],
)  # B9/A52-A55: Settings catalog, effective-value resolver, tenant writes, user overrides
app.include_router(
    markups.router,
    prefix="/api/v1/settings",
    tags=["settings"],
)  # B20/A90: Category-specific markup management (temporal versioning)
app.include_router(
    labor_rates.router,
    prefix="/api/v1/settings",
    tags=["settings"],
)  # B20/A91: Labor rate version management (temporal versioning by skill level)
app.include_router(
    tenant_10dlc_profile.router,
    prefix="/api/v1/settings",
    tags=["settings"],
)  # DLC-1: 10DLC business profile GET/PUT (single-row-per-tenant upsert)
app.include_router(
    tenant_site.router,
    prefix="/api/v1/tenant-site",
    tags=["settings"],
)  # C-B16: Tenant-hosted compliance site config (5 endpoints + /test twins)
app.include_router(
    notification_categories.router,
    prefix="/api/v1/notifications",
    tags=["notifications"],
)  # B10/A56: Notification category registry + sub-trigger endpoints
app.include_router(
    notification_preferences.router,
    prefix="/api/v1/notifications",
    tags=["notifications"],
)  # B10/A57: Preference matrix endpoints + tenant policy endpoints
app.include_router(
    notification_sse.router,
    prefix="/api/v1/notifications",
    tags=["notifications"],
)  # B10/A57: SSE stream + in-app mark-read + recent bell panel
app.include_router(
    tenant_phone_numbers.router,
    prefix="/api/v1/tenants/{tenant_id}/phone-numbers",
    tags=["sms"],
)  # B11/A61: Telnyx phone number provisioning + listing for a tenant
app.include_router(
    messaging_quote.router,
    prefix="/api/v1/tenants/{tenant_id}",
    tags=["sms"],
)  # C-B8: 10DLC carrier cost quote (reads carrier_fee_schedule config table)
app.include_router(
    messaging_provisioning.router,
    prefix="/api/v1/tenants/{tenant_id}",
    tags=["sms"],
)  # C-B9: 10DLC provisioning state machine (8 endpoints + /test twins)
app.include_router(
    communications_threads.router,
    prefix="/api/v1/communications",
    tags=["communications"],
)  # B11/A60+A62+A66: Thread routing, unrouted queue, reply, inbox, mark-read
app.include_router(
    sms_quota.router,
    prefix="/api/v1/sms/quota",
    tags=["sms"],
)  # B11/A65: SMS quota status endpoint
app.include_router(
    voice_persona.router,
    prefix="/api/v1/settings",
    tags=["settings"],
)  # B12/A67: Voice persona tone endpoints (7 endpoints: user+tenant CRUD + meta-toggle)
app.include_router(
    onboarding_checklist.router,
    prefix="/api/v1/tenants",
    tags=["onboarding"],
)  # B14/A77: Onboarding checklist widget state + skip/hide/dismiss
app.include_router(
    signup.router,
    prefix="/api/v1/signup",
    tags=["signup"],
)  # B14/A73: Tenant signup wizard (steps 1-5) + state resumability
app.include_router(
    subscription_tiers.router,
    prefix="/api/v1/subscription-tiers",
    tags=["subscription"],
)  # B14/A75: Subscription tier catalogue (GET active tiers)
app.include_router(
    tenant_subscription.router,
    prefix="/api/v1/tenants",
    tags=["subscription"],
)  # B14/A75: Tenant subscription state + upgrade endpoint
app.include_router(
    sync_status.router,
    prefix="/api/v1/sync",
    tags=["sync"],
)  # B15/A79: Unified sync surface pending-count exposure (calendar | quickbooks | mobile_data | background)
app.include_router(
    tenant_email_branding.router,
    prefix="/api/v1/settings/email-branding",
    tags=["settings"],
)  # B15/A82: Email branding CRUD, logo upload presign, preview, test-send
app.include_router(
    public_quotes.router,
    prefix="/api/v1/public",
    tags=["public"],
)  # B15/A80: Public quote view, accept, decline endpoints (no JWT)
app.include_router(
    public_invoices.router,
    prefix="/api/v1/public",
    tags=["public"],
)  # B15/A80+A81: Public invoice view, payment-intent, confirm-payment (no JWT)
app.include_router(
    public_charter.router,
    prefix="/api/v1/public",
    tags=["public"],
)  # C-B13: Public Charter availability endpoint (no JWT)
app.include_router(
    public_tenant_sites.router,
    prefix="/api/v1/public/tenant-sites",
    tags=["public"],
)  # C-B16: Public tenant site SSR endpoint (no JWT, SlowAPI 60/min, Redis cache)
app.include_router(
    public_short_redirect.router,
    prefix="/api/v1/short",
    tags=["public"],
)  # B15/A80: Short-code redirect → full signed URL
app.include_router(
    help_router,
    prefix="/api/v1/help",
    tags=["help"],
)  # B16/A85+A84+A86: Help article delivery, RAG retrieval, chat sessions, context payload
app.include_router(
    feedback_router,
    prefix="/api/v1/feedback",
    tags=["help"],
)  # B16/A87: User feedback submission → support email via SendGrid
app.include_router(
    admin_help_router,
    prefix="/api/v1/admin",
    tags=["admin"],
)  # B16/A85: Admin trigger to re-embed a single help article


app.include_router(
    cohort_dashboard.router,
)  # C-B11: Operator cohort dashboard (platform-level, prefix=/api/v1/operator)

app.include_router(
    operator_tenants.router,
)  # C-B15: Operator tenant list + impersonation start/end (platform-level, prefix=/api/v1/operator)

app.include_router(
    nec_routes.router,
    prefix="/api/v1/nec",
    tags=["nec"],
)  # MOB-B0: NEC 2023 calculation engine — voltage drop, conduit fill, ampacity

app.include_router(
    marketing.router,
    prefix="/api/v1/marketing",
    tags=["marketing"],
)  # MKT-B1-BE: Public waitlist signup (no auth, Turnstile + rate limit)

app.include_router(
    stripe_connect.router,
    prefix="/api/v1/settings/billing",
    tags=["settings"],
)  # UI-FIX-2F: Stripe Connect Account Links — connect/status/disconnect tenant Stripe account
app.include_router(
    billing_payment_contact.router,
    prefix="/api/v1/settings/billing",
    tags=["settings"],
)  # STRIPE-CONNECT-1-B2: billing payment-contact (phone + email) for the public invoice manual-payment panel

# CORS allowed origins — separated by environment so localhost origins
# are never permitted in staging or production.
_PRODUCTION_ORIGINS = [
    # Web app (pilot-web, ECS Fargate behind the ALB)
    "https://app.pilotfortrades.com",
    # Marketing site (CloudFront / S3)
    "https://pilotfortrades.com",
    "https://www.pilotfortrades.com",
]

_DEV_ORIGINS = [
    # Web app (Next.js dev server, Vite)
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    # Mobile / Expo
    "http://localhost:8081",
    "http://localhost:8082",
    "http://127.0.0.1:8081",
    "http://127.0.0.1:8082",
    # Marketing site local dev (port 3001)
    "http://localhost:3001",
    "http://127.0.0.1:3001",
]

if _settings.ENVIRONMENT in ("staging", "production"):
    origins = _PRODUCTION_ORIGINS
else:
    # dev / qa: allow all localhost origins + production origins so that
    # QA can run against the dev backend while the production-spec site is also up.
    origins = _DEV_ORIGINS + _PRODUCTION_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# C-B15 — Impersonated-mutation audit middleware.
# After the call, if request.state.impersonator_user_id is set AND the method
# is a mutation (POST/PATCH/PUT/DELETE), write one audit.event row with
# action='request'.  Failure to write must never break the request.
_impersonation_logger = logging.getLogger("pilot.impersonation_audit")


@app.middleware("http")
async def impersonation_audit_middleware(request: Request, call_next):
    """Audit-log every mutation performed under tenant impersonation (C-B15)."""
    response = await call_next(request)
    try:
        impersonator_user_id = getattr(request.state, "impersonator_user_id", None)
        if impersonator_user_id is not None and request.method not in (
            "GET",
            "HEAD",
            "OPTIONS",
        ):
            tenant_id = getattr(request.state, "tenant_id", None)
            with Session(engine) as session:
                event = AuditEvent(
                    occurred_at=safe_now_utc(),
                    tenant_id=tenant_id,
                    user_id=impersonator_user_id,
                    actor_type="platform",
                    entity_name="impersonation",
                    entity_id=str(tenant_id) if tenant_id else "",
                    action="request",
                    contextdata={
                        "method": request.method,
                        "path": request.url.path,
                    },
                )
                session.add(event)
                session.commit()
    except Exception:
        _impersonation_logger.exception(
            "Failed to write impersonation audit event for %s %s",
            request.method,
            request.url.path,
        )
    return response


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    # Serve the product favicon from the marketing site (no third-party icon)
    icon_url = "https://pilotfortrades.com/brand/logo-icon.png"
    return RedirectResponse(url=icon_url)


@app.get("/")
async def root():
    return {"message": "Pilot for Trades API is online", "status": "healthy"}


@app.get("/api/v1/hello")
async def hello_aeveofab():
    return {"greeting": "Hello from the FastAPI backend!"}
