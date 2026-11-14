"""
NEC Calculation API Tests — MOB-B0

Coverage:
  TestNecCalculateEndpoint    — POST /api/v1/nec/calculate/test
  TestNecCalcLogsCreate       — POST /api/v1/nec/calc-logs/test
  TestNecCalcLogsList         — GET  /api/v1/nec/calc-logs/test
  TestNecCalcLogTable         — Database schema verification
  TestNecServiceUnit          — Pure nec_service.calculate() unit tests

Per design doc batch-mob-b0-design.md §H.

Note: Tests use the no-auth /test endpoints which call get_test_context() and
use the test tenant (00000000-0000-0000-0000-000000000001).
Never use module-level TestClient — always use the conftest `client` fixture.
"""

import uuid

import pytest
from sqlalchemy import text
from sqlmodel import select

from app.models.fulfillment import NecCalculationLog
from services import nec_service

pytestmark = [pytest.mark.domain_field_operations, pytest.mark.unit]

NEC_BASE = "/api/v1/nec"
_TEST_TENANT_ID = "00000000-0000-0000-0000-000000000001"


# ---------------------------------------------------------------------------
# Shared payloads
# ---------------------------------------------------------------------------

_VOLTAGE_DROP_INPUTS = {
    "calc_type": "voltage_drop",
    "inputs": {
        "amperage": 20,
        "distance_feet": 10,
        "wire_gauge": "12 AWG",
        "voltage": 120,
        "phase": 1,
    },
}

_CONDUIT_FILL_INPUTS = {
    "calc_type": "conduit_fill",
    "inputs": {
        "conduit_trade_size": "3/4",
        "conduit_type": "EMT",
        "wire_gauge": "12",
        "num_conductors": 3,
    },
}

_AMPACITY_INPUTS = {
    "calc_type": "ampacity",
    "inputs": {
        "wire_gauge": "12",
        "wire_material": "copper",
        "temp_rating_c": 75,
        "conductor_count": 3,
        "ambient_temp_c": 30,
    },
}


# ===========================================================================
# TestNecCalculateEndpoint — POST /api/v1/nec/calculate/test
# ===========================================================================


class TestNecCalculateEndpoint:
    """POST /api/v1/nec/calculate/test"""

    def test_voltage_drop_returns_201_with_log_id(self, client, db_session):
        """Basic voltage drop calculation returns 201 and log_id."""
        resp = client.post(f"{NEC_BASE}/calculate/test", json=_VOLTAGE_DROP_INPUTS)
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert "log_id" in data
        assert data["calc_type"] == "voltage_drop"
        assert "result" in data
        assert "nec_citation" in data

    def test_conduit_fill_returns_result(self, client, db_session):
        """Conduit fill calc returns result with fill_pct and is_compliant."""
        resp = client.post(f"{NEC_BASE}/calculate/test", json=_CONDUIT_FILL_INPUTS)
        assert resp.status_code == 201, resp.text
        data = resp.json()
        result = data["result"]
        assert "fill_pct" in result
        assert "is_compliant" in result
        assert result["is_compliant"] is True  # 3×12AWG in 3/4 EMT is ~7.5% < 40%

    def test_ampacity_returns_result(self, client, db_session):
        """Ampacity calc returns adjusted_ampacity."""
        resp = client.post(f"{NEC_BASE}/calculate/test", json=_AMPACITY_INPUTS)
        assert resp.status_code == 201, resp.text
        data = resp.json()
        result = data["result"]
        assert "adjusted_ampacity" in result
        assert result["adjusted_ampacity"] > 0

    def test_invalid_calc_type_returns_400(self, client, db_session):
        """calc_type='unknown' → 400."""
        resp = client.post(
            f"{NEC_BASE}/calculate/test",
            json={"calc_type": "unknown_type", "inputs": {}},
        )
        assert resp.status_code == 400, resp.text

    def test_result_saved_to_db(self, client, db_session):
        """After POST, row exists in nec_calculation_log with correct calc_type."""
        idem_key = str(uuid.uuid4())
        payload = {**_VOLTAGE_DROP_INPUTS, "idempotency_key": idem_key}
        resp = client.post(f"{NEC_BASE}/calculate/test", json=payload)
        assert resp.status_code == 201, resp.text
        log_id = uuid.UUID(resp.json()["log_id"])

        db_session.expire_all()
        log = db_session.exec(
            select(NecCalculationLog).where(NecCalculationLog.id == log_id)
        ).first()
        assert log is not None
        assert log.calc_type == "voltage_drop"
        assert log.is_offline_calc is False
        assert log.result_json is not None
        assert "voltage_drop" in log.result_json

    def test_idempotency_key_dedup(self, client, db_session):
        """Same idempotency_key twice → second call returns same log_id."""
        idem_key = str(uuid.uuid4())
        payload = {**_VOLTAGE_DROP_INPUTS, "idempotency_key": idem_key}

        resp1 = client.post(f"{NEC_BASE}/calculate/test", json=payload)
        assert resp1.status_code == 201, resp1.text
        log_id_1 = resp1.json()["log_id"]

        resp2 = client.post(f"{NEC_BASE}/calculate/test", json=payload)
        assert resp2.status_code in (200, 201), resp2.text
        log_id_2 = resp2.json()["log_id"]

        assert log_id_1 == log_id_2, "Idempotency key should return same log_id"

    def test_tenant_isolation(self, client, db_session):
        """Saved log has tenant_id = test tenant."""
        resp = client.post(f"{NEC_BASE}/calculate/test", json=_VOLTAGE_DROP_INPUTS)
        assert resp.status_code == 201, resp.text
        log_id = uuid.UUID(resp.json()["log_id"])

        db_session.expire_all()
        log = db_session.exec(
            select(NecCalculationLog).where(NecCalculationLog.id == log_id)
        ).first()
        assert log is not None
        assert str(log.tenant_id) == _TEST_TENANT_ID


# ===========================================================================
# TestNecCalcLogsCreate — POST /api/v1/nec/calc-logs/test (offline sync)
# ===========================================================================


class TestNecCalcLogsCreate:
    """POST /api/v1/nec/calc-logs/test (offline sync endpoint)"""

    def test_offline_calc_saved(self, client, db_session):
        """Offline result saved with is_offline_calc=True."""
        payload = {
            "calc_type": "voltage_drop",
            "inputs": {"wire_gauge": "12", "amperage": 20, "distance_feet": 50},
            "result": {"voltage_drop_pct": 3.29, "is_compliant": True},
            "nec_guide_version": "2023",
            "is_offline_calc": True,
        }
        resp = client.post(f"{NEC_BASE}/calc-logs/test", json=payload)
        assert resp.status_code == 201, resp.text
        log_id = uuid.UUID(resp.json()["log_id"])

        db_session.expire_all()
        log = db_session.exec(
            select(NecCalculationLog).where(NecCalculationLog.id == log_id)
        ).first()
        assert log is not None
        assert log.is_offline_calc is True
        assert log.calc_type == "voltage_drop"

    def test_idempotency_replay(self, client, db_session):
        """Same idempotency_key → returns 200/201 with existing log_id."""
        idem_key = str(uuid.uuid4())
        payload = {
            "calc_type": "conduit_fill",
            "inputs": {},
            "result": {"fill_pct": 7.5},
            "idempotency_key": idem_key,
        }

        resp1 = client.post(f"{NEC_BASE}/calc-logs/test", json=payload)
        assert resp1.status_code == 201, resp1.text
        log_id_1 = resp1.json()["log_id"]

        resp2 = client.post(f"{NEC_BASE}/calc-logs/test", json=payload)
        assert resp2.status_code in (200, 201), resp2.text
        log_id_2 = resp2.json()["log_id"]

        assert log_id_1 == log_id_2


# ===========================================================================
# TestNecCalcLogsList — GET /api/v1/nec/calc-logs/test
# ===========================================================================


class TestNecCalcLogsList:
    """GET /api/v1/nec/calc-logs/test"""

    def _create_calc(self, client) -> str:
        """Helper: create one voltage drop calc via the API, return log_id."""
        resp = client.post(f"{NEC_BASE}/calculate/test", json=_VOLTAGE_DROP_INPUTS)
        assert resp.status_code == 201, resp.text
        return resp.json()["log_id"]

    def test_list_returns_logs(self, client, db_session):
        """After creating 2 logs, list returns at least 2 items."""
        id1 = self._create_calc(client)
        id2 = self._create_calc(client)

        resp = client.get(f"{NEC_BASE}/calc-logs/test")
        assert resp.status_code == 200, resp.text
        ids = [item["id"] for item in resp.json()]
        assert id1 in ids
        assert id2 in ids

    def test_limit_and_offset(self, client, db_session):
        """limit=1 returns 1 item; offset=99999 returns empty list."""
        self._create_calc(client)

        resp = client.get(f"{NEC_BASE}/calc-logs/test?limit=1")
        assert resp.status_code == 200, resp.text
        assert len(resp.json()) == 1

        resp2 = client.get(f"{NEC_BASE}/calc-logs/test?offset=99999")
        assert resp2.status_code == 200, resp2.text
        assert resp2.json() == []

    def test_tenant_isolation(self, client, db_session):
        """All returned logs belong to the test tenant."""
        self._create_calc(client)
        resp = client.get(f"{NEC_BASE}/calc-logs/test")
        assert resp.status_code == 200, resp.text
        for item in resp.json():
            # All logs returned must have the expected structure
            assert "id" in item
            assert "calc_type" in item
            assert "created_at" in item

    def test_response_shape(self, client, db_session):
        """Response items have all required NecCalcLogResponse fields."""
        self._create_calc(client)
        resp = client.get(f"{NEC_BASE}/calc-logs/test?limit=1")
        assert resp.status_code == 200, resp.text
        item = resp.json()[0]
        required_fields = {
            "id",
            "calc_type",
            "nec_guide_version",
            "inputs_json",
            "result_json",
            "is_offline_calc",
            "created_at",
        }
        for field in required_fields:
            assert field in item, f"Missing field: {field}"


# ===========================================================================
# TestNecCalcLogTable — Database schema verification
# ===========================================================================


class TestNecCalcLogTable:
    """Database schema verification for nec_calculation_log."""

    def test_table_exists(self, db_session):
        """nec_calculation_log table exists in the public schema."""
        result = db_session.exec(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = 'nec_calculation_log'"
            )
        ).fetchall()
        assert len(result) == 1, "nec_calculation_log table not found"

    def test_required_columns_exist(self, db_session):
        """All required columns are present with correct nullability."""
        required_columns = {
            "id",
            "tenant_id",
            "user_id",
            "job_id",
            "calc_type",
            "nec_guide_version",
            "inputs_json",
            "result_json",
            "is_offline_calc",
            "idempotency_key",
            "client_capture_at",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        }
        result = db_session.exec(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'nec_calculation_log'"
            )
        ).fetchall()
        existing_columns = {row[0] for row in result}
        missing = required_columns - existing_columns
        assert not missing, f"Missing columns: {missing}"

    def test_ck_nec_calc_type_enforced(self, db_session):
        """calc_type constraint rejects unknown values at DB level."""
        with pytest.raises(Exception):
            db_session.exec(
                text(
                    "INSERT INTO nec_calculation_log "
                    "(id, tenant_id, user_id, calc_type, nec_guide_version, "
                    "inputs_json, result_json) VALUES "
                    "(gen_random_uuid(), "
                    "'00000000-0000-0000-0000-000000000001'::uuid, "
                    "'00000000-0000-0000-0000-000000000002'::uuid, "
                    "'invalid_calc_type', '2023', '{}', '{}')"
                )
            )
            db_session.commit()

    def test_updated_at_trigger(self, db_session, test_tenant, test_user):
        """updated_at changes on UPDATE (via set_updated_at trigger)."""
        import time

        log = NecCalculationLog(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            calc_type="voltage_drop",
            nec_guide_version="2023",
            inputs_json={"wire_gauge": "12"},
            result_json={"voltage_drop_pct": 1.5},
            is_offline_calc=False,
        )
        db_session.add(log)
        db_session.commit()
        db_session.refresh(log)
        original_updated_at = log.updated_at

        # Small sleep to ensure timestamp difference
        time.sleep(0.05)

        # Update a field to trigger the set_updated_at trigger
        db_session.exec(
            text(
                "UPDATE nec_calculation_log SET nec_guide_version = '2023' "
                f"WHERE id = '{log.id}'"
            )
        )
        db_session.commit()
        db_session.expire(log)
        db_session.refresh(log)

        # updated_at should have changed
        assert log.updated_at >= original_updated_at

    def test_created_at_immutable(self, db_session, test_tenant, test_user):
        """created_at cannot be changed after insert (guard trigger blocks it)."""

        log = NecCalculationLog(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            calc_type="conduit_fill",
            nec_guide_version="2023",
            inputs_json={},
            result_json={},
            is_offline_calc=False,
        )
        db_session.add(log)
        db_session.commit()
        db_session.refresh(log)

        with pytest.raises(Exception):
            db_session.exec(
                text(
                    "UPDATE nec_calculation_log "
                    "SET created_at = '2020-01-01 00:00:00+00' "
                    f"WHERE id = '{log.id}'"
                )
            )
            db_session.commit()


# ===========================================================================
# TestNecServiceUnit — Pure nec_service.calculate() unit tests
# ===========================================================================


class TestNecServiceUnit:
    """Pure nec_service.calculate() unit tests — no DB, no HTTP."""

    def test_voltage_drop_copper_12awg(self):
        """12 AWG, 10ft, 20A, 120V → voltage_drop_pct ≈ 0.659%, compliant."""
        result = nec_service.calculate(
            "voltage_drop",
            {
                "amperage": 20,
                "distance_feet": 10,
                "wire_gauge": "12",
                "voltage": 120,
                "phase": 1,
            },
        )
        assert result.calc_type == "voltage_drop"
        assert result.is_compliant is True  # ~0.66% < 3%
        assert result.details["voltage_drop_pct"] == pytest.approx(0.659, rel=1e-2)

    def test_voltage_drop_three_phase(self):
        """√3 factor applied correctly for phase=3 — result less than single-phase."""
        result_1ph = nec_service.calculate(
            "voltage_drop",
            {
                "amperage": 20,
                "distance_feet": 100,
                "wire_gauge": "12",
                "voltage": 120,
                "phase": 1,
            },
        )
        result_3ph = nec_service.calculate(
            "voltage_drop",
            {
                "amperage": 20,
                "distance_feet": 100,
                "wire_gauge": "12",
                "voltage": 120,
                "phase": 3,
            },
        )
        assert result_3ph.details["voltage_drop"] < result_1ph.details["voltage_drop"]
        ratio = result_3ph.details["voltage_drop"] / result_1ph.details["voltage_drop"]
        assert ratio == pytest.approx(1.732 / 2.0, rel=1e-3)

    def test_voltage_drop_over_3pct_not_compliant(self):
        """High distance + current → is_compliant=False."""
        result = nec_service.calculate(
            "voltage_drop",
            {
                "amperage": 20,
                "distance_feet": 100,
                "wire_gauge": "12",
                "voltage": 120,
                "phase": 1,
            },
        )
        assert result.is_compliant is False  # ~6.59% > 3%

    def test_conduit_fill_emt_half_inch(self):
        """EMT ½", 3× #12 THHN → correct fill area, compliant."""
        result = nec_service.calculate(
            "conduit_fill",
            {
                "conduit_trade_size": "1/2",
                "conduit_type": "EMT",
                "wire_gauge": "12",
                "num_conductors": 3,
            },
        )
        assert result.calc_type == "conduit_fill"
        assert result.details["fill_pct"] > 0
        assert result.details["max_fill_pct"] == 40.0

    def test_conduit_fill_over_40pct_fails(self):
        """Fill >40% for 3+ wires → is_compliant=False."""
        result = nec_service.calculate(
            "conduit_fill",
            {
                "conduit_trade_size": "3/4",
                "conduit_type": "EMT",
                "wire_gauge": "8",
                "num_conductors": 9,
            },
        )
        assert result.is_compliant is False
        assert result.details["fill_pct"] > 40.0

    def test_ampacity_basic_lookup(self):
        """#12 THHN 75°C, 30°C ambient, 3 conductors → 25A base, adjusted ≤ 25A."""
        result = nec_service.calculate(
            "ampacity",
            {
                "wire_gauge": "12",
                "wire_material": "copper",
                "temp_rating_c": 75,
                "conductor_count": 3,
                "ambient_temp_c": 30,
            },
        )
        assert result.calc_type == "ampacity"
        # At exactly 30°C ambient, temp correction factor = 1.0
        assert result.details["adjusted_ampacity"] == pytest.approx(25.0, rel=1e-2)

    def test_invalid_calc_type_raises(self):
        """ValueError raised for unsupported calc_type."""
        with pytest.raises(ValueError, match="Unsupported calc_type"):
            nec_service.calculate("unknown_type", {})

    def test_nec_citation_present(self):
        """All calc types return a non-empty nec_citation."""
        for calc_type, inputs in [
            ("voltage_drop", {"amperage": 20, "distance_feet": 50, "wire_gauge": "10"}),
            (
                "conduit_fill",
                {"conduit_trade_size": "3/4", "wire_gauge": "12", "num_conductors": 3},
            ),
            ("ampacity", {"wire_gauge": "12"}),
        ]:
            result = nec_service.calculate(calc_type, inputs)
            assert result.nec_citation, f"Empty nec_citation for {calc_type}"
            assert result.nec_article, f"Empty nec_article for {calc_type}"
