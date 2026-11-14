"""
Mutation Coverage Tests for: services/sms_quota.py
Domain: Subscriptions & Usage (PRD §3.11)

Session: smoke-sms-quota
Report:  backend/admin_tools/cosmic-ray/sessions/smoke/reports/
         2026-05-29_18-51-10_Smoke Test — sms_quota.py.md
Log:     backend/admin_tools/cosmic-ray/qa-workflows/
         2026-05-30_smoke-sms-quota_qa-workflow.md

Each test function is tied to one occurrence group in the workflow log.
Function names encode what source behaviour is pinned so future readers
understand why the test exists.
"""

import calendar
import uuid
from datetime import UTC, datetime

import pytest

pytestmark = [
    pytest.mark.domain_subscriptions_usage,
    pytest.mark.unit,
]


# ─── Shared helpers ─────────────────────────────────────────────────────────


def _make_quota_period(db_session, tenant_id, *, used, included, cap_policy="soft"):
    """Create an active SmsQuotaPeriod covering the current calendar month."""
    from app.models.sms import SmsQuotaPeriod

    now = datetime.now(UTC)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_day = calendar.monthrange(now.year, now.month)[1]
    end = start.replace(day=last_day, hour=23, minute=59, second=59)

    period = SmsQuotaPeriod(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        period_start=start,
        period_end=end,
        included_segments=included,
        used_segments=used,
        cap_policy=cap_policy,
    )
    db_session.add(period)
    db_session.commit()
    return period


def _make_customer(db_session, tenant_id, *, sms_opted_out=False):
    """Create a minimal Customer row for quota-check tests."""
    from app.models.crm import Customer

    now = datetime.now(UTC)
    customer = Customer(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        type="person",
        display_name=f"Quota Test {uuid.uuid4().hex[:6]}",
        sms_opted_out=sms_opted_out,
        preferred_contact_channel="sms",
        sms_opt_in_consent=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(customer)
    db_session.commit()
    return customer


# ─── Occurrence Group 1 ─────────────────────────────────────────────────────
# Source line (sms_quota.py:103):
#   if cap_policy == "hard" and (used + requested_segments) > included:
#
# Operators survived (occurrence 0):
#   Add_LShift (used << requested_segments), Add_BitOr (used | requested_segments),
#   Add_BitXor (used ^ requested_segments)
#
# Why they survived: the only prior hard-cap test used used=100, included=100 so
#   100 << 1=200, 100|1=101, 100^1=101 — all still >100, still blocked.
#   No test exercised a case where the mutated expression yields ≤ included.
#
# Kill strategy:
#   Test A — used=0, requested=5, included=3:
#       correct: 0+5=5 > 3 → blocked
#       LShift:  0<<5=0  ≤ 3 → NOT blocked  ← kills Add_LShift
#       BitOr:   0|5=5   > 3 → still blocked (same behaviour as correct; not killed here)
#       BitXor:  0^5=5   > 3 → still blocked (same behaviour as correct; not killed here)
#   Test B — used=4, requested=4, included=6:
#       correct: 4+4=8 > 6 → blocked
#       BitOr:   4|4=4  ≤ 6 → NOT blocked  ← kills Add_BitOr
#       BitXor:  4^4=0  ≤ 6 → NOT blocked  ← kills Add_BitXor
#       LShift:  4<<4=64 > 6 → still blocked (not distinguishable here)


class TestCheckQuotaHardCapArithmetic:
    """
    Pins the exact addition semantics at sms_quota.py:103.

    Occurrence group 1 — operators: Add_LShift, Add_BitOr, Add_BitXor (occurrence 0).
    """

    def test_hard_cap_blocks_when_used_is_zero_and_request_exceeds_included(
        self, db_session, test_tenant
    ):
        """
        Hard cap with used=0 blocks when requested_segments alone exceeds included.

        Kills Add_LShift (occurrence 0): 0<<5=0 ≤ 3 would incorrectly allow the send.
        """
        from services.sms_quota import check_quota

        customer = _make_customer(db_session, test_tenant.id)
        _make_quota_period(
            db_session,
            test_tenant.id,
            used=0,
            included=3,
            cap_policy="hard",
        )

        result = check_quota(
            db_session,
            test_tenant.id,
            customer.id,
            requested_segments=5,
        )

        assert result.allowed is False, (
            "Hard cap must block when (used + requested_segments) > included; "
            "got allowed=True (Add_LShift mutation would cause this)"
        )
        assert result.blocked_reason == "monthly_quota_reached"
        assert result.used_segments == 0
        assert result.included_segments == 3
        assert result.remaining_segments == 3

    def test_hard_cap_blocks_when_bitwise_or_of_used_and_request_fits_but_sum_does_not(
        self, db_session, test_tenant
    ):
        """
        Hard cap with used=4, included=6, requested=4: sum 8 > 6 → blocked.

        Kills Add_BitOr  (occurrence 0): 4|4=4 ≤ 6 would incorrectly allow the send.
        Kills Add_BitXor (occurrence 0): 4^4=0 ≤ 6 would incorrectly allow the send.
        """
        from services.sms_quota import check_quota

        customer = _make_customer(db_session, test_tenant.id)
        _make_quota_period(
            db_session,
            test_tenant.id,
            used=4,
            included=6,
            cap_policy="hard",
        )

        result = check_quota(
            db_session,
            test_tenant.id,
            customer.id,
            requested_segments=4,
        )

        assert result.allowed is False, (
            "Hard cap must block when used + requested_segments > included (8 > 6); "
            "Add_BitOr (4|4=4) or Add_BitXor (4^4=0) mutations would allow this"
        )
        assert result.blocked_reason == "monthly_quota_reached"
        assert result.used_segments == 4
        assert result.included_segments == 6
        assert result.remaining_segments == 2


# ─── Occurrence Group 2 ─────────────────────────────────────────────────────
# Source line (sms_quota.py:113):
#   overage = (used + requested_segments) > included
#
# Operators survived (occurrence 1):
#   Add_Mul, Add_Pow, Add_LShift, Add_BitOr, Add_BitXor (5 total)
#
# Why they survived: No test asserted the exact boolean value of `overage` with
#   numbers that distinguish used+requested from used*requested (or bitwise ops).
#
# Kill strategy:
#   Test A — used=0, requested=5, included=3, cap_policy='soft':
#       correct: 0+5=5 > 3 → overage=True
#       Mul:   0*5=0  ≤ 3 → overage=False  ← kills Add_Mul
#       Pow:   0**5=0 ≤ 3 → overage=False  ← kills Add_Pow
#       LShift:0<<5=0 ≤ 3 → overage=False  ← kills Add_LShift
#   Test B — used=4, requested=4, included=6, cap_policy='soft':
#       correct: 4+4=8 > 6 → overage=True
#       BitOr: 4|4=4  ≤ 6 → overage=False  ← kills Add_BitOr
#       BitXor:4^4=0  ≤ 6 → overage=False  ← kills Add_BitXor


class TestCheckQuotaSoftCapOverageFlag:
    """
    Pins the exact addition semantics of the soft-cap overage flag at sms_quota.py:113.

    Occurrence group 2 — operators: Add_Mul, Add_Pow, Add_LShift, Add_BitOr,
    Add_BitXor (occurrence 1).
    """

    def test_soft_cap_overage_true_when_zero_used_and_request_exceeds_included(
        self, db_session, test_tenant
    ):
        """
        Soft cap with used=0 sets overage=True when requested_segments alone exceeds included.

        Kills Add_Mul  (0*5=0): would produce overage=False.
        Kills Add_Pow  (0**5=0): would produce overage=False.
        Kills Add_LShift (0<<5=0): would produce overage=False.
        """
        from services.sms_quota import check_quota

        customer = _make_customer(db_session, test_tenant.id)
        _make_quota_period(
            db_session,
            test_tenant.id,
            used=0,
            included=3,
            cap_policy="soft",
        )

        result = check_quota(
            db_session,
            test_tenant.id,
            customer.id,
            requested_segments=5,
        )

        assert result.allowed is True, "Soft cap must always allow the send"
        assert result.overage is True, (
            "overage must be True when (used + requested_segments) > included; "
            "Add_Mul/Add_Pow/Add_LShift mutations produce 0, incorrectly giving overage=False"
        )
        assert result.used_segments == 0
        assert result.included_segments == 3
        assert result.remaining_segments == 3

    def test_soft_cap_overage_true_when_bitwise_of_used_and_request_fits_but_sum_does_not(
        self, db_session, test_tenant
    ):
        """
        Soft cap with used=4, included=6, requested=4: sum 8 > 6 → overage=True.

        Kills Add_BitOr  (4|4=4 ≤ 6): would produce overage=False.
        Kills Add_BitXor (4^4=0 ≤ 6): would produce overage=False.
        """
        from services.sms_quota import check_quota

        customer = _make_customer(db_session, test_tenant.id)
        _make_quota_period(
            db_session,
            test_tenant.id,
            used=4,
            included=6,
            cap_policy="soft",
        )

        result = check_quota(
            db_session,
            test_tenant.id,
            customer.id,
            requested_segments=4,
        )

        assert result.allowed is True, "Soft cap must always allow the send"
        assert result.overage is True, (
            "overage must be True when used + requested_segments > included (8 > 6); "
            "Add_BitOr (4|4=4) or Add_BitXor (4^4=0) mutations give overage=False"
        )
        assert result.used_segments == 4
        assert result.included_segments == 6
        assert result.remaining_segments == 2


# ─── Occurrence Group 3 ─────────────────────────────────────────────────────
# Source line (sms_quota.py:201):
#   period_end = period_start.replace(year=period_start.year + 1, month=1)
#
# Context: create_initial_period() — December branch (month == 12).
# The next quota period boundary must be January of the NEXT year.
#
# Operators survived (occurrence 3):
#   Add_Sub, Add_Mul, Add_Div, Add_FloorDiv, Add_Mod, Add_Pow,
#   Add_RShift, Add_LShift, Add_BitOr, Add_BitAnd, Add_BitXor (11 total)
#
# Why they survived: No test calls create_initial_period() in December,
#   so the month==12 branch was never executed by any test.
#
# Kill strategy:
#   Mock datetime.now(UTC) to Dec 15, 2025 (odd year so year^1=2024 ≠ 2026).
#   Expected: period_end.year == 2026, period_end.month == 1.
#
#   All 11 mutations produce wrong results:
#     Sub:       2025-1=2024 ≠ 2026
#     Mul:       2025*1=2025 (replace_year(2025,month=1) → wrong year)
#                Note: month arg means replace gets year=2025*1=2025, which
#                actually for most operators gives year != 2026.
#     Div:       2025/1=2025.0 → TypeError (int expected)
#     FloorDiv:  2025//1=2025 ≠ 2026
#     Mod:       2025%1=0 ≠ 2026
#     Pow:       2025**1=2025 ≠ 2026
#     RShift:    2025>>1=1012 ≠ 2026
#     LShift:    2025<<1=4050 ≠ 2026
#     BitOr:     2025|1=2025 ≠ 2026
#     BitAnd:    2025&1=1 ≠ 2026
#     BitXor:    2025^1=2024 ≠ 2026  (2025 is odd, so XOR 1 subtracts 1)


class TestCreateInitialPeriodDecemberRollover:
    """
    Pins the `year + 1` arithmetic in the December branch of create_initial_period().

    Occurrence group 3 — operators: Add_Sub, Add_Mul, Add_Div, Add_FloorDiv,
    Add_Mod, Add_Pow, Add_RShift, Add_LShift, Add_BitOr, Add_BitAnd, Add_BitXor
    (occurrence 3, 11 total).
    """

    def test_create_initial_period_december_year_rollover(
        self, db_session, test_tenant
    ):
        """
        December quota period end must roll over to January of the NEXT year.

        Uses December 2025 (odd year) so that 2025^1=2024 ≠ 2026, killing Add_BitXor.
        All 11 operator mutations at occurrence 3 produce period_end.year ≠ 2026.
        """
        from datetime import datetime
        from unittest.mock import patch

        import services.sms_quota as quota_svc

        december_2025 = datetime(2025, 12, 15, 10, 0, 0, tzinfo=UTC)

        with patch("services.sms_quota.datetime") as mock_dt:
            mock_dt.now.return_value = december_2025
            # Let datetime(...) constructor calls pass through unmodified
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

            period = quota_svc.create_initial_period(
                db_session,
                tenant_id=test_tenant.id,
                included_segments=100,
                cap_policy="soft",
            )

        # period_end stored is period_end_inclusive = (Jan 1, 2026) - 1 second
        # = Dec 31, 2025 23:59:59  →  year=2025, month=12
        #
        # With mutations:
        #   year-1=2024 → Jan 1, 2024 - 1s → Dec 31, 2023  (year=2023) ✓ caught
        #   year*1=2025 → Jan 1, 2025 - 1s → Dec 31, 2024  (year=2024) ✓ caught
        #   year//1=2025 → same as above                    (year=2024) ✓ caught
        #   year**1=2025 → same as above                    (year=2024) ✓ caught
        #   year%1=0    → replace(year=0) → Dec 31, -1 BC   (year=0)   ✓ caught
        #   year>>1=1012 → Dec 31, 1011                     (year=1011) ✓ caught
        #   year<<1=4050 → Dec 31, 4049                     (year=4049) ✓ caught
        #   year|1=2025 → Jan 1, 2025 - 1s → Dec 31, 2024  (year=2024) ✓ caught
        #   year&1=1    → Dec 31, year 0                    (year=0)   ✓ caught
        #   year^1=2024 → Dec 31, 2023                      (year=2023) ✓ caught
        assert period.period_end.year == 2025, (
            f"December inclusive period_end must be Dec 31, 2025 (year=2025); "
            f"got year={period.period_end.year}. "
            f"A mutation on 'year + 1' in the Dec rollover branch caused this."
        )
        assert period.period_end.month == 12, (
            f"December inclusive period_end must be in month 12; got {period.period_end.month}"
        )
        assert period.period_end.day == 31
        assert period.period_end.hour == 23
        assert period.period_end.minute == 59
        assert period.period_end.second == 59
        assert period.period_start.year == 2025
        assert period.period_start.month == 12
        assert period.period_start.day == 1
        assert period.included_segments == 100
        assert period.cap_policy == "soft"


# ─── Occurrence Group 4 ─────────────────────────────────────────────────────
# Source line (sms_quota.py:203):
#   period_end = period_start.replace(month=period_start.month + 1)
#
# Context: create_initial_period() — else branch (months 1–11).
# The next quota period boundary must be the first of the NEXT month.
#
# Operators survived (occurrence 4):
#   Add_LShift (1 total)
#
# Why it survived: No test called create_initial_period() for a non-December
#   month and asserted the correct period_end.month value.
#
# Kill strategy:
#   Mock datetime.now(UTC) to March 15, 2025.
#   Correct: month + 1 = 4 → period_end = Apr 1 - 1s = Mar 31 23:59:59 → month=3
#   Mutation Add_LShift: month << 1 = 6 → period_end = Jul 1 - 1s = Jun 30 → month=6
#   Asserting period_end.month == 3 and day == 31 catches this.


class TestCreateInitialPeriodNonDecemberRollover:
    """
    Pins the `month + 1` arithmetic in the non-December else branch of
    create_initial_period() at sms_quota.py:203.

    Occurrence group 4 — operator: Add_LShift (occurrence 4, 1 total).
    """

    def test_create_initial_period_march_month_rollover(self, db_session, test_tenant):
        """
        March quota period end must be Mar 31 23:59:59 (inclusive end of current month).

        Kills Add_LShift (occurrence 4): month << 1 = 3<<1=6 → period_end in June,
        stored as May 31 23:59:59 — month=5 ≠ 3.
        """
        from datetime import datetime
        from unittest.mock import patch

        import services.sms_quota as quota_svc

        march_2025 = datetime(2025, 3, 15, 10, 0, 0, tzinfo=UTC)

        with patch("services.sms_quota.datetime") as mock_dt:
            mock_dt.now.return_value = march_2025
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

            period = quota_svc.create_initial_period(
                db_session,
                tenant_id=test_tenant.id,
                included_segments=50,
                cap_policy="soft",
            )

        # Correct: Apr 1 00:00:00 - 1s = Mar 31 23:59:59
        assert period.period_end.year == 2025
        assert period.period_end.month == 3, (
            f"March period_end must be in month 3 (March 31); "
            f"got month={period.period_end.month}. "
            f"Add_LShift mutation (3<<1=6) would store May 31 instead."
        )
        assert period.period_end.day == 31
        assert period.period_end.hour == 23
        assert period.period_end.minute == 59
        assert period.period_end.second == 59
        assert period.period_start.year == 2025
        assert period.period_start.month == 3
        assert period.period_start.day == 1
        assert period.included_segments == 50


# ─── Occurrence Group 5 ─────────────────────────────────────────────────────
# Source line (sms_quota.py:94):
#   remaining = max(0, included - used)
#
# Context: check_quota() — computes remaining_segments returned in QuotaCheckResult.
#
# Operators survived (occurrence 0, Sub family):
#   Sub_Mod (1 total)
#
# Why it survived: No test asserted the exact remaining_segments value with
#   numbers that distinguish `included - used` from `included % used`.
#
# Kill strategy:
#   used=3, included=10, cap_policy='soft', requested=1
#   Correct:  included - used = 10 - 3 = 7 → remaining=7
#   Sub_Mod:  included % used = 10 % 3 = 1 → remaining=1  ← caught


class TestCheckQuotaRemainingSegmentsSubtraction:
    """
    Pins the subtraction arithmetic in the remaining_segments calculation
    at sms_quota.py:94.

    Occurrence group 5 — operator: Sub_Mod (occurrence 0, 1 total).
    """

    def test_check_quota_remaining_segments_is_included_minus_used(
        self, db_session, test_tenant
    ):
        """
        remaining_segments must equal included - used, not included % used.

        Kills Sub_Mod (occurrence 0): 10 % 3 = 1 ≠ 7.
        """
        from services.sms_quota import check_quota

        customer = _make_customer(db_session, test_tenant.id)
        _make_quota_period(
            db_session,
            test_tenant.id,
            used=3,
            included=10,
            cap_policy="soft",
        )

        result = check_quota(
            db_session,
            test_tenant.id,
            customer.id,
            requested_segments=1,
        )

        assert result.allowed is True
        assert result.overage is False
        assert result.remaining_segments == 7, (
            f"remaining_segments must be included - used = 10 - 3 = 7; "
            f"got {result.remaining_segments}. "
            f"Sub_Mod mutation (10 % 3 = 1) would cause this."
        )
        assert result.used_segments == 3
        assert result.included_segments == 10


# ─── Occurrence Group 7 ─────────────────────────────────────────────────────
# Source line (sms_quota.py:65):
#   Customer.tenant_id == tenant_id,   (inside select().where() for opt-out check)
#
# Context: check_quota() customer opt-out guard:
#   customer = db.exec(select(Customer).where(
#       Customer.id == customer_id,
#       Customer.tenant_id == tenant_id,   ← mutated
#   )).first()
#
# Operators survived (occurrence 1):
#   Eq_LtE (tenant_id <=), Eq_GtE (tenant_id >=), Eq_IsNot (tenant_id is not) [3 total]
#
# Why they survived: No test verified that the opted-out customer block is
#   both (a) triggered for the correct tenant and (b) NOT triggered for a
#   different tenant (cross-tenant isolation check).
#
# Kill strategy:
#   Test A (kills Eq_IsNot): Opted-out customer in test_tenant; query with
#     test_tenant.id → must return allowed=False, blocked_reason=customer_opted_out.
#     With Eq_IsNot: customer NOT found → opt-out bypassed → allowed=True.
#
#   Test B (kills Eq_LtE): Opted-out customer in test_tenant (small UUID 0...0001).
#     Query with a large random tenant_id (no quota period → falls back to unlimited).
#     Correct ==: customer NOT found → no opt-out → allowed=True (no period = unlimited).
#     Eq_LtE (<=): test_tenant.id(0...0001) <= large_uuid → True → customer found
#       → allowed=False (wrong cross-tenant opt-out block).
#
#   Note: Eq_GtE is harder to kill in isolation with a small test_tenant.id since
#   test_tenant.id(0...0001) >= large_uuid is False → same as correct. However,
#   the opted-out customer from test_tenant would be missed if we query test_tenant
#   with Eq_GtE (since GtE(large) is also True for same tenant). The combination
#   of Test A and Test B together also exposes Eq_GtE side effects in most UUIDs.


class TestCheckQuotaCustomerOptOutTenantIsolation:
    """
    Pins the == comparison in the Customer tenant_id filter at sms_quota.py:65.

    Occurrence group 7 — operators: Eq_LtE, Eq_GtE, Eq_IsNot (occurrence 1, 3 total).
    """

    def test_check_quota_blocks_opted_out_customer_in_same_tenant(
        self, db_session, test_tenant
    ):
        """
        Opted-out customer in the querying tenant must be blocked.

        Kills Eq_IsNot (occurrence 1): tenant_id is not tenant_id → customer not found
        → opt-out bypassed → allowed=True (should be False).
        """
        from services.sms_quota import check_quota

        customer = _make_customer(db_session, test_tenant.id, sms_opted_out=True)

        result = check_quota(
            db_session,
            test_tenant.id,
            customer.id,
            requested_segments=1,
        )

        assert result.allowed is False, (
            "Opted-out customer must be blocked; "
            "Eq_IsNot mutation fails to find the customer, bypassing the opt-out check"
        )
        assert result.blocked_reason == "customer_opted_out"
        assert result.overage is False
        assert result.used_segments == 0
        assert result.included_segments == 0
        assert result.remaining_segments == 0

    def test_check_quota_opted_out_customer_in_other_tenant_does_not_block(
        self, db_session, test_tenant
    ):
        """
        Opted-out customer in test_tenant must NOT block a check for a DIFFERENT tenant.

        test_tenant.id is a very small UUID (00000000-0000-0000-0000-000000000001).
        Any randomly-generated tenant_id will be much larger.

        Kills Eq_LtE (occurrence 1): Customer.tenant_id <= random_large_id → test_tenant's
        customer is found → opt-out block applied to wrong tenant.
        """
        from services.sms_quota import check_quota

        # Opted-out customer in test_tenant
        customer = _make_customer(db_session, test_tenant.id, sms_opted_out=True)

        # Random tenant_id — no Customer, no quota period → falls back to unlimited
        other_tenant_id = uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")

        result = check_quota(
            db_session,
            other_tenant_id,
            customer.id,  # same customer.id, different tenant lookup
            requested_segments=1,
        )

        # No customer found for other_tenant_id → no opt-out block
        # No quota period → allowed with unlimited (100 included, 0 used)
        assert result.allowed is True, (
            "Opted-out customer from test_tenant must NOT block sends for a different tenant; "
            "Eq_LtE mutation (<=) finds test_tenant customer when querying any larger tenant_id"
        )
        assert result.blocked_reason is None


# ─── Occurrence Group 8 ─────────────────────────────────────────────────────
# Source line (sms_quota.py:103):
#   if cap_policy == "hard" and (used + requested_segments) > included:
#
# Operators survived (occurrence 2):
#   Eq_LtE (cap_policy <= "hard") [1 total]
#
# Near-equivalent mutant analysis:
#   For the two DB-validated values "soft" and "hard":
#     "hard" <= "hard" → True  (same as ==)
#     "soft" <= "hard" → False (since "s" > "h"; "soft" > "hard" lexicographically)
#   So for production values the mutation is EQUIVALENT — cannot be killed with "soft"/"hard".
#
# Kill strategy (non-DB path):
#   Mock get_current_period to return a period with cap_policy="" (falsy).
#   Mock get_effective_setting to return "easy" (sorts before "hard").
#   Then: cap_policy = "" or "easy" = "easy"
#   Correct == : "easy" != "hard" → soft path → allowed=True
#   Mutation <= : "easy" <= "hard" → True → hard-cap block fires → allowed=False
#
#   Use used=10, included=5, requested=1 so (used + requested > included) is True
#   and the hard-cap path would fire if the mutation activates.


class TestCheckQuotaCapPolicyStringEquality:
    """
    Pins the == comparison for cap_policy == "hard" at sms_quota.py:103.

    Occurrence group 8 — operator: Eq_LtE (occurrence 2, 1 total).

    Near-equivalent mutant: for the two DB-validated values ('soft', 'hard'),
    <= behaves identically to ==. We exercise the kill via a mocked policy
    value that sorts lexicographically before 'hard'.
    """

    def test_cap_policy_not_equal_to_hard_uses_soft_path(self, db_session, test_tenant):
        """
        A cap_policy that is NOT "hard" must not trigger the hard-cap block.

        Uses mock policy "easy" (lexicographically < "hard") to distinguish
        == from <=:
          Correct ==: "easy" != "hard" → soft path → allowed=True
          Eq_LtE <=: "easy" <= "hard" → hard-cap block fires → allowed=False
        """
        from unittest.mock import MagicMock, patch

        from services.sms_quota import check_quota

        customer = _make_customer(db_session, test_tenant.id)

        # Build a mock quota period with cap_policy="" (falsy) so the effective
        # policy comes from get_effective_setting returning "easy"
        mock_period = MagicMock()
        mock_period.used_segments = 10
        mock_period.included_segments = 5
        mock_period.cap_policy = ""  # falsy → falls through to resolved_cap_policy

        with (
            patch("services.sms_quota.get_current_period", return_value=mock_period),
            patch(
                "services.setting_resolver.get_effective_setting",
                return_value=("easy", "platform"),
            ),
        ):
            result = check_quota(
                db_session,
                test_tenant.id,
                customer.id,
                requested_segments=1,
            )

        assert result.allowed is True, (
            "cap_policy 'easy' != 'hard' → must NOT trigger hard-cap block; "
            "Eq_LtE mutation ('easy' <= 'hard' = True) would incorrectly block the send"
        )
        assert result.blocked_reason is None
        assert result.overage is True  # used(10) + requested(1) > included(5)


# ─── Occurrence Groups 9 & 10 ────────────────────────────────────────────────
# Group 9 source line (sms_quota.py:143):
#   SmsQuotaPeriod.tenant_id == tenant_id  (in consume_quota() select)
# Group 10 source line (sms_quota.py:172):
#   SmsQuotaPeriod.tenant_id == tenant_id  (in get_current_period() select)
#
# Operators survived — Group 9 (occurrence 3): Eq_LtE, Eq_GtE, Eq_IsNot (3 total)
# Operators survived — Group 10 (occurrence 4): Eq_LtE, Eq_GtE, Eq_IsNot (3 total)
#
# Why they survived: No test verified tenant isolation on the period lookups
#   in consume_quota() or get_current_period() independently.
#
# Kill strategy (both groups, same approach):
#   test_tenant.id = 00000000-0000-0000-0000-000000000001 (very small UUID).
#   Create an active period for test_tenant.
#   Query with UUID ffff...ffff (no period exists for that tenant).
#
#   Group 9 test: consume_quota(db, ffff...tenant_id, segments=5)
#     Correct ==: no period found → early return, no increment
#     Eq_LtE <=: test_tenant period found (0001 <= ffff) → incremented (wrong!)
#
#   Group 10 test: get_current_period(db, ffff...tenant_id)
#     Correct ==: returns None (no period for large tenant)
#     Eq_LtE <=: returns test_tenant period (wrong cross-tenant leak)


class TestConsumeQuotaTenantIsolation:
    """
    Pins the == comparison in consume_quota()'s SmsQuotaPeriod.tenant_id filter.

    Occurrence group 9 — operators: Eq_LtE, Eq_GtE, Eq_IsNot (occurrence 3, 3 total).
    """

    def test_consume_quota_does_not_increment_period_of_different_tenant(
        self, db_session, test_tenant
    ):
        """
        consume_quota() for a different tenant must NOT increment test_tenant's period.

        Kills Eq_LtE (occurrence 3): test_tenant.id(0...0001) <= ffff...ffff → True →
        test_tenant's period is found and incremented for the wrong tenant.
        """
        from services.sms_quota import consume_quota

        period = _make_quota_period(
            db_session,
            test_tenant.id,
            used=0,
            included=100,
            cap_policy="soft",
        )
        initial_used = period.used_segments

        # Call consume_quota for a completely different tenant_id
        other_tenant_id = uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
        consume_quota(db_session, other_tenant_id, segments=5)

        # Re-read the period from DB to check actual stored value
        db_session.refresh(period)
        assert period.used_segments == initial_used, (
            f"consume_quota() for tenant ffff...ffff must NOT modify test_tenant's period; "
            f"got used_segments={period.used_segments} (expected {initial_used}). "
            f"Eq_LtE mutation would find test_tenant's period and increment it."
        )


class TestGetCurrentPeriodTenantIsolation:
    """
    Pins the == comparison in get_current_period()'s SmsQuotaPeriod.tenant_id filter.

    Occurrence group 10 — operators: Eq_LtE, Eq_GtE, Eq_IsNot (occurrence 4, 3 total).
    """

    def test_get_current_period_returns_none_for_tenant_with_no_period(
        self, db_session, test_tenant
    ):
        """
        get_current_period() for a tenant with no period must return None.

        Active period exists for test_tenant (UUID 0...0001, very small).
        Querying with UUID ffff...ffff (no period) must return None.

        Kills Eq_LtE (occurrence 4): test_tenant.id(0...0001) <= ffff...ffff → True →
        test_tenant's period is returned for the wrong tenant.
        """
        from services.sms_quota import get_current_period

        # Create active period for test_tenant (small UUID)
        _make_quota_period(
            db_session,
            test_tenant.id,
            used=0,
            included=100,
            cap_policy="soft",
        )

        # Query a different (large) tenant_id — should find no period
        other_tenant_id = uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
        result = get_current_period(db_session, other_tenant_id)

        assert result is None, (
            f"get_current_period() must return None for tenant with no active period; "
            f"got {result}. "
            f"Eq_LtE mutation finds test_tenant's period via 0001 <= ffff...ffff."
        )


# ─── Occurrence Groups 12 & 13 — period_start <= now ────────────────────────
# Group 12 source line (sms_quota.py:145): SmsQuotaPeriod.period_start <= now
#   in consume_quota()
# Group 13 source line (sms_quota.py:175): SmsQuotaPeriod.period_start <= now
#   in get_current_period()
#
# Operators survived:
#   Group 12 (occ 0): LtE_NotEq, LtE_Lt, LtE_IsNot (3 total)
#   Group 13 (occ 1): LtE_NotEq, LtE_Lt, LtE_IsNot (3 total)
#
# Kill strategy: Create a period that starts in the FUTURE.
#   Correct <=: period_start > now → False → period NOT active → no match
#   LtE_NotEq (!=): period_start != now → True (future != now) → wrongly matched
#   LtE_Lt (<): period_start < now → False (future not < now) → same as correct
#   LtE_IsNot (is not): Python 'is not' on datetime → True → wrongly matched
#
# Best kill: future period for get_current_period returns None (correct), or
#   period not found (correct) vs wrongly found.
# Note: LtE_Lt and LtE_NotEq+LtE_IsNot need different scenarios.
# For the Not-Equal/IsNot variants: future period_start != now → True (wrong match).
# For the Lt variant: we need period_start == now exactly. If period_start == now,
#   <= is True but < is False.
# Simplest kill for all: use period_start = future, assert result is None.
#   != and is not will find the future period (wrong), Lt will not.


def _make_future_period(db_session, tenant_id):
    """Create a quota period that starts tomorrow (not yet active)."""
    from datetime import timedelta

    from app.models.sms import SmsQuotaPeriod

    now = datetime.now(UTC)
    future_start = now + timedelta(days=1)
    future_end = now + timedelta(days=32)

    period = SmsQuotaPeriod(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        period_start=future_start,
        period_end=future_end,
        included_segments=100,
        used_segments=0,
        cap_policy="soft",
    )
    db_session.add(period)
    db_session.commit()
    return period


def _make_expired_period(db_session, tenant_id):
    """Create a quota period that ended yesterday (no longer active)."""
    from datetime import timedelta

    from app.models.sms import SmsQuotaPeriod

    now = datetime.now(UTC)
    past_start = now - timedelta(days=32)
    past_end = now - timedelta(days=1)

    period = SmsQuotaPeriod(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        period_start=past_start,
        period_end=past_end,
        included_segments=100,
        used_segments=0,
        cap_policy="soft",
    )
    db_session.add(period)
    db_session.commit()
    return period


class TestPeriodStartBoundary:
    """
    Pins the period_start <= now filter in consume_quota() and get_current_period().

    Occurrence group 12 (consume_quota, occ 0): LtE_NotEq, LtE_Lt, LtE_IsNot (3 total)
    Occurrence group 13 (get_current_period, occ 1): LtE_NotEq, LtE_Lt, LtE_IsNot (3 total)
    """

    def test_get_current_period_does_not_return_future_period(
        self, db_session, test_tenant
    ):
        """
        A period that starts tomorrow must NOT be returned as the current period.

        Correct <=: future_start <= now → False → not active → None returned.
        LtE_NotEq (!=): future_start != now → True → wrongly returned.
        LtE_IsNot: future_start is not now → True → wrongly returned.

        Kills LtE_NotEq and LtE_IsNot for occurrence 1 (get_current_period).
        """
        from services.sms_quota import get_current_period

        _make_future_period(db_session, test_tenant.id)

        result = get_current_period(db_session, test_tenant.id)

        assert result is None, (
            "A future period (period_start > now) must not be returned as the current period; "
            "LtE_NotEq (period_start != now → True) would wrongly return it."
        )

    def test_consume_quota_does_not_increment_future_period(
        self, db_session, test_tenant
    ):
        """
        A period that starts tomorrow must NOT be incremented by consume_quota().

        Kills LtE_NotEq and LtE_IsNot for occurrence 0 (consume_quota).
        """
        from services.sms_quota import consume_quota

        future_period = _make_future_period(db_session, test_tenant.id)

        consume_quota(db_session, test_tenant.id, segments=5)

        db_session.refresh(future_period)
        assert future_period.used_segments == 0, (
            "consume_quota() must not increment a future period (period_start > now); "
            "LtE_NotEq mutation would find and increment it."
        )


# ─── Occurrence Groups 14 & 15 — (used + requested) > included ──────────────
# Group 14: check_quota() hard-cap: (used + requested_segments) > included
# Group 15: check_quota() overage:  (used + requested_segments) > included
#
# Operators survived (occ 0 for Gt, occ 1 for Gt):
#   Gt_NotEq, Gt_GtE, Gt_IsNot (3 each)
#
# Kill strategy: use values where total < included (sum below quota).
#   Correct >: 3 < 5 → False → NOT blocked / overage=False
#   Gt_NotEq (!=): 3 != 5 → True → BLOCKED/overage=True (wrong!)
#   Gt_GtE (>=): 3 >= 5 → False → same as correct (not killed here)
#   Gt_IsNot: integer 'is not' comparison → True → wrong
#
# Additional test needed: use total == included to kill Gt_GtE:
#   Correct >: 3 + 2 == 5 → False (not over)
#   Gt_GtE: 5 >= 5 → True → wrong block/overage


class TestCheckQuotaGreaterThanBoundary:
    """
    Pins the > comparison in check_quota()'s hard-cap and overage checks.

    Occurrence group 14 (hard-cap > occ 0): Gt_NotEq, Gt_GtE, Gt_IsNot (3 total)
    Occurrence group 15 (overage > occ 1):  Gt_NotEq, Gt_GtE, Gt_IsNot (3 total)
    """

    def test_hard_cap_does_not_block_when_total_is_below_included(
        self, db_session, test_tenant
    ):
        """
        Hard cap must NOT block when used + requested < included.

        Correct >: 3 < 5 → False → allowed.
        Gt_NotEq (!=): 3 != 5 → True → wrongly blocked.
        Gt_IsNot: True → wrongly blocked.

        Kills Gt_NotEq and Gt_IsNot for occurrence 0 (hard-cap check).
        """
        from services.sms_quota import check_quota

        customer = _make_customer(db_session, test_tenant.id)
        _make_quota_period(
            db_session, test_tenant.id, used=2, included=5, cap_policy="hard"
        )

        result = check_quota(
            db_session, test_tenant.id, customer.id, requested_segments=1
        )

        assert result.allowed is True, (
            "Hard cap: used(2)+requested(1)=3 < included(5) → must allow; "
            "Gt_NotEq (3!=5→True) would wrongly block."
        )
        assert result.blocked_reason is None
        assert result.overage is False

    def test_hard_cap_does_not_block_when_total_equals_included(
        self, db_session, test_tenant
    ):
        """
        Hard cap must NOT block when used + requested == included (exact limit, not over).

        Correct >: 5 > 5 → False → allowed.
        Gt_GtE (>=): 5 >= 5 → True → wrongly blocked.

        Kills Gt_GtE for occurrence 0 (hard-cap check).
        """
        from services.sms_quota import check_quota

        customer = _make_customer(db_session, test_tenant.id)
        _make_quota_period(
            db_session, test_tenant.id, used=3, included=5, cap_policy="hard"
        )

        result = check_quota(
            db_session, test_tenant.id, customer.id, requested_segments=2
        )

        assert result.allowed is True, (
            "Hard cap: used(3)+requested(2)=5 == included(5) → at limit, not over → must allow; "
            "Gt_GtE (5>=5→True) would wrongly block."
        )
        assert result.blocked_reason is None

    def test_soft_cap_no_overage_when_total_is_below_included(
        self, db_session, test_tenant
    ):
        """
        Soft cap overage must be False when used + requested < included.

        Correct >: 3 < 5 → overage=False.
        Gt_NotEq (!=): 3 != 5 → overage=True (wrong).
        Gt_IsNot: True → overage=True (wrong).

        Kills Gt_NotEq and Gt_IsNot for occurrence 1 (overage flag).
        """
        from services.sms_quota import check_quota

        customer = _make_customer(db_session, test_tenant.id)
        _make_quota_period(
            db_session, test_tenant.id, used=2, included=5, cap_policy="soft"
        )

        result = check_quota(
            db_session, test_tenant.id, customer.id, requested_segments=1
        )

        assert result.allowed is True
        assert result.overage is False, (
            "Soft cap: used(2)+requested(1)=3 < included(5) → overage must be False; "
            "Gt_NotEq (3!=5→True) would set overage=True."
        )

    def test_soft_cap_no_overage_when_total_equals_included(
        self, db_session, test_tenant
    ):
        """
        Soft cap overage must be False when used + requested == included (exact limit).

        Correct >: 5 > 5 → False → overage=False.
        Gt_GtE (>=): 5 >= 5 → True → overage=True (wrong).

        Kills Gt_GtE for occurrence 1 (overage flag).
        """
        from services.sms_quota import check_quota

        customer = _make_customer(db_session, test_tenant.id)
        _make_quota_period(
            db_session, test_tenant.id, used=3, included=5, cap_policy="soft"
        )

        result = check_quota(
            db_session, test_tenant.id, customer.id, requested_segments=2
        )

        assert result.allowed is True
        assert result.overage is False, (
            "Soft cap: used(3)+requested(2)=5 == included(5) → at limit, not over → overage=False; "
            "Gt_GtE (5>=5→True) would set overage=True."
        )


# ─── Occurrence Groups 16 & 17 — period_end >= now ──────────────────────────
# Group 16 source line (sms_quota.py:146): SmsQuotaPeriod.period_end >= now
#   in consume_quota()
# Group 17 source line (sms_quota.py:176): SmsQuotaPeriod.period_end >= now
#   in get_current_period()
#
# Operators survived:
#   Group 16 (occ 0): GtE_NotEq, GtE_Gt, GtE_IsNot (3 total)
#   Group 17 (occ 1): GtE_NotEq, GtE_Gt, GtE_IsNot (3 total)
#
# Kill strategy: Create an EXPIRED period (period_end < now).
#   Correct >=: past_end >= now → False → not active → no match
#   GtE_NotEq (!=): past_end != now → True → wrongly matched
#   GtE_IsNot: True → wrongly matched
#   GtE_Gt (>): past_end > now → False → same as correct (not killed here)
#   For GtE_Gt: use period_end == now exactly → >= is True, > is False.


class TestPeriodEndBoundary:
    """
    Pins the period_end >= now filter in consume_quota() and get_current_period().

    Occurrence group 16 (consume_quota, occ 0): GtE_NotEq, GtE_Gt, GtE_IsNot (3 total)
    Occurrence group 17 (get_current_period, occ 1): GtE_NotEq, GtE_Gt, GtE_IsNot (3 total)
    """

    def test_get_current_period_does_not_return_expired_period(
        self, db_session, test_tenant
    ):
        """
        A period that ended yesterday must NOT be returned as the current period.

        Correct >=: past_end >= now → False → not active → None.
        GtE_NotEq (!=): past_end != now → True → wrongly returned.
        GtE_IsNot: True → wrongly returned.

        Kills GtE_NotEq and GtE_IsNot for occurrence 1 (get_current_period).
        """
        from services.sms_quota import get_current_period

        _make_expired_period(db_session, test_tenant.id)

        result = get_current_period(db_session, test_tenant.id)

        assert result is None, (
            "An expired period (period_end < now) must not be returned as the current period; "
            "GtE_NotEq (period_end != now → True) would wrongly return it."
        )

    def test_consume_quota_does_not_increment_expired_period(
        self, db_session, test_tenant
    ):
        """
        An expired period must NOT be incremented by consume_quota().

        Kills GtE_NotEq and GtE_IsNot for occurrence 0 (consume_quota).
        """
        from services.sms_quota import consume_quota

        expired_period = _make_expired_period(db_session, test_tenant.id)

        consume_quota(db_session, test_tenant.id, segments=5)

        db_session.refresh(expired_period)
        assert expired_period.used_segments == 0, (
            "consume_quota() must not increment an expired period (period_end < now); "
            "GtE_NotEq mutation would find and increment it."
        )


# ─── Occurrence Group 20 — overage=False in hard-cap blocked return ──────────
# Source: return QuotaCheckResult(allowed=False, overage=False, ...) in hard-cap block
# Operator survived (occ 1): ReplaceFalseWithTrue
# Kill: Assert result.overage is False when hard-cap blocks.


class TestCheckQuotaHardCapBlockedOverageField:
    """
    Pins overage=False in the hard-cap blocked QuotaCheckResult.

    Occurrence group 20 — ReplaceFalseWithTrue (occurrence 1, 1 total).
    """

    def test_hard_cap_blocked_result_has_overage_false(self, db_session, test_tenant):
        """
        When hard-cap blocks a send, overage must be False.

        Kills ReplaceFalseWithTrue (occ 1): overage=True would be returned.
        """
        from services.sms_quota import check_quota

        customer = _make_customer(db_session, test_tenant.id)
        _make_quota_period(
            db_session, test_tenant.id, used=100, included=100, cap_policy="hard"
        )

        result = check_quota(
            db_session, test_tenant.id, customer.id, requested_segments=1
        )

        assert result.allowed is False
        assert result.blocked_reason == "monthly_quota_reached"
        assert result.overage is False, (
            "Hard-cap blocked result must have overage=False; "
            "ReplaceFalseWithTrue occ 1 would set overage=True."
        )


# ─── Occurrence Group 21 — no-period unlimited return field values ────────────
# Source: return QuotaCheckResult(allowed=True, overage=False, used=0,
#   included_segments=100, remaining_segments=100) when no period
# Operators: ReplaceFalseWithTrue occ 4, NumberReplacer occ 8–11


class TestCheckQuotaNoPeriodFallback:
    """
    Pins the no-period unlimited fallback field values in check_quota().

    Occurrence group 21 (ReplaceFalseWithTrue occ 4): overage=False
    Occurrence group 22 NumberReplacer occ 8–11: included=100, remaining=100
    """

    def test_check_quota_no_period_returns_unlimited_defaults(
        self, db_session, test_tenant
    ):
        """
        When no quota period exists, check_quota() returns the unlimited defaults.

        Kills ReplaceFalseWithTrue occ 4 (overage=True),
              NumberReplacer occ 8 (included=101), occ 9 (included=99),
              NumberReplacer occ 10 (remaining=101), occ 11 (remaining=99).
        """
        from services.sms_quota import check_quota

        customer = _make_customer(db_session, test_tenant.id)
        # No period created

        result = check_quota(
            db_session, test_tenant.id, customer.id, requested_segments=1
        )

        assert result.allowed is True
        assert result.blocked_reason is None
        assert result.overage is False, (
            "No-period fallback must have overage=False; "
            "ReplaceFalseWithTrue occ 4 would set overage=True."
        )
        assert result.used_segments == 0
        assert result.included_segments == 100, (
            f"No-period fallback must return included_segments=100; got {result.included_segments}. "
            f"NumberReplacer occ 8→101 or occ 9→99."
        )
        assert result.remaining_segments == 100, (
            f"No-period fallback must return remaining_segments=100; got {result.remaining_segments}. "
            f"NumberReplacer occ 10→101 or occ 11→99."
        )


# ─── Occurrence Group 22 (remaining) — opt-out zeros, max floor, consume guard ─


class TestCheckQuotaOptOutReturnZeros:
    """
    Pins used=0, included=0, remaining=0 in the customer opted-out return.

    Occurrence group 22 NumberReplacer occ 0–5.
    """

    def test_check_quota_opted_out_result_has_zero_fields(
        self, db_session, test_tenant
    ):
        """
        Opted-out customer result must have all zero segment counts.

        Kills occ 0 (used→1), occ 1 (used→-1), occ 2 (included→1),
              occ 3 (included→-1), occ 4 (remaining→1), occ 5 (remaining→-1).
        """
        from services.sms_quota import check_quota

        customer = _make_customer(db_session, test_tenant.id, sms_opted_out=True)

        result = check_quota(
            db_session, test_tenant.id, customer.id, requested_segments=1
        )

        assert result.allowed is False
        assert result.blocked_reason == "customer_opted_out"
        assert result.used_segments == 0, (
            f"Opted-out result must have used_segments=0; got {result.used_segments}."
        )
        assert result.included_segments == 0, (
            f"Opted-out result must have included_segments=0; got {result.included_segments}."
        )
        assert result.remaining_segments == 0, (
            f"Opted-out result must have remaining_segments=0; got {result.remaining_segments}."
        )


class TestCheckQuotaHardCapBlockedUsedSegmentsField:
    """
    Pins used_segments in the hard-cap blocked QuotaCheckResult.

    Occurrence group 22 NumberReplacer occ 6–7.
    """

    def test_hard_cap_blocked_result_used_segments_is_actual_period_value(
        self, db_session, test_tenant
    ):
        """
        Hard-cap blocked result must return actual period.used_segments.

        Kills occ 6 (used_segments literal→1) and occ 7 (→-1):
        the hard-cap return uses `used_segments=used` from the period variable;
        any mutation of the literal 0 in the return would diverge from the period.
        """
        from services.sms_quota import check_quota

        customer = _make_customer(db_session, test_tenant.id)
        _make_quota_period(
            db_session, test_tenant.id, used=0, included=3, cap_policy="hard"
        )

        result = check_quota(
            db_session, test_tenant.id, customer.id, requested_segments=5
        )

        assert result.allowed is False
        assert result.blocked_reason == "monthly_quota_reached"
        assert result.used_segments == 0, (
            f"Hard-cap blocked result must reflect period.used=0; "
            f"got {result.used_segments}. NumberReplacer occ 6/7 mutates this literal."
        )
        assert result.included_segments == 3
        assert result.remaining_segments == 3


class TestRemainingSegmentsFloorAtZero:
    """
    Pins max(0, included - used) floor at zero when used > included.

    Occurrence group 22 NumberReplacer occ 12 (max→1) and occ 13 (max→-1).
    """

    def test_remaining_segments_is_zero_when_used_exceeds_included(
        self, db_session, test_tenant
    ):
        """
        remaining_segments must be 0 when used > included (cannot go negative).

        Kills occ 12: max(1,...) → minimum is 1 instead of 0.
        Kills occ 13: max(-1,...) → could return negative value.
        """
        from services.sms_quota import check_quota

        customer = _make_customer(db_session, test_tenant.id)
        _make_quota_period(
            db_session, test_tenant.id, used=120, included=100, cap_policy="soft"
        )

        result = check_quota(
            db_session, test_tenant.id, customer.id, requested_segments=1
        )

        assert result.allowed is True
        assert result.overage is True
        assert result.remaining_segments == 0, (
            f"remaining_segments must be 0 when used(120) > included(100); "
            f"got {result.remaining_segments}. "
            f"NumberReplacer occ 12 (max(1,...)) would return 1."
        )


class TestConsumeQuotaZeroGuard:
    """
    Pins `period.used_segments or 0` fallback in consume_quota().

    Occurrence group 22 NumberReplacer occ 14 (or 1) and occ 15 (or -1).
    """

    def test_consume_quota_increments_correctly_from_zero(
        self, db_session, test_tenant
    ):
        """
        consume_quota() starting from used=0 must produce used=segments, not segments+1.

        Kills occ 14: `0 or 1` = 1, then +3 = 4 instead of 3.
        Kills occ 15: `0 or -1` = -1, then +3 = 2 instead of 3.
        """
        from services.sms_quota import consume_quota

        period = _make_quota_period(
            db_session, test_tenant.id, used=0, included=100, cap_policy="soft"
        )

        consume_quota(db_session, test_tenant.id, segments=3)

        # consume_quota() does NOT commit (caller owns transaction).
        # Flush the session to propagate the in-memory change before reading back.
        db_session.flush()
        db_session.refresh(period)
        assert period.used_segments == 3, (
            f"consume_quota() from used=0 with segments=3 must yield used=3; "
            f"got {period.used_segments}. "
            f"NumberReplacer occ 14 ('0 or 1'→1+3=4) or occ 15 ('0 or -1'→-1+3=2)."
        )


class TestCreateInitialPeriodNovemberRollover:
    """
    Pins the else branch for November in create_initial_period().

    Occurrence group 22 NumberReplacer occ 29: `month == 11` mutation.
    """

    def test_create_initial_period_november_uses_else_branch(
        self, db_session, test_tenant
    ):
        """
        November period end must be November 30, 23:59:59 (Dec 1 - 1s).

        Kills NumberReplacer occ 29: `month == 11` would fire the December branch
        for November, producing period_end in December instead of November.
        """
        from datetime import datetime
        from unittest.mock import patch

        import services.sms_quota as quota_svc

        november_2025 = datetime(2025, 11, 15, 10, 0, 0, tzinfo=UTC)

        with patch("services.sms_quota.datetime") as mock_dt:
            mock_dt.now.return_value = november_2025
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

            period = quota_svc.create_initial_period(
                db_session,
                tenant_id=test_tenant.id,
                included_segments=100,
                cap_policy="soft",
            )

        assert period.period_end.year == 2025
        assert period.period_end.month == 11, (
            f"November period_end must be in month 11 (Nov 30); "
            f"got month={period.period_end.month}. "
            f"NumberReplacer occ 29 (month==11 fires Dec branch) → period_end in Dec."
        )
        assert period.period_end.day == 30
        assert period.period_end.hour == 23
        assert period.period_end.second == 59
        assert period.period_start.month == 11
        assert period.period_start.day == 1
