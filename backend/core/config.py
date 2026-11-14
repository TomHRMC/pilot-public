from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Celery Configuration (Task #12 - Gap #21)
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str | None = (
        None  # Optional result backend (default: same as broker)
    )

    # Production SQS fallback (optional, for future use)
    CELERY_BROKER_USE_SQS: bool = False
    AWS_SQS_REGION: str = "us-east-1"

    # Worker settings
    CELERY_WORKER_CONCURRENCY: int = 2  # CPU-bound tasks
    CELERY_WORKER_PREFETCH_MULTIPLIER: int = 4

    API_BASE_URL: str = "http://localhost:8000"
    COGNITO_REGION: str = "us-east-1"
    COGNITO_USER_POOL_ID: str = ""

    # QuickBooks OAuth 2.0 Configuration (Task #16 - Gap #22)
    QUICKBOOKS_CLIENT_ID: str = ""
    QUICKBOOKS_CLIENT_SECRET: str = ""
    QUICKBOOKS_REDIRECT_URI: str = "https://your-tunnel.ngrok-free.dev/api/v1/integrations/quickbooks/callback"
    QUICKBOOKS_ENVIRONMENT: Literal["sandbox", "production"] = "sandbox"
    QUICKBOOKS_AUTH_URL: str = "https://appcenter.intuit.com/connect/oauth2"
    QUICKBOOKS_TOKEN_URL: str = (
        "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
    )
    QUICKBOOKS_REVOKE_URL: str = (
        "https://developer.api.intuit.com/v2/oauth2/tokens/revoke"
    )
    QUICKBOOKS_BASE_URL: str = (
        "https://sandbox-quickbooks.api.intuit.com"  # sandbox by default
    )

    # QuickBooks Webhook Configuration (Task #19 - Gap #27)
    QUICKBOOKS_WEBHOOK_VERIFIER_TOKEN: str = (
        ""  # HMAC-SHA256 verifier token from Intuit Developer Portal
    )

    # Token encryption (Fernet: AES-128-CBC + HMAC-SHA256) - Task #16
    ENCRYPTION_KEY: str = ""  # 32 URL-safe base64-encoded bytes

    WHISPER_API_URL: str = "http://localhost:8080/v1"
    WHISPER_MODEL: str = "base"
    OLLAMA_API_URL: str = "http://localhost:11434/api"
    OLLAMA_CHAT_MODEL: str = "llama3.1:8b"
    OLLAMA_EMBED_MODEL: str = "mxbai-embed-large"

    # Test endpoint configuration (Gap #28)
    TEST_ENDPOINT_ENABLED: bool = False  # Default: disabled for production safety
    ENVIRONMENT: Literal["dev", "qa", "staging", "production"] = "dev"
    TEST_TENANT_ID: str = "00000000-0000-0000-0000-000000000001"
    TEST_USER_ID: str = "00000000-0000-0000-0000-000000000002"

    # Notification Configuration (Task #14 - Gap #26)
    SENDGRID_API_KEY: str = ""
    SENDGRID_FROM_EMAIL: str = "noreply@pilotfortrades.com"
    SENDGRID_FROM_NAME: str = "Pilot for Trades"

    # B11/A59: SMS carrier selection and Telnyx configuration
    # NOTE: Twilio removed in DLC-B2 — Pathway B uses Telnyx (see telnyx_sms_carrier.py)
    SMS_CARRIER: str = "mock"  # "telnyx" | "mock" (default: mock for local dev)
    DATA_EXPORT_S3_BUCKET: str = (
        "pilot-data-exports-dev"  # B13/A71: S3 bucket for data exports
    )
    TELNYX_API_KEY: str = ""  # Telnyx API key (set in .env for telnyx carrier)
    TELNYX_PUBLIC_KEY: str = ""  # Telnyx webhook public key for signature verification
    TELNYX_MESSAGING_PROFILE_ID: str = (
        ""  # B21/FIND-173: Telnyx messaging profile ID for sandbox testing
    )
    TELNYX_SANDBOX_FROM_NUMBER: str = (
        ""  # B21/FIND-173: Telnyx sandbox FROM number for integration tests (+E.164)
    )
    TELNYX_SANDBOX_TO_NUMBER: str = (
        ""  # B21/FIND-173: Telnyx sandbox TO number for integration tests (+E.164)
    )
    # TELNYX-INT-1: When True, 10DLC brand/campaign creation uses Telnyx mock
    # objects ($0 — no TCR fees, no SMS traffic). Enables free real-API
    # provisioning-flow + webhook integration tests. See 10DLC playbook §14.
    TELNYX_10DLC_MOCK: bool = False
    # MFA-WIRE-1: Mock↔real Cognito MFA client toggle. DEFAULT TRUE (mock) —
    # fail-safe: real Cognito MFA calls happen only where the env explicitly
    # sets MFA_COGNITO_MOCK=false (prod task definition). Dev pool has MFA
    # disabled, so real enrollment cannot work outside prod (design §G-Q6).
    MFA_COGNITO_MOCK: bool = True
    # SIGNUP-C / Pathway C: Pilot's ONE shared platform-sender number for
    # Pilot→owner notifications (account, billing & security alerts). NOT a
    # per-tenant TenantPhoneNumber row. Stored in Secrets Manager
    # (pilot/prod/telnyx) in production; set in .env for local dev/tests.
    PILOT_PLATFORM_SMS_NUMBER: str = ""

    # B20/A93: Expo Push Notifications API access token
    EXPO_ACCESS_TOKEN: str = ""  # Expo Dashboard → Access Tokens → set in .env for prod

    # Notification retry configuration
    NOTIFICATION_MAX_RETRIES: int = 5
    NOTIFICATION_RETRY_DELAYS: list[int] = [60, 300, 900, 3600, 21600]

    # Map Provider Configuration (Task 1-C-1)
    MAP_PROVIDER: str = "mock"  # "google" | "mock"
    GOOGLE_MAPS_API_KEY: str = ""
    GOOGLE_MAPS_API_URL: str = (
        "https://maps.googleapis.com/maps/api/distancematrix/json"
    )
    MAP_HTTP_TIMEOUT_SECONDS: float = 5.0
    MAP_MOCK_FALLBACK_MINUTES: int = 20  # Used when address has no lat/lon

    # B3/A20: Drive-time Redis cache settings
    MAP_CACHE_TTL_SECONDS: int = 86400  # 24 hours per design doc
    MAP_CACHE_ENABLED: bool = (
        False  # Default OFF — must explicitly enable in production .env
    )
    REDIS_URL: str = "redis://localhost:6379/0"  # Sync Redis URL for map cache

    # C-B16: Tenant-hosted compliance sites base domain.
    # Dev: localhost:3000 (wildcard *.localhost resolves on macOS).
    # Prod: the registered domain (e.g. p4tsites.com).
    TENANT_SITES_BASE_DOMAIN: str = "localhost:3000"

    # Google Calendar OAuth 2.0 Configuration (Task 1-D-1)
    GOOGLE_CALENDAR_CLIENT_ID: str = ""
    GOOGLE_CALENDAR_CLIENT_SECRET: str = ""
    GOOGLE_CALENDAR_REDIRECT_URI: str = (
        "http://localhost:8000/api/v1/integrations/calendar/callback"
    )
    GOOGLE_CALENDAR_AUTH_URL: str = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_CALENDAR_TOKEN_URL: str = "https://oauth2.googleapis.com/token"
    # OAuth state token validity window (seconds)
    CALENDAR_OAUTH_STATE_TTL_SECONDS: int = 600  # 10 minutes

    # B14/A76: Stripe configuration
    STRIPE_SECRET_KEY: str = ""  # sk_test_... or sk_live_...
    STRIPE_WEBHOOK_SECRET: str = ""  # whsec_... from Stripe Dashboard → Webhooks
    STRIPE_BASE_URL: str = (
        "https://api.stripe.com"  # Override to http://stripe-mock:12111 in tests
    )
    # STRIPE-CONNECT-1 (A7): Connect platform key + Connect webhook secret.
    # The platform key is used for Connect API calls (Account.create, Account.retrieve,
    # PaymentIntent with stripe_account=). Falls back to STRIPE_SECRET_KEY in dev
    # (getattr fallback in stripe_connect.py / webhooks_stripe.py).
    # The Connect webhook secret is from the Connect endpoint registration in
    # Stripe Dashboard (separate from the platform endpoint's STRIPE_WEBHOOK_SECRET).
    STRIPE_CONNECT_PLATFORM_KEY: str = ""  # sk_test_... or sk_live_... (Connect)
    STRIPE_CONNECT_WEBHOOK_SECRET: str = ""  # whsec_... from Connect webhook endpoint

    # B7b/A41: S3 Photo Upload Configuration
    S3_BUCKET_NAME: str = (
        ""  # General-purpose bucket (email branding, logos, invoices) — set in .env
    )
    AWS_S3_PHOTOS_BUCKET_NAME: str = ""  # Set in .env for dev/prod
    AWS_S3_REGION: str = "us-east-1"
    AWS_S3_MULTIPART_CHUNK_SIZE_BYTES: int = 5_242_880  # 5 MB (S3 minimum)
    AWS_S3_PRESIGNED_URL_EXPIRY_SECONDS: int = 3600  # 1 hour

    # B19/FIND-165: Audit log S3 archive configuration
    AUDIT_ARCHIVE_S3_BUCKET: str = (
        "pilot-audit-archive"  # S3 bucket for audit event exports
    )

    # B16/A85: Help corpus S3 bucket and OpenAI embedding API
    HELP_CONTENT_BUCKET: str = ""  # e.g. "pilot-help-content" — set in .env for prod
    OPENAI_API_KEY: str = ""  # text-embedding-3-small for help corpus embedding

    # B16/A87: Support feedback email address
    SUPPORT_EMAIL_ADDRESS: str = "support@pilotfortrades.com"

    # MKT-B6: Per-form notification routing
    # Each marketing form routes admin notifications to its own inbox.
    # SUPPORT_EMAIL_ADDRESS above is retained for the help system (help_corpus.py).
    NEWSLETTER_EMAIL_ADDR: str = "newsletter@pilotfortrades.com"
    SALES_EMAIL_ADDR: str = "sales@pilotfortrades.com"
    CONTACT_US_EMAIL_ADDR: str = "info@pilotfortrades.com"
    CAREERS_EMAIL_ADDR: str = "careers@pilotfortrades.com"

    # Comma-separated list of open role titles for the careers form dropdown.
    # Update this value in .env without a code deploy to change what roles appear.
    CAREERS_OPEN_ROLES: str = "Example Role A,Example Role B"

    # MKT-B1-BE: Cloudflare Turnstile bot-protection secret key (server-side only)
    # Dev/test: use Cloudflare always-passes test secret (no real account needed)
    # Production: obtain from Cloudflare Dashboard → Turnstile → site secret key
    CLOUDFLARE_TURNSTILE_SECRET_KEY: str = "1x0000000000000000000000000000000AA"

    # MKT-B1.5-BE: Newsletter one-click unsubscribe HMAC secret (32+ random chars)
    # Production: generate with `python -c "import secrets; print(secrets.token_hex(32))"`
    NEWSLETTER_UNSUBSCRIBE_SECRET: str = (
        "dev-newsletter-unsub-secret-CHANGE-IN-PRODUCTION"
    )

    # MKT-B1.5-BE: Marketing site base URL (for unsubscribe link generation)
    MARKETING_SITE_BASE_URL: str = "http://localhost:3001"

    # TEAM-INVITE-1: Web app base URL for invite link construction.
    # Used by team_invite_service._get_web_app_base_url() and integrations.py
    # (QuickBooks callback redirect). Must be set to the production web app URL
    # (e.g. https://app.pilotfortrades.com) in the production .env / task definition.
    FRONTEND_URL: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()


def is_test_endpoint_allowed() -> bool:
    """
    Check if test endpoints are allowed in current environment.

    FIND-001-049 (ARCH-§7.2): Uses an ALLOWLIST pattern — only 'dev' and 'qa'
    are permitted. Any other environment value (including unknown future names)
    is hard-blocked automatically.

    Test endpoints are only available when BOTH conditions are true:
    1. TEST_ENDPOINT_ENABLED environment variable is set to 'true', AND
    2. ENVIRONMENT is exactly 'dev' or 'qa' (allowlist, not a blocklist)

    Returns:
        True if test endpoints should be accessible, False otherwise

    Security:
        Allowlist pattern ensures unrecognized environment names fail closed.
        Defaults to False (TEST_ENDPOINT_ENABLED=False) for deployment safety.
    """
    return settings.TEST_ENDPOINT_ENABLED and settings.ENVIRONMENT in ["dev", "qa"]
