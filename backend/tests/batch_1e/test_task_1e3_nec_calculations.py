"""
Task 1-E-3: NEC Code Assistance — Handler Completion Tests

Verifies the NEC calculation handlers in `services/voice_action_router.py`:

  A. Math Accuracy  — calculate_nec_voltage_drop returns exact physics-accurate values.
  B. State Persistence — ConversationSession.context_window_json.current_technical_context
                         is updated after a successful calculation.
  C. Conduit Fill Accuracy — calculate_conduit_fill correctly flags is_compliant
                              based on the 40% NEC Chapter 9 Table 1 threshold.

Reference: dev-docs/analysis/db-schema-domain-mvp-features-impl-plan.md Task 1-E-3
Batch: 1-E
"""

import uuid
from datetime import UTC, datetime

import pytest

from api.schemas.voice import (
    ContextWindowSchema,
    NecConduitFillArgs,
    NecVoltageDropArgs,
)
from app.models.ai import ConversationSession
from services.voice_action_router import (
    _AWG_CIRCULAR_MILS,
    _AWG_WIRE_AREA_SQ_IN,
    _CONDUIT_AREA_SQ_IN,
    _normalize_gauge,
    calculate_conduit_fill,
    calculate_nec_voltage_drop,
)

# ============================================================
# Seed helpers
# ============================================================


def _seed_active_session(db_session, test_tenant, test_user) -> ConversationSession:
    """
    Create and persist an active ConversationSession for the test tenant/user.
    Used as the 'session' argument passed to Voice AI handlers.
    """
    session = ConversationSession(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        user_id=test_user.id,
        status="active",
        context_window_json=None,
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    return session


class _FakeUserContext:
    """Minimal stand-in for AuthenticatedUser / TestUserContext in handler calls."""

    def __init__(self, tenant_id: uuid.UUID, user_id: uuid.UUID):
        self.id = user_id
        self.user_id = user_id
        self.tenant_id = tenant_id


# ============================================================
# Unit Tests — Schema Models (sanity checks on Pydantic models)
# ============================================================


class TestNecSchemas:
    """Verify that the Pydantic input/output models behave as specified."""

    def test_nec_voltage_drop_args_defaults(self):
        """NecVoltageDropArgs applies correct defaults for voltage and phase."""
        args = NecVoltageDropArgs(amperage=20.0, distance_feet=100.0, wire_gauge="12")
        assert args.voltage == 120.0
        assert args.phase == 1

    def test_nec_voltage_drop_args_rejects_zero_amperage(self):
        """NecVoltageDropArgs must reject amperage ≤ 0."""
        with pytest.raises(Exception):
            NecVoltageDropArgs(amperage=0, distance_feet=100.0, wire_gauge="12")

    def test_nec_voltage_drop_args_rejects_zero_distance(self):
        """NecVoltageDropArgs must reject distance_feet ≤ 0."""
        with pytest.raises(Exception):
            NecVoltageDropArgs(amperage=20.0, distance_feet=0, wire_gauge="12")

    def test_nec_conduit_fill_args_defaults(self):
        """NecConduitFillArgs defaults conduit_type to 'EMT'."""
        args = NecConduitFillArgs(
            conduit_trade_size="3/4",
            wire_gauge="12",
            num_conductors=3,
        )
        assert args.conduit_type == "EMT"

    def test_nec_conduit_fill_args_rejects_zero_conductors(self):
        """NecConduitFillArgs must reject num_conductors < 1."""
        with pytest.raises(Exception):
            NecConduitFillArgs(
                conduit_trade_size="3/4",
                wire_gauge="12",
                num_conductors=0,
            )

    def test_normalize_gauge_strips_awg_suffix(self):
        """_normalize_gauge handles '12 AWG', '12awg', '#12', '12 gauge' → '12'."""
        assert _normalize_gauge("12 AWG") == "12"
        assert _normalize_gauge("12awg") == "12"
        assert _normalize_gauge("#12") == "12"
        assert _normalize_gauge("12 gauge") == "12"
        assert _normalize_gauge("1/0") == "1/0"

    def test_awg_circular_mils_table_spot_check(self):
        """Key AWG gauges must have correct circular mil values (NEC reference)."""
        assert _AWG_CIRCULAR_MILS["12"] == 6530.0
        assert _AWG_CIRCULAR_MILS["10"] == 10380.0
        assert _AWG_CIRCULAR_MILS["8"] == 16510.0

    def test_awg_wire_area_table_spot_check(self):
        """Key wire area values must match NEC Chapter 9 Table 5 (THHN)."""
        assert _AWG_WIRE_AREA_SQ_IN["12"] == pytest.approx(0.0133, rel=1e-3)
        assert _AWG_WIRE_AREA_SQ_IN["10"] == pytest.approx(0.0211, rel=1e-3)

    def test_emt_conduit_area_three_quarter_inch(self):
        """3/4\" EMT internal area must be 0.533 sq in (NEC Chapter 9 Table 4)."""
        assert _CONDUIT_AREA_SQ_IN["EMT"]["3/4"] == pytest.approx(0.533, rel=1e-3)


# ============================================================
# Test A — Math Accuracy
# ============================================================


class TestNecVoltageDropMath:
    """
    Test A: Verify the voltage drop handler produces physics-accurate results.

    Known-good test vector (single-phase copper):
        I = 20 A, D = 100 ft, AWG 12 (CM = 6530), V = 120V, phase = 1
        Formula: V_D = (2 × 12.9 × 20 × 100) / 6530
                     = 51600 / 6530
                     ≈ 7.9021 V
        Pct:     7.9021 / 120 × 100 ≈ 6.585 %
        Compliance: 6.585 > 3.0 → NOT compliant
    """

    # Pre-computed expected values (double-checked against NEC formula)
    _K = 12.9
    _I = 20.0
    _D = 100.0
    _CM_12AWG = 6530.0
    _V = 120.0
    _EXPECTED_DROP = round((2 * _K * _I * _D) / _CM_12AWG, 4)
    _EXPECTED_PCT = round((_EXPECTED_DROP / _V) * 100, 4)

    @pytest.mark.asyncio
    async def test_voltage_drop_returns_success(
        self, db_session, test_tenant, test_user
    ):
        """Handler returns success=True for valid inputs."""
        session = _seed_active_session(db_session, test_tenant, test_user)
        user_ctx = _FakeUserContext(test_tenant.id, test_user.id)

        result = await calculate_nec_voltage_drop(
            entities={
                "amperage": 20.0,
                "distance_feet": 100.0,
                "wire_gauge": "12 AWG",
                "voltage": 120.0,
                "phase": 1,
            },
            current_user=user_ctx,
            db=db_session,
            session=session,
        )

        assert result["success"] is True
        assert result["action"] == "calculate_voltage_drop"

    @pytest.mark.asyncio
    async def test_voltage_drop_exact_volts(self, db_session, test_tenant, test_user):
        """
        voltage_drop value must match the NEC single-phase formula exactly.

        V_D = (2 × 12.9 × 20 × 100) / 6530 ≈ 7.9021 V
        """
        session = _seed_active_session(db_session, test_tenant, test_user)
        user_ctx = _FakeUserContext(test_tenant.id, test_user.id)

        result = await calculate_nec_voltage_drop(
            entities={
                "amperage": self._I,
                "distance_feet": self._D,
                "wire_gauge": "12",
                "voltage": self._V,
                "phase": 1,
            },
            current_user=user_ctx,
            db=db_session,
            session=session,
        )

        data = result["data"]
        assert data["voltage_drop"] == pytest.approx(self._EXPECTED_DROP, rel=1e-4), (
            f"Expected {self._EXPECTED_DROP}V, got {data['voltage_drop']}V"
        )

    @pytest.mark.asyncio
    async def test_voltage_drop_pct_exact(self, db_session, test_tenant, test_user):
        """
        voltage_drop_pct must equal (voltage_drop / voltage) × 100 rounded to 4dp.

        For 20A, 100ft, 12 AWG, 120V → ≈ 6.5854%
        """
        session = _seed_active_session(db_session, test_tenant, test_user)
        user_ctx = _FakeUserContext(test_tenant.id, test_user.id)

        result = await calculate_nec_voltage_drop(
            entities={
                "amperage": self._I,
                "distance_feet": self._D,
                "wire_gauge": "12",
                "voltage": self._V,
                "phase": 1,
            },
            current_user=user_ctx,
            db=db_session,
            session=session,
        )

        data = result["data"]
        assert data["voltage_drop_pct"] == pytest.approx(
            self._EXPECTED_PCT, rel=1e-4
        ), f"Expected {self._EXPECTED_PCT}%, got {data['voltage_drop_pct']}%"

    @pytest.mark.asyncio
    async def test_voltage_drop_non_compliant_for_long_run(
        self, db_session, test_tenant, test_user
    ):
        """
        20A on 100ft of 12 AWG at 120V exceeds the 3% NEC threshold.
        is_compliant must be False.
        """
        session = _seed_active_session(db_session, test_tenant, test_user)
        user_ctx = _FakeUserContext(test_tenant.id, test_user.id)

        result = await calculate_nec_voltage_drop(
            entities={
                "amperage": 20.0,
                "distance_feet": 100.0,
                "wire_gauge": "12",
                "voltage": 120.0,
                "phase": 1,
            },
            current_user=user_ctx,
            db=db_session,
            session=session,
        )

        # 6.59% >> 3% → not compliant
        assert result["data"]["is_compliant"] is False

    @pytest.mark.asyncio
    async def test_voltage_drop_compliant_for_short_run(
        self, db_session, test_tenant, test_user
    ):
        """
        20A on 10ft of 12 AWG at 120V is well within the 3% NEC threshold.
        is_compliant must be True.

        V_D = (2 × 12.9 × 20 × 10) / 6530 ≈ 0.7902V → 0.66% → compliant
        """
        session = _seed_active_session(db_session, test_tenant, test_user)
        user_ctx = _FakeUserContext(test_tenant.id, test_user.id)

        result = await calculate_nec_voltage_drop(
            entities={
                "amperage": 20.0,
                "distance_feet": 10.0,
                "wire_gauge": "12",
                "voltage": 120.0,
                "phase": 1,
            },
            current_user=user_ctx,
            db=db_session,
            session=session,
        )

        assert result["data"]["is_compliant"] is True
        assert result["data"]["voltage_drop_pct"] == pytest.approx(0.659, rel=1e-2)

    @pytest.mark.asyncio
    async def test_voltage_drop_three_phase_uses_sqrt3_multiplier(
        self, db_session, test_tenant, test_user
    ):
        """
        Three-phase formula uses 1.732 multiplier instead of 2.0.
        For same inputs, three-phase drop < single-phase drop.

        V_D_3ph = (1.732 × 12.9 × 20 × 100) / 6530 ≈ 6.836V
        V_D_1ph = (2.0 × 12.9 × 20 × 100) / 6530 ≈ 7.902V
        """
        session_1ph = _seed_active_session(db_session, test_tenant, test_user)
        session_3ph = _seed_active_session(db_session, test_tenant, test_user)
        user_ctx = _FakeUserContext(test_tenant.id, test_user.id)

        result_1ph = await calculate_nec_voltage_drop(
            entities={
                "amperage": 20.0,
                "distance_feet": 100.0,
                "wire_gauge": "12",
                "voltage": 120.0,
                "phase": 1,
            },
            current_user=user_ctx,
            db=db_session,
            session=session_1ph,
        )
        result_3ph = await calculate_nec_voltage_drop(
            entities={
                "amperage": 20.0,
                "distance_feet": 100.0,
                "wire_gauge": "12",
                "voltage": 120.0,
                "phase": 3,
            },
            current_user=user_ctx,
            db=db_session,
            session=session_3ph,
        )

        drop_1ph = result_1ph["data"]["voltage_drop"]
        drop_3ph = result_3ph["data"]["voltage_drop"]

        # Three-phase drop must be less than single-phase
        assert drop_3ph < drop_1ph, (
            f"Three-phase drop {drop_3ph} should be < single-phase {drop_1ph}"
        )

        # Verify the √3 ratio (3ph_drop / 1ph_drop ≈ 1.732 / 2.0 ≈ 0.866)
        ratio = drop_3ph / drop_1ph
        assert ratio == pytest.approx(1.732 / 2.0, rel=1e-3)

    @pytest.mark.asyncio
    async def test_voltage_drop_invalid_gauge_returns_error(
        self, db_session, test_tenant, test_user
    ):
        """Unsupported wire gauge returns success=False with an informative message."""
        session = _seed_active_session(db_session, test_tenant, test_user)
        user_ctx = _FakeUserContext(test_tenant.id, test_user.id)

        result = await calculate_nec_voltage_drop(
            entities={
                "amperage": 20.0,
                "distance_feet": 100.0,
                "wire_gauge": "99 AWG",
                "voltage": 120.0,
                "phase": 1,
            },
            current_user=user_ctx,
            db=db_session,
            session=session,
        )

        assert result["success"] is False
        assert "99" in result["error"] or "99" in result["message"]

    @pytest.mark.asyncio
    async def test_voltage_drop_missing_amperage_returns_error(
        self, db_session, test_tenant, test_user
    ):
        """Zero amperage (from missing entity) returns a validation error."""
        session = _seed_active_session(db_session, test_tenant, test_user)
        user_ctx = _FakeUserContext(test_tenant.id, test_user.id)

        result = await calculate_nec_voltage_drop(
            entities={
                # amperage omitted → defaults to 0 → fails gt=0 validation
                "distance_feet": 100.0,
                "wire_gauge": "12",
            },
            current_user=user_ctx,
            db=db_session,
            session=session,
        )

        assert result["success"] is False


# ============================================================
# Test B — State Persistence
# ============================================================


class TestNecVoltageDropStatePersistence:
    """
    Test B: After a successful calculation, the active ConversationSession must have
    its current_technical_context updated with the wire specs and result.
    """

    @pytest.mark.asyncio
    async def test_context_window_updated_after_voltage_drop(
        self, db_session, test_tenant, test_user
    ):
        """
        After calculate_nec_voltage_drop completes, re-fetching the ConversationSession
        from the DB must show current_technical_context populated with wire specs.
        """
        session = _seed_active_session(db_session, test_tenant, test_user)
        session_id = session.id
        user_ctx = _FakeUserContext(test_tenant.id, test_user.id)

        result = await calculate_nec_voltage_drop(
            entities={
                "amperage": 20.0,
                "distance_feet": 100.0,
                "wire_gauge": "12 AWG",
                "voltage": 120.0,
                "phase": 1,
            },
            current_user=user_ctx,
            db=db_session,
            session=session,
        )

        assert result["success"] is True

        # Re-fetch from DB to verify persistence
        db_session.expire_all()
        updated_session = db_session.get(ConversationSession, session_id)
        assert updated_session is not None

        ctx = ContextWindowSchema.from_jsonb(updated_session.context_window_json)
        tech_ctx = ctx.current_technical_context

        # Must contain the wire gauge and key calculated values
        assert "wire_gauge" in tech_ctx, (
            "wire_gauge missing from current_technical_context"
        )
        assert "12" in tech_ctx["wire_gauge"], (
            f"Expected '12' in wire_gauge, got {tech_ctx['wire_gauge']}"
        )
        assert "amperage" in tech_ctx
        assert tech_ctx["amperage"] == 20.0
        assert "distance_feet" in tech_ctx
        assert tech_ctx["distance_feet"] == 100.0
        assert "voltage_drop_pct" in tech_ctx
        assert "voltage_drop_compliant" in tech_ctx
        assert tech_ctx["last_nec_calculation"] == "voltage_drop"

    @pytest.mark.asyncio
    async def test_last_action_set_to_calculate_voltage_drop(
        self, db_session, test_tenant, test_user
    ):
        """
        ContextWindowSchema.last_action must be 'calculate_voltage_drop'
        after the handler runs.
        """
        session = _seed_active_session(db_session, test_tenant, test_user)
        session_id = session.id
        user_ctx = _FakeUserContext(test_tenant.id, test_user.id)

        await calculate_nec_voltage_drop(
            entities={
                "amperage": 20.0,
                "distance_feet": 50.0,
                "wire_gauge": "10",
                "voltage": 120.0,
            },
            current_user=user_ctx,
            db=db_session,
            session=session,
        )

        db_session.expire_all()
        updated_session = db_session.get(ConversationSession, session_id)
        ctx = ContextWindowSchema.from_jsonb(updated_session.context_window_json)
        assert ctx.last_action == "calculate_voltage_drop"

    @pytest.mark.asyncio
    async def test_context_preserves_existing_loto_state(
        self, db_session, test_tenant, test_user
    ):
        """
        Running a voltage drop calculation must NOT reset safety_loto_verified.
        The LOTO flag is only reset when a new job/customer context is established,
        not when a technical calculation is run.
        """
        # Pre-seed session with LOTO verified = True
        session = _seed_active_session(db_session, test_tenant, test_user)
        ctx = ContextWindowSchema()
        ctx.safety_loto_verified = True
        ctx.last_action = "loto_confirmed"
        session.context_window_json = ctx.to_jsonb()
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)

        session_id = session.id
        user_ctx = _FakeUserContext(test_tenant.id, test_user.id)

        await calculate_nec_voltage_drop(
            entities={
                "amperage": 15.0,
                "distance_feet": 50.0,
                "wire_gauge": "12",
                "voltage": 120.0,
            },
            current_user=user_ctx,
            db=db_session,
            session=session,
        )

        db_session.expire_all()
        updated_session = db_session.get(ConversationSession, session_id)
        ctx_after = ContextWindowSchema.from_jsonb(updated_session.context_window_json)

        # LOTO should still be True — NEC calculations don't touch this flag
        assert ctx_after.safety_loto_verified is True, (
            "safety_loto_verified was incorrectly reset by a voltage drop calculation"
        )

    @pytest.mark.asyncio
    async def test_context_window_updated_after_conduit_fill(
        self, db_session, test_tenant, test_user
    ):
        """
        After calculate_conduit_fill completes, the ConversationSession must have
        current_technical_context populated with conduit specs.
        """
        session = _seed_active_session(db_session, test_tenant, test_user)
        session_id = session.id
        user_ctx = _FakeUserContext(test_tenant.id, test_user.id)

        result = await calculate_conduit_fill(
            entities={
                "conduit_trade_size": "3/4",
                "conduit_type": "EMT",
                "wire_gauge": "12 AWG",
                "num_conductors": 3,
            },
            current_user=user_ctx,
            db=db_session,
            session=session,
        )

        assert result["success"] is True

        db_session.expire_all()
        updated_session = db_session.get(ConversationSession, session_id)
        ctx = ContextWindowSchema.from_jsonb(updated_session.context_window_json)
        tech_ctx = ctx.current_technical_context

        assert tech_ctx["last_nec_calculation"] == "conduit_fill"
        assert "fill_pct" in tech_ctx
        assert "conduit_fill_compliant" in tech_ctx
        assert "wire_gauge" in tech_ctx
        assert ctx.last_action == "calculate_conduit_fill"


# ============================================================
# Test C — Conduit Fill Accuracy
# ============================================================


class TestNecConduitFillAccuracy:
    """
    Test C: Verify conduit fill calculations use correct NEC Chapter 9 Table 1 rules.

    Key compliance thresholds:
        1 conductor  → 53% max
        2 conductors → 31% max
        3+ conductors → 40% max  (most common case)

    Known-good test vectors (3/4\" EMT, THHN):
        3 × 12 AWG: area = 3 × 0.0133 = 0.0399 sq in
                    conduit = 0.533 sq in
                    fill = 0.0399 / 0.533 × 100 ≈ 7.49% → COMPLIANT (< 40%)

        6 × 10 AWG: area = 6 × 0.0211 = 0.1266 sq in
                    conduit = 0.533 sq in
                    fill = 0.1266 / 0.533 × 100 ≈ 23.75% → COMPLIANT

        9 × 8 AWG:  area = 9 × 0.0366 = 0.3294 sq in
                    conduit = 0.533 sq in
                    fill = 0.3294 / 0.533 × 100 ≈ 61.8% → NOT COMPLIANT (> 40%)
    """

    @pytest.mark.asyncio
    async def test_conduit_fill_returns_success(
        self, db_session, test_tenant, test_user
    ):
        """Handler returns success=True for valid inputs."""
        session = _seed_active_session(db_session, test_tenant, test_user)
        user_ctx = _FakeUserContext(test_tenant.id, test_user.id)

        result = await calculate_conduit_fill(
            entities={
                "conduit_trade_size": "3/4",
                "conduit_type": "EMT",
                "wire_gauge": "12",
                "num_conductors": 3,
            },
            current_user=user_ctx,
            db=db_session,
            session=session,
        )

        assert result["success"] is True
        assert result["action"] == "calculate_conduit_fill"

    @pytest.mark.asyncio
    async def test_three_12awg_in_three_quarter_emt_is_compliant(
        self, db_session, test_tenant, test_user
    ):
        """
        3 × 12 AWG in 3/4\" EMT:
          fill ≈ 7.49% < 40% → is_compliant = True
        """
        session = _seed_active_session(db_session, test_tenant, test_user)
        user_ctx = _FakeUserContext(test_tenant.id, test_user.id)

        result = await calculate_conduit_fill(
            entities={
                "conduit_trade_size": "3/4",
                "conduit_type": "EMT",
                "wire_gauge": "12",
                "num_conductors": 3,
            },
            current_user=user_ctx,
            db=db_session,
            session=session,
        )

        data = result["data"]
        assert data["is_compliant"] is True
        assert data["max_fill_pct"] == 40.0
        assert data["fill_pct"] == pytest.approx(
            (3 * _AWG_WIRE_AREA_SQ_IN["12"]) / _CONDUIT_AREA_SQ_IN["EMT"]["3/4"] * 100,
            rel=1e-3,
        )

    @pytest.mark.asyncio
    async def test_nine_8awg_in_three_quarter_emt_not_compliant(
        self, db_session, test_tenant, test_user
    ):
        """
        9 × 8 AWG in 3/4\" EMT:
          fill ≈ 61.8% > 40% → is_compliant = False
        """
        session = _seed_active_session(db_session, test_tenant, test_user)
        user_ctx = _FakeUserContext(test_tenant.id, test_user.id)

        result = await calculate_conduit_fill(
            entities={
                "conduit_trade_size": "3/4",
                "conduit_type": "EMT",
                "wire_gauge": "8",
                "num_conductors": 9,
            },
            current_user=user_ctx,
            db=db_session,
            session=session,
        )

        data = result["data"]
        assert data["is_compliant"] is False
        assert data["fill_pct"] > 40.0

    @pytest.mark.asyncio
    async def test_conduit_fill_pct_exact_math(
        self, db_session, test_tenant, test_user
    ):
        """
        Exact fill_pct value must match: (num_conductors × wire_area) / conduit_area × 100.

        Using 6 × 10 AWG in 3/4\" EMT:
            area    = 6 × 0.0211 = 0.1266 sq in
            conduit = 0.533 sq in
            fill    ≈ 23.75%
        """
        session = _seed_active_session(db_session, test_tenant, test_user)
        user_ctx = _FakeUserContext(test_tenant.id, test_user.id)

        result = await calculate_conduit_fill(
            entities={
                "conduit_trade_size": "3/4",
                "conduit_type": "EMT",
                "wire_gauge": "10",
                "num_conductors": 6,
            },
            current_user=user_ctx,
            db=db_session,
            session=session,
        )

        expected_fill = (
            6 * _AWG_WIRE_AREA_SQ_IN["10"] / _CONDUIT_AREA_SQ_IN["EMT"]["3/4"] * 100
        )
        assert result["data"]["fill_pct"] == pytest.approx(expected_fill, rel=1e-3)
        assert result["data"]["is_compliant"] is True  # ≈23.75% < 40%

    @pytest.mark.asyncio
    async def test_single_conductor_uses_53pct_threshold(
        self, db_session, test_tenant, test_user
    ):
        """
        NEC Table 1: 1 conductor → 53% max fill.
        max_fill_pct in the result must be 53.0.
        """
        session = _seed_active_session(db_session, test_tenant, test_user)
        user_ctx = _FakeUserContext(test_tenant.id, test_user.id)

        result = await calculate_conduit_fill(
            entities={
                "conduit_trade_size": "1/2",
                "conduit_type": "EMT",
                "wire_gauge": "14",
                "num_conductors": 1,
            },
            current_user=user_ctx,
            db=db_session,
            session=session,
        )

        assert result["data"]["max_fill_pct"] == 53.0

    @pytest.mark.asyncio
    async def test_two_conductors_uses_31pct_threshold(
        self, db_session, test_tenant, test_user
    ):
        """
        NEC Table 1: 2 conductors → 31% max fill.
        max_fill_pct in the result must be 31.0.
        """
        session = _seed_active_session(db_session, test_tenant, test_user)
        user_ctx = _FakeUserContext(test_tenant.id, test_user.id)

        result = await calculate_conduit_fill(
            entities={
                "conduit_trade_size": "1/2",
                "conduit_type": "EMT",
                "wire_gauge": "14",
                "num_conductors": 2,
            },
            current_user=user_ctx,
            db=db_session,
            session=session,
        )

        assert result["data"]["max_fill_pct"] == 31.0

    @pytest.mark.asyncio
    async def test_three_plus_conductors_uses_40pct_threshold(
        self, db_session, test_tenant, test_user
    ):
        """
        NEC Table 1: 3+ conductors → 40% max fill (the standard residential case).
        max_fill_pct in the result must be 40.0.
        """
        session = _seed_active_session(db_session, test_tenant, test_user)
        user_ctx = _FakeUserContext(test_tenant.id, test_user.id)

        for num in [3, 4, 5, 10]:
            s = _seed_active_session(db_session, test_tenant, test_user)
            result = await calculate_conduit_fill(
                entities={
                    "conduit_trade_size": "2",
                    "conduit_type": "EMT",
                    "wire_gauge": "12",
                    "num_conductors": num,
                },
                current_user=user_ctx,
                db=db_session,
                session=s,
            )
            assert result["data"]["max_fill_pct"] == 40.0, (
                f"For {num} conductors expected max_fill_pct=40.0, "
                f"got {result['data']['max_fill_pct']}"
            )

    @pytest.mark.asyncio
    async def test_conduit_fill_invalid_gauge_returns_error(
        self, db_session, test_tenant, test_user
    ):
        """Unknown wire gauge returns success=False."""
        session = _seed_active_session(db_session, test_tenant, test_user)
        user_ctx = _FakeUserContext(test_tenant.id, test_user.id)

        result = await calculate_conduit_fill(
            entities={
                "conduit_trade_size": "3/4",
                "wire_gauge": "99 AWG",
                "num_conductors": 3,
            },
            current_user=user_ctx,
            db=db_session,
            session=session,
        )

        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_conduit_fill_invalid_conduit_size_returns_error(
        self, db_session, test_tenant, test_user
    ):
        """Unknown conduit size returns success=False."""
        session = _seed_active_session(db_session, test_tenant, test_user)
        user_ctx = _FakeUserContext(test_tenant.id, test_user.id)

        result = await calculate_conduit_fill(
            entities={
                "conduit_trade_size": "99",
                "wire_gauge": "12",
                "num_conductors": 3,
            },
            current_user=user_ctx,
            db=db_session,
            session=session,
        )

        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_conduit_fill_awg_suffix_normalized_correctly(
        self, db_session, test_tenant, test_user
    ):
        """'12 AWG' and '12' produce identical results — gauge normalization works."""
        session_a = _seed_active_session(db_session, test_tenant, test_user)
        session_b = _seed_active_session(db_session, test_tenant, test_user)
        user_ctx = _FakeUserContext(test_tenant.id, test_user.id)

        result_a = await calculate_conduit_fill(
            entities={
                "conduit_trade_size": "3/4",
                "wire_gauge": "12 AWG",
                "num_conductors": 3,
            },
            current_user=user_ctx,
            db=db_session,
            session=session_a,
        )
        result_b = await calculate_conduit_fill(
            entities={
                "conduit_trade_size": "3/4",
                "wire_gauge": "12",
                "num_conductors": 3,
            },
            current_user=user_ctx,
            db=db_session,
            session=session_b,
        )

        assert result_a["data"]["fill_pct"] == result_b["data"]["fill_pct"]
        assert result_a["data"]["is_compliant"] == result_b["data"]["is_compliant"]
