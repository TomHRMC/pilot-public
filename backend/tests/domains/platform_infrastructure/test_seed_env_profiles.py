"""
Unit tests for the env-aware seed profile registry (DB-MGMT-1, ADR-0016).

Tests pure logic — no DB connection required. Covers:
  - resolve_seed_env precedence (flag > SEED_ENV > default)
  - unknown env → SystemExit
  - prod without --stripe-mode → SystemExit
  - --stripe-mode live with non-prod → SystemExit
  - group gating (prod = A+B only; non-prod = A+B+C+D)
  - host guards (prod↔localhost-dev refusal; non-prod↔RDS refusal)
  - price-ID map selection per mode
  - banner output (capsys)
"""

import pytest

from migrations.scripts._env_profiles import (
    SeedEnv,
    StripeMode,
    assert_group_allowed,
    assert_target_compatible,
    convergeable_tiers,
    get_profile,
    print_seed_banner,
    resolve_seed_env,
)

pytestmark = [pytest.mark.domain_platform_infrastructure, pytest.mark.unit]

# ── resolve_seed_env precedence ──────────────────────────────────────────────


class TestResolveSeedEnv:
    def test_default_dev_when_no_flag_no_env(self, monkeypatch):
        monkeypatch.delenv("SEED_ENV", raising=False)
        assert resolve_seed_env(None) is SeedEnv.DEV

    def test_flag_overrides_env(self, monkeypatch):
        monkeypatch.setenv("SEED_ENV", "qa")
        assert resolve_seed_env("prod") is SeedEnv.PROD

    def test_env_var_used_when_no_flag(self, monkeypatch):
        monkeypatch.setenv("SEED_ENV", "e2e")
        assert resolve_seed_env(None) is SeedEnv.E2E

    def test_unknown_env_exits(self, monkeypatch):
        monkeypatch.delenv("SEED_ENV", raising=False)
        with pytest.raises(SystemExit):
            resolve_seed_env("staging")


# ── get_profile fail-closed ──────────────────────────────────────────────────


class TestGetProfile:
    def test_prod_without_stripe_mode_exits(self):
        with pytest.raises(SystemExit):
            get_profile(SeedEnv.PROD, None)

    def test_stripe_mode_live_with_dev_exits(self):
        with pytest.raises(SystemExit):
            get_profile(SeedEnv.DEV, "live")

    def test_stripe_mode_live_with_qa_exits(self):
        with pytest.raises(SystemExit):
            get_profile(SeedEnv.QA, "live")

    def test_dev_test_mode_succeeds(self):
        p = get_profile(SeedEnv.DEV, "test")
        assert p.env is SeedEnv.DEV
        assert p.stripe_mode is StripeMode.TEST

    def test_prod_test_mode_succeeds(self):
        p = get_profile(SeedEnv.PROD, "test")
        assert p.env is SeedEnv.PROD
        assert p.stripe_mode is StripeMode.TEST

    def test_prod_live_mode_succeeds(self):
        p = get_profile(SeedEnv.PROD, "live")
        assert p.env is SeedEnv.PROD
        assert p.stripe_mode is StripeMode.LIVE

    def test_unknown_stripe_mode_exits(self):
        with pytest.raises(SystemExit):
            get_profile(SeedEnv.PROD, "invalid")


# ── Group gating ─────────────────────────────────────────────────────────────


class TestGroupGating:
    def test_prod_allows_a_and_b(self):
        p = get_profile(SeedEnv.PROD, "test")
        assert p.is_group_allowed("A")
        assert p.is_group_allowed("B")

    def test_prod_refuses_c_and_d(self):
        p = get_profile(SeedEnv.PROD, "test")
        assert not p.is_group_allowed("C")
        assert not p.is_group_allowed("D")

    def test_dev_allows_all_groups(self):
        p = get_profile(SeedEnv.DEV, None)
        for g in ("A", "B", "C", "D"):
            assert p.is_group_allowed(g)

    def test_qa_allows_all_groups(self):
        p = get_profile(SeedEnv.QA, None)
        for g in ("A", "B", "C", "D"):
            assert p.is_group_allowed(g)

    def test_assert_group_allowed_prod_c_exits(self):
        p = get_profile(SeedEnv.PROD, "test")
        with pytest.raises(SystemExit):
            assert_group_allowed(p, "C", "seed_test_tenant.py")

    def test_assert_group_allowed_dev_c_ok(self):
        p = get_profile(SeedEnv.DEV, None)
        # Should not raise
        assert_group_allowed(p, "C", "seed_test_tenant.py")


# ── Host guards ──────────────────────────────────────────────────────────────


class TestHostGuards:
    def test_prod_refuses_localhost_dev(self):
        p = get_profile(SeedEnv.PROD, "test")
        with pytest.raises(SystemExit):
            assert_target_compatible(
                p, "postgresql://pilot:pilot@localhost:5432/pilot_dev"
            )

    def test_prod_accepts_rds(self):
        p = get_profile(SeedEnv.PROD, "test")
        # Should not raise
        assert_target_compatible(
            p,
            "postgresql://pilot:pilot@mydb.abcd1234.us-east-1.rds.amazonaws.com:5432/pilot_prod",
        )

    def test_prod_accepts_tunnel_5433(self):
        p = get_profile(SeedEnv.PROD, "test")
        assert_target_compatible(
            p, "postgresql://pilot:pilot@localhost:5433/pilot_prod"
        )

    def test_prod_accepts_tunnel_5433_ip_spelling(self):
        """Runbook teaches 127.0.0.1:5433 — same tunnel as localhost:5433, guard accepts both."""
        p = get_profile(SeedEnv.PROD, "test")
        assert_target_compatible(
            p, "postgresql://pilot:pilot@127.0.0.1:5433/pilot_prod"
        )

    def test_prod_still_refuses_dev_db_on_ip_spelling(self):
        """Fail-closed: the IP spelling must not widen the guard to the dev DB."""
        p = get_profile(SeedEnv.PROD, "test")
        with pytest.raises(SystemExit):
            assert_target_compatible(
                p, "postgresql://pilot:pilot@127.0.0.1:5432/pilot_dev"
            )

    def test_dev_refuses_rds(self):
        p = get_profile(SeedEnv.DEV, None)
        with pytest.raises(SystemExit):
            assert_target_compatible(
                p,
                "postgresql://pilot:pilot@mydb.abcd1234.us-east-1.rds.amazonaws.com:5432/pilot_dev",
            )

    def test_dev_accepts_localhost(self):
        p = get_profile(SeedEnv.DEV, None)
        assert_target_compatible(p, "postgresql://pilot:pilot@localhost:5432/pilot_dev")

    def test_empty_url_skips_guard(self):
        p = get_profile(SeedEnv.PROD, "test")
        # No DATABASE_URL — falls back to dev singleton; guard skipped
        assert_target_compatible(p, "")


# ── Price-ID map selection ───────────────────────────────────────────────────


class TestPriceIdSelection:
    def test_dev_uses_test_ids(self):
        p = get_profile(SeedEnv.DEV, None)
        assert (
            p.stripe_price_id("starter", "monthly") == "price_REDACTED16"
        )
        assert (
            p.stripe_price_id("starter", "annual") == "price_REDACTED17"
        )

    def test_prod_test_uses_test_ids(self):
        p = get_profile(SeedEnv.PROD, "test")
        assert (
            p.stripe_price_id("starter", "monthly") == "price_REDACTED16"
        )

    def test_prod_live_uses_live_ids(self):
        p = get_profile(SeedEnv.PROD, "live")
        assert (
            p.stripe_price_id("starter", "monthly") == "price_REDACTED01"
        )
        assert (
            p.stripe_price_id("starter", "annual") == "price_REDACTED05"
        )

    def test_trial_has_no_price_ids(self):
        p = get_profile(SeedEnv.DEV, None)
        assert p.stripe_price_id("trial", "monthly") is None
        assert p.stripe_price_id("trial", "annual") is None

    def test_unknown_tier_returns_none(self):
        p = get_profile(SeedEnv.DEV, None)
        assert p.stripe_price_id("nonexistent", "monthly") is None

    def test_convergeable_tiers_includes_charter(self):
        """Charter re-admitted 2026-08-18 — price-ID mode classified."""
        tiers = convergeable_tiers()
        assert "starter" in tiers
        assert "teams" in tiers
        assert "charter" in tiers
        assert "trial" not in tiers


# ── Banner output ────────────────────────────────────────────────────────────


class TestBanner:
    def test_banner_prints_env_and_groups(self, capsys):
        p = get_profile(SeedEnv.DEV, None)
        print_seed_banner(
            p,
            "postgresql://pilot:secret@localhost:5432/pilot_dev",
            "seed_core.py",
        )
        out = capsys.readouterr().out
        assert "seed_core.py" in out
        assert "dev" in out
        assert "A, B, C, D" in out

    def test_banner_masks_password(self, capsys):
        p = get_profile(SeedEnv.DEV, None)
        print_seed_banner(
            p,
            "postgresql://pilot:supersecret@localhost:5432/pilot_dev",
            "seed_core.py",
        )
        out = capsys.readouterr().out
        # The banner parses the URL and displays only host:port/dbname,
        # so the password never appears in the output.
        assert "supersecret" not in out

    def test_banner_prod_shows_stripe_mode(self, capsys):
        p = get_profile(SeedEnv.PROD, "test")
        print_seed_banner(
            p,
            "postgresql://pilot:pw@localhost:5433/pilot_prod",
            "seed_platform.py",
        )
        out = capsys.readouterr().out
        assert "test" in out
        assert "A, B" in out

    def test_banner_password_with_special_chars(self, capsys):
        """Passwords containing @, :, / must not crash urlparse (Python 3.14+)."""
        p = get_profile(SeedEnv.PROD, "test")
        print_seed_banner(
            p,
            "postgresql://pilot_user:p@ss:w0rd/with@specials@localhost:5433/pilot_prod",
            "seed_prod_db.py",
        )
        out = capsys.readouterr().out
        assert "seed_prod_db.py" in out
        assert "p@ss:w0rd/with@specials" not in out
        assert "localhost:5433/pilot_prod" in out

    def test_mask_password_no_crash_on_percent_encoded(self):
        """Percent-encoded passwords with %2F etc. must not crash."""
        from migrations.scripts._env_profiles import _mask_password

        result = _mask_password("postgresql://user:p%40ss%2Fword@localhost:5432/db")
        assert "p%40ss%2Fword" not in result
        assert "***" in result
        assert "localhost:5432/db" in result
