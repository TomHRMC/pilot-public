"""
_env_profiles.py — Environment-aware seed profile registry (DB-MGMT-1, ADR-0016).

Implements design §F.1: every seed script resolves its target environment via
``--env`` / ``SEED_ENV`` (precedence: flag > env var > default ``dev``), obtains
an :class:`EnvProfile`, and enforces fail-closed guards before any DB work.

Binding contracts (batch-db-mgmt-1-design.md §B.4 / §F.1 / §G):

* ``--env`` is **decoupled** from pydantic ``settings.ENVIRONMENT`` (§G-1).
  Seed scripts never read or assign ``settings.ENVIRONMENT`` — its Literal
  rejects ``e2e`` (``core/config.py`` line 57).
* prod = Groups A+B only; Group C/D scripts invoked with ``--env prod`` exit
  non-zero (§B.4).
* ``--env prod`` **requires** ``--stripe-mode {test|live}`` — no default,
  fail-closed (§G-2). ``--stripe-mode live`` with non-prod is rejected.
* Bidirectional host guard (§E-3): non-prod refuses RDS hosts; prod refuses
  the localhost dev DB and accepts only RDS or ``localhost:5433`` (tunnel).

Rollout order (per Tom, 2026-08-18): dev first → verify → prod → e2e.
QA is a placeholder (no QA env yet — design §G-4: "a data profile, not a
location"); its profile is wired but unverified until a QA target exists.

This module is pure logic + subprocess preflight — it never opens a DB
connection. ``assert_target_compatible`` runs BEFORE any connection opens.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import urlparse

# ── Enums ────────────────────────────────────────────────────────────────────


class SeedEnv(StrEnum):
    """Target environment for seed scripts (decoupled from pydantic ENVIRONMENT)."""

    DEV = "dev"
    E2E = "e2e"
    QA = "qa"
    PROD = "prod"


class StripeMode(StrEnum):
    """Stripe key/price mode for env-aware seeding."""

    TEST = "test"
    LIVE = "live"


# ── Stripe price-ID registry ─────────────────────────────────────────────────
# Authoritative source: backend/scripts/stripe_ids.{test,live}.json (emitted by
# stripe_bootstrap.py; the runtime loads these same files via core/stripe_config.py).
# Human reference: dev-docs/integrations/stripe/stripe-pricing-config.md §4.
# Charter = monthly price on prod_starter (not a separate product); annual=None
# both modes. The original test charter ``price_REDACTED09`` was
# superseded by the 2026-08-08 test bootstrap re-run; mode classified 2026-08-18
# (DB-MGMT-1 follow-up closed) — prod converge may now include the charter row.
# ``None`` = no Stripe price for this tier/interval (trial, charter-annual).

_STRIPE_PRICE_IDS_TEST: Mapping[str, dict[str, str | None]] = {
    "charter": {"monthly": "price_REDACTED15", "annual": None},
    "trial": {"monthly": None, "annual": None},
    "starter": {
        "monthly": "price_REDACTED16",
        "annual": "price_REDACTED17",
    },
    "teams": {
        "monthly": "price_REDACTED19",
        "annual": "price_REDACTED18",
    },
}

_STRIPE_PRICE_IDS_LIVE: Mapping[str, dict[str, str | None]] = {
    "charter": {"monthly": "price_REDACTED11", "annual": None},
    "trial": {"monthly": None, "annual": None},
    "starter": {
        "monthly": "price_REDACTED01",
        "annual": "price_REDACTED05",
    },
    "teams": {
        "monthly": "price_REDACTED02",
        "annual": "price_REDACTED06",
    },
}

# Tiers whose price IDs are safe to converge in prod. Charter re-admitted
# 2026-08-18 — its price-ID mode is classified (DB-MGMT-1 follow-up closed) and
# the registry mirrors stripe_ids.{test,live}.json. Trial stays excluded:
# NULL/NULL (no Stripe price) — nothing to converge.
_CONVERGEABLE_TIERS = ("charter", "starter", "teams")

# ── Vendor posture matrix (design §B.3) ───────────────────────────────────────
# Machine-readable source of truth; the seed banner prints it on every run.
# Stripe is the only actively enforced preflight (verify_stripe_key_alignment).

_VENDOR_POSTURE_DEV: Mapping[str, str] = {
    "quickbooks": "sandbox",
    "cognito": "dev-pool",
    "sendgrid": "shared",
    "telnyx": "mock",
    "stripe": "test",
}

_VENDOR_POSTURE_E2E: Mapping[str, str] = {
    "quickbooks": "mocked",
    "cognito": "mocked",
    "sendgrid": "mocked",
    "telnyx": "mock",
    "stripe": "test",
}

# QA placeholder — no QA env exists yet (design §G-4). Values reflect the
# Phase 2 target posture; unverified until a QA target is provisioned.
_VENDOR_POSTURE_QA: Mapping[str, str] = {
    "quickbooks": "sandbox",
    "cognito": "qa-pool",
    "sendgrid": "shared",
    "telnyx": "real",
    "stripe": "test",
}

_VENDOR_POSTURE_PROD: Mapping[str, str] = {
    "quickbooks": "sandbox",
    "cognito": "prod-pool",
    "sendgrid": "shared",
    "telnyx": "real",
    "stripe": "test",  # Phase 1: test mode (sk_test_ keys in pilot/prod/stripe)
}


# ── EnvProfile ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class EnvProfile:
    """Resolved environment profile for a seed run (design §F.1)."""

    env: SeedEnv
    allowed_groups: frozenset[str]
    stripe_mode: StripeMode | None
    stripe_price_ids: Mapping[str, dict[str, str | None]]
    allowed_db_host_patterns: tuple[str, ...]
    forbidden_db_host_patterns: tuple[str, ...]
    require_typed_confirmation: bool
    vendor_posture: Mapping[str, str]

    def stripe_price_id(self, tier_name: str, interval: str) -> str | None:
        """Return the resolved Stripe price ID for a tier/interval, or None."""
        tier_map = self.stripe_price_ids.get(tier_name)
        if tier_map is None:
            return None
        return tier_map.get(interval)

    def is_group_allowed(self, group: str) -> bool:
        """True if this profile permits seeding the given data group (A/B/C/D)."""
        return group in self.allowed_groups


# ── Profile construction ─────────────────────────────────────────────────────


def _build_profile(env: SeedEnv, stripe_mode: StripeMode | None) -> EnvProfile:
    if env is SeedEnv.PROD:
        if stripe_mode is None:
            _fail(
                "--env prod requires --stripe-mode {test|live} (no default — "
                "fail-closed per design §G-2)."
            )
        price_ids = (
            _STRIPE_PRICE_IDS_TEST
            if stripe_mode is StripeMode.TEST
            else _STRIPE_PRICE_IDS_LIVE
        )
        return EnvProfile(
            env=env,
            allowed_groups=frozenset({"A", "B"}),
            stripe_mode=stripe_mode,
            stripe_price_ids=price_ids,
            allowed_db_host_patterns=(
                "rds.amazonaws.com",
                "localhost:5433",
                "127.0.0.1:5433",
            ),
            forbidden_db_host_patterns=(":5432/pilot_dev",),
            require_typed_confirmation=True,
            vendor_posture=_VENDOR_POSTURE_PROD,
        )

    # Non-prod: stripe_mode must be TEST or None (hardwired to TEST).
    if stripe_mode is StripeMode.LIVE:
        _fail(
            f"--stripe-mode live is only valid with --env prod (got --env {env.value})."
        )
    mode = stripe_mode or StripeMode.TEST

    if env is SeedEnv.DEV:
        return EnvProfile(
            env=env,
            allowed_groups=frozenset({"A", "B", "C", "D"}),
            stripe_mode=mode,
            stripe_price_ids=_STRIPE_PRICE_IDS_TEST,
            allowed_db_host_patterns=("",),  # any host allowed (local dev)
            forbidden_db_host_patterns=("rds.amazonaws.com",),
            require_typed_confirmation=False,
            vendor_posture=_VENDOR_POSTURE_DEV,
        )
    if env is SeedEnv.E2E:
        return EnvProfile(
            env=env,
            allowed_groups=frozenset({"A", "B", "C", "D"}),
            stripe_mode=mode,
            stripe_price_ids=_STRIPE_PRICE_IDS_TEST,
            allowed_db_host_patterns=("",),
            forbidden_db_host_patterns=("rds.amazonaws.com",),
            require_typed_confirmation=False,
            vendor_posture=_VENDOR_POSTURE_E2E,
        )
    # QA — placeholder profile (design §G-4). Unverified until a QA target exists.
    return EnvProfile(
        env=env,
        allowed_groups=frozenset({"A", "B", "C", "D"}),
        stripe_mode=mode,
        stripe_price_ids=_STRIPE_PRICE_IDS_TEST,
        allowed_db_host_patterns=("",),
        forbidden_db_host_patterns=("rds.amazonaws.com",),
        require_typed_confirmation=False,
        vendor_posture=_VENDOR_POSTURE_QA,
    )


# ── Public API ───────────────────────────────────────────────────────────────


def resolve_seed_env(cli_value: str | None) -> SeedEnv:
    """Resolve the target env: ``--env`` flag > ``SEED_ENV`` env var > default dev.

    Never reads pydantic ``settings.ENVIRONMENT`` (design §G-1). Unknown values
    raise :class:`SystemExit` with a usage message.
    """
    raw = cli_value or os.environ.get("SEED_ENV")
    if raw is None:
        return SeedEnv.DEV
    try:
        return SeedEnv(raw)
    except ValueError:
        valid = ", ".join(e.value for e in SeedEnv)
        _fail(
            f"Unknown --env / SEED_ENV value: {raw!r}. Valid: {valid}. "
            "(--env is decoupled from pydantic ENVIRONMENT — see design §G-1.)"
        )


def get_profile(env: SeedEnv, stripe_mode: str | None) -> EnvProfile:
    """Build and return the :class:`EnvProfile` for ``env`` + ``stripe_mode``.

    Fail-closed: prod without ``stripe_mode`` → SystemExit; ``--stripe-mode live``
    with non-prod → SystemExit (design §F.1 / §G-2).
    """
    sm: StripeMode | None = None
    if stripe_mode is not None:
        try:
            sm = StripeMode(stripe_mode)
        except ValueError:
            valid = ", ".join(m.value for m in StripeMode)
            _fail(f"Unknown --stripe-mode value: {stripe_mode!r}. Valid: {valid}.")
    return _build_profile(env, sm)


def assert_target_compatible(profile: EnvProfile, database_url: str) -> None:
    """Bidirectional host guard (design §E-3). Runs BEFORE any connection opens.

    * prod: requires an RDS host or ``localhost:5433`` (the SSH tunnel port);
      refuses ``:5432/pilot_dev`` and ``:5432/pilot``.
    * non-prod: refuses hosts containing ``rds.amazonaws.com``.
    """
    url_lower = (database_url or "").lower()
    if not url_lower:
        # No DATABASE_URL set — the script will fall back to the dev engine
        # singleton (via _db_utils.get_db_session). Skip the host guard in
        # this case; it only applies when an explicit target URL is provided.
        return

    if profile.env is SeedEnv.PROD:
        for bad in profile.forbidden_db_host_patterns:
            if bad.lower() in url_lower:
                _fail(
                    f"--env prod refuses the localhost dev DB (matched {bad!r}). "
                    "Set DATABASE_URL to the RDS host (via SSH tunnel on "
                    "localhost:5433) or an rds.amazonaws.com endpoint."
                )
        allowed = [p.lower() for p in profile.allowed_db_host_patterns if p]
        if allowed and not any(p in url_lower for p in allowed):
            _fail(
                "--env prod requires an RDS host or localhost:5433 (the tunnel). "
                f"DATABASE_URL does not match any allowed pattern: {allowed}."
            )
    else:
        for bad in profile.forbidden_db_host_patterns:
            if bad.lower() in url_lower:
                _fail(
                    f"--env {profile.env.value} refuses RDS hosts (matched {bad!r}). "
                    "Non-prod seeds target local databases only."
                )


def print_seed_banner(profile: EnvProfile, database_url: str, script_name: str) -> None:
    """Print the audit banner: script, env, stripe_mode, posture, host, groups."""
    safe_url = _mask_password(database_url)
    host_db: str
    if "://" in safe_url:
        try:
            parsed = urlparse(safe_url)
            host_db = (
                f"{parsed.hostname}:{parsed.port}/{parsed.path.lstrip('/')}"
                if parsed.hostname
                else safe_url
            )
        except ValueError:
            host_db = safe_url
    else:
        host_db = safe_url
    groups = ", ".join(sorted(profile.allowed_groups))
    mode = profile.stripe_mode.value if profile.stripe_mode else "(none)"
    posture = ", ".join(f"{k}={v}" for k, v in sorted(profile.vendor_posture.items()))
    print("=" * 72)
    print(f"  SEED BANNER — {script_name}")
    print(f"    env            : {profile.env.value}")
    print(f"    stripe_mode    : {mode}")
    print(f"    vendor_posture : {posture}")
    print(f"    target         : {host_db}")
    print(f"    allowed_groups : {groups}")
    print("=" * 72)


def verify_stripe_key_alignment(
    profile: EnvProfile, secret_id: str, *, skip_preflight: bool = False
) -> None:
    """Prod preflight: confirm the Stripe secret key mode matches the profile.

    Uses ``aws secretsmanager get-secret-value`` via :mod:`subprocess` (no boto3
    dependency — matches the psql-subprocess pattern in ``init_e2e_schema.py``).
    ``sk_test_`` must pair with :attr:`StripeMode.TEST`; ``sk_live_`` with
    :attr:`StripeMode.LIVE`. An unreadable secret is refused unless
    ``skip_preflight`` is set (loud warning). Auto-skipped for non-prod envs.
    """
    if profile.env is not SeedEnv.PROD:
        return  # Local envs: no preflight.
    if skip_preflight:
        print(
            "  ⚠️  WARNING: --skip-preflight set — Stripe key alignment NOT verified. "
            "Proceeding without confirming the secret key mode matches --stripe-mode."
        )
        return
    if profile.stripe_mode is None:
        _fail(
            "verify_stripe_key_alignment called with prod profile but no stripe_mode."
        )

    print(f"  Preflight: verifying Stripe key mode in secret '{secret_id}'...")
    try:
        result = subprocess.run(
            [
                "aws",
                "secretsmanager",
                "get-secret-value",
                "--secret-id",
                secret_id,
                "--query",
                "SecretString",
                "--output",
                "text",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except FileNotFoundError:
        _fail(
            "aws CLI not found — cannot run Stripe key preflight. "
            "Install the AWS CLI or pass --skip-preflight (not recommended)."
        )
    except subprocess.TimeoutExpired:
        _fail("aws secretsmanager get-secret-value timed out after 30s.")

    if result.returncode != 0:
        _fail(
            f"aws secretsmanager get-secret-value failed (exit {result.returncode}):\n"
            f"{result.stderr.strip()[:500]}\n"
            "Refusing to proceed. Fix the secret access or pass --skip-preflight."
        )

    secret_text = result.stdout.strip()
    expected_prefix = (
        "sk_test_" if profile.stripe_mode is StripeMode.TEST else "sk_live_"
    )
    other_prefix = "sk_live_" if profile.stripe_mode is StripeMode.TEST else "sk_test_"
    if expected_prefix in secret_text:
        print(
            f"  ✅ Stripe key alignment verified ({expected_prefix}... matches "
            f"{profile.stripe_mode.value})."
        )
        return
    if other_prefix in secret_text:
        _fail(
            f"Stripe key MISMATCH: secret '{secret_id}' contains a {other_prefix}... "
            f"key but --stripe-mode={profile.stripe_mode.value} was requested. "
            "Flip the key in Secrets Manager or use the matching --stripe-mode."
        )
    print(
        f"  ⚠️  WARNING: Stripe secret '{secret_id}' is readable but no "
        f"{expected_prefix} or {other_prefix} prefix was found. Proceeding — "
        "verify the secret shape manually."
    )


# ── Helpers ──────────────────────────────────────────────────────────────────


def convergeable_tiers() -> tuple[str, ...]:
    """Tiers whose price IDs are safe to converge in prod (design §G-7).

    Charter is excluded until its price-ID mode is classified by Tom.
    """
    return _CONVERGEABLE_TIERS


# Regex to match the password component in a postgresql:// URL.
# Matches: scheme://user:password@host:port/db  →  captures user + password + rest
# Handles passwords containing special chars (@, :, /, %, etc.) by matching
# greedily up to the LAST @ (the real userinfo/host separator per RFC 3986).
_PG_URL_RE = re.compile(
    r"^([a-zA-Z]+://)"  # scheme://
    r"([^:@]+):"  # username:
    r"(.+)@"  # password (greedy — everything up to the LAST @)
    r"(.+)$"  # host:port/db
)


def _mask_password(url: str) -> str:
    """Replace the password in a postgresql:// URL with *** for display.

    Uses a regex instead of ``urlparse`` because passwords containing
    special characters (``@``, ``:``, ``/``) cause ``urlparse`` to raise
    ``ValueError("Invalid IPv6 URL")`` on Python 3.14+.
    """
    if "://" not in url:
        return url
    match = _PG_URL_RE.match(url)
    if match and match.group(3):
        scheme, user, _pw, rest = match.groups()
        return f"{scheme}{user}:***@{rest}"
    return url


def _fail(message: str) -> None:
    """Print an error to stderr and exit non-zero (fail-closed)."""
    print(f"ERROR [seed-env]: {message}", file=sys.stderr)
    raise SystemExit(1)


# ── Standard argparse helper ─────────────────────────────────────────────────


def add_env_args(parser) -> None:
    """Add the standard ``--env`` / ``--stripe-mode`` / ``--skip-preflight`` args.

    Call this in every seed script's ``parse_args()`` alongside its existing
    ``--mode`` / ``--reset`` args. The resolved profile is obtained via
    :func:`resolve_seed_env` + :func:`get_profile` in the script's main block.
    """
    parser.add_argument(
        "--env",
        choices=["dev", "e2e", "qa", "prod"],
        default=None,
        help="Target environment profile (default: $SEED_ENV, else dev). "
        "Decoupled from pydantic ENVIRONMENT (design §G-1).",
    )
    parser.add_argument(
        "--stripe-mode",
        choices=["test", "live"],
        default=None,
        help="Stripe key/price mode. Required with --env prod; rejected with "
        "--stripe-mode live on non-prod envs (design §G-2).",
    )
    parser.add_argument(
        "--skip-preflight",
        action="store_true",
        default=False,
        help="Skip the Stripe secrets-manager key-alignment preflight (prod). "
        "Not recommended — emits a loud warning.",
    )


def resolve_profile_from_args(args) -> EnvProfile:
    """Convenience: resolve env + stripe_mode from parsed args + SEED_ENV."""
    env = resolve_seed_env(getattr(args, "env", None))
    return get_profile(env, getattr(args, "stripe_mode", None))


def assert_group_allowed(profile: EnvProfile, group: str, script_name: str) -> None:
    """Exit non-zero if ``group`` is not allowed for this profile (design §B.4)."""
    if not profile.is_group_allowed(group):
        _fail(
            f"{script_name} is a Group {group} script — not allowed for "
            f"--env {profile.env.value} (allowed groups: "
            f"{', '.join(sorted(profile.allowed_groups))}). "
            "Prod permits Groups A+B only (design §B.4)."
        )
