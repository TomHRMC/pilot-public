"""
seed_prod_db.py — Prod converge-in-place orchestrator (DB-MGMT-1, design §F.4).

Converges Groups A+B only (registry enforces). Existing prod is **never
reprovisioned** — it is converged by idempotent seed re-runs (design §G-3).

Sequence:
  1. Typed confirmation (``PILOT-PROD-SEED``) — required for ``seed`` mode only
  2. ``verify_stripe_key_alignment("pilot/prod/stripe")`` preflight
  3. ``seed_core.py --env prod``
  4. ``seed_platform.py --env prod --stripe-mode <mode>``
  5. Inspect summary vs manifest

``--mode show|inspect`` requires no confirmation and opens no writes.

Usage:
    # Dry-run (no writes, no confirmation):
    DATABASE_URL=postgresql://... python migrations/scripts/seed_prod_db.py --mode show
    DATABASE_URL=postgresql://... python migrations/scripts/seed_prod_db.py --mode inspect

    # Real converge (Tom executes this):
    DATABASE_URL=postgresql://... \\
    python migrations/scripts/seed_prod_db.py --mode seed --stripe-mode test

SAFETY: The host guard refuses to run against the localhost dev DB.
``--env prod`` is hardwired; ``--stripe-mode`` is required for ``seed`` mode.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).parent.parent.parent
SCRIPTS_DIR = BACKEND_DIR / "migrations" / "scripts"

sys.path.insert(0, str(BACKEND_DIR))

from migrations.scripts._env_profiles import (  # noqa: E402
    SeedEnv,
    assert_target_compatible,
    get_profile,
    print_seed_banner,
    verify_stripe_key_alignment,
)

# The Stripe secret ID for prod key alignment preflight
STRIPE_SECRET_ID = "pilot/prod/stripe"


def _typed_confirmation() -> None:
    """Require the user to type PILOT-PROD-SEED to proceed with prod seeding."""
    print("\n" + "!" * 72)
    print("  ⚠️  PROD SEED — This will converge Group A+B data in PRODUCTION.")
    print("  This is NOT a drill. Existing rows are updated idempotently.")
    print("!" * 72)
    print("\n  Type PILOT-PROD-SEED to proceed, or anything else to abort:")
    response = input("  > ").strip()
    if response != "PILOT-PROD-SEED":
        print("  Aborted.")
        sys.exit(1)
    print("  Confirmation accepted.\n")


def _run(cmd: list[str], env: dict | None = None) -> None:
    """Run a command, raising on non-zero exit."""
    print(f"  $ {' '.join(cmd)}")
    result = subprocess.run(cmd, env=env or os.environ, cwd=str(BACKEND_DIR))
    if result.returncode != 0:
        print(
            f"ERROR: Command failed with exit code {result.returncode}", file=sys.stderr
        )
        sys.exit(result.returncode)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="seed_prod_db.py — prod converge-in-place orchestrator (DB-MGMT-1)"
    )
    parser.add_argument(
        "--mode",
        choices=["seed", "inspect", "show"],
        default="seed",
        help="seed: converge Group A+B | inspect: show current state | show: print what would be written",
    )
    # --stripe-mode and --skip-preflight are added by add_env_args below.
    # This script forces --env prod, so --env is not exposed (it's hardwired).
    parser.add_argument(
        "--stripe-mode",
        choices=["test", "live"],
        default=None,
        help="Required for --mode seed. test = Phase 1 (sk_test_ keys); live = GA cutover.",
    )
    parser.add_argument(
        "--skip-preflight",
        action="store_true",
        default=False,
        help="Skip the Stripe secrets-manager key-alignment preflight. Not recommended.",
    )
    # Only add --skip-preflight from add_env_args (stripe-mode already defined above).
    # We don't use add_env_args here because this script hardwires --env prod.
    args = parser.parse_args()

    # Force --env prod (this script is prod-only)
    env = SeedEnv.PROD
    profile = get_profile(env, args.stripe_mode)
    target_url = os.environ.get("DATABASE_URL", "")
    if not target_url:
        print("ERROR: DATABASE_URL must be set to the prod database.", file=sys.stderr)
        sys.exit(1)
    assert_target_compatible(profile, target_url)
    print_seed_banner(profile, target_url, "seed_prod_db.py")

    if args.mode == "seed":
        # Typed confirmation
        _typed_confirmation()

        # Stripe key alignment preflight
        verify_stripe_key_alignment(
            profile, STRIPE_SECRET_ID, skip_preflight=args.skip_preflight
        )

        # Step 1: Group A — core lookup data
        print("\n[1/3] Converging Group A — core lookups (seed_core.py)...")
        _run(
            [
                "python",
                str(SCRIPTS_DIR / "seed_core.py"),
                "--env",
                "prod",
                "--stripe-mode",
                args.stripe_mode,
            ],
            env={**os.environ, "DATABASE_URL": target_url},
        )

        # Step 2: Group B — platform config (env-aware Stripe converge)
        print("\n[2/3] Converging Group B — platform config (seed_platform.py)...")
        _run(
            [
                "python",
                str(SCRIPTS_DIR / "seed_platform.py"),
                "--env",
                "prod",
                "--stripe-mode",
                args.stripe_mode,
            ],
            env={**os.environ, "DATABASE_URL": target_url},
        )

        # Step 3: Inspect summary
        print("\n[3/3] Inspecting converged state...")
        _run(
            [
                "python",
                str(SCRIPTS_DIR / "seed_core.py"),
                "--env",
                "prod",
                "--stripe-mode",
                args.stripe_mode,
                "--mode",
                "inspect",
            ],
            env={**os.environ, "DATABASE_URL": target_url},
        )

        print("\n" + "=" * 72)
        print("  ✅ Prod converge complete (Groups A+B).")
        print("=" * 72)
        print("  Verify subscription_tier price IDs match the Stripe dashboard:")
        print("  python migrations/scripts/seed_platform.py --env prod --mode inspect")

    elif args.mode == "inspect":
        # Read-only: no confirmation, no preflight
        print("\n  Inspecting prod Group A+B state (read-only)...\n")
        _run(
            [
                "python",
                str(SCRIPTS_DIR / "seed_core.py"),
                "--env",
                "prod",
                "--stripe-mode",
                args.stripe_mode or "test",
                "--mode",
                "inspect",
            ],
            env={**os.environ, "DATABASE_URL": target_url},
        )
        _run(
            [
                "python",
                str(SCRIPTS_DIR / "seed_platform.py"),
                "--env",
                "prod",
                "--stripe-mode",
                args.stripe_mode or "test",
                "--mode",
                "inspect",
            ],
            env={**os.environ, "DATABASE_URL": target_url},
        )

    elif args.mode == "show":
        # Read-only: no confirmation, no preflight, no DB connection
        print("\n  Showing what would be written to prod (no DB connection)...\n")
        _run(
            [
                "python",
                str(SCRIPTS_DIR / "seed_core.py"),
                "--env",
                "prod",
                "--stripe-mode",
                args.stripe_mode or "test",
                "--mode",
                "show",
            ],
            env={**os.environ, "DATABASE_URL": target_url},
        )
        _run(
            [
                "python",
                str(SCRIPTS_DIR / "seed_platform.py"),
                "--env",
                "prod",
                "--stripe-mode",
                args.stripe_mode or "test",
                "--mode",
                "show",
            ],
            env={**os.environ, "DATABASE_URL": target_url},
        )


if __name__ == "__main__":
    main()
