"""
CP-8: NEC Calculation (SD-10 E2E Tier 1)

W-07: NEC calculation via /calculate/test endpoint.
Tests use valid calc_type='voltage_drop' with deterministic inputs.

Verified from nec_service.py: valid calc_types are 'voltage_drop', 'conduit_fill', 'ampacity'.
Note: 'box_fill' is NOT a valid calc_type in the current nec_service implementation.
"""

from __future__ import annotations

import uuid

import pytest

pytestmark = [pytest.mark.e2e]

# Valid voltage_drop inputs — deterministic result
_VOLTAGE_DROP_INPUTS = {
    "amperage": 20,
    "distance_feet": 50,
    "wire_gauge": "12",
    "voltage": 120,
    "phase": 1,
}

# Valid result dict for offline calc save
_VOLTAGE_DROP_RESULT = {
    "calc_type": "voltage_drop",
    "result_value": 0.3947,
    "is_compliant": True,
    "nec_article": "NEC 210.19(A)(1)",
    "nec_citation": "NEC 210.19(A)(1) Informational Note 4 — Voltage drop <= 3% recommended",
}


class TestNecCalculation:
    """W-07: NEC calculation persists log rows and is retrievable."""

    def test_nec_calculate_persists_log_row(
        self, e2e_client, e2e_mock_entitlement, e2e_mock_ai
    ):
        """
        POST /api/v1/nec/calculate/test → 201.
        Response has log_id, calc_type, result, nec_guide_version.
        """
        resp = e2e_client.post(
            "/api/v1/nec/calculate/test",
            json={
                "calc_type": "voltage_drop",
                "inputs": _VOLTAGE_DROP_INPUTS,
            },
        )
        assert resp.status_code == 201, (
            f"NEC calculate/test expected 201, got {resp.status_code}: {resp.text[:300]}"
        )
        body = resp.json()
        assert "log_id" in body, f"Response must contain 'log_id': {body}"
        assert "calc_type" in body, f"Response must contain 'calc_type': {body}"
        assert "result" in body, f"Response must contain 'result': {body}"
        assert "nec_guide_version" in body, (
            f"Response must contain 'nec_guide_version': {body}"
        )
        assert body["calc_type"] == "voltage_drop"
        assert body["nec_guide_version"] == "2023"

        # Store log_id for next test
        TestNecCalculation._log_id = body["log_id"]

    def test_nec_calc_log_retrievable(
        self, e2e_client, e2e_mock_entitlement, e2e_mock_ai
    ):
        """
        GET /api/v1/nec/calc-logs/test → 200.
        The log created in test 1 must appear in the list.
        """
        log_id = getattr(TestNecCalculation, "_log_id", None)

        if log_id is None:
            # Create a fresh calculation first
            create_resp = e2e_client.post(
                "/api/v1/nec/calculate/test",
                json={
                    "calc_type": "voltage_drop",
                    "inputs": _VOLTAGE_DROP_INPUTS,
                },
            )
            assert create_resp.status_code == 201
            log_id = create_resp.json()["log_id"]

        resp = e2e_client.get("/api/v1/nec/calc-logs/test")
        assert resp.status_code == 200, (
            f"GET /nec/calc-logs/test expected 200, got {resp.status_code}: {resp.text[:200]}"
        )
        logs = resp.json()
        assert isinstance(logs, list), f"Expected list of logs, got: {type(logs)}"

        # Assert the created log is in the returned list
        log_ids = [str(log.get("id")) for log in logs]
        assert str(log_id) in log_ids, (
            f"Created log {log_id} must appear in /nec/calc-logs/test response. "
            f"Found IDs: {log_ids[:5]}"
        )

    def test_nec_offline_calc_can_be_saved(
        self, e2e_client, e2e_mock_entitlement, e2e_mock_ai
    ):
        """
        POST /api/v1/nec/calc-logs/test with is_offline_calc=True → 201.
        Verifies offline calculation sync endpoint works.
        """
        idempotency_key = str(uuid.uuid4())

        resp = e2e_client.post(
            "/api/v1/nec/calc-logs/test",
            json={
                "calc_type": "voltage_drop",
                "inputs": _VOLTAGE_DROP_INPUTS,
                "result": _VOLTAGE_DROP_RESULT,
                "nec_guide_version": "2023",
                "is_offline_calc": True,
                "idempotency_key": idempotency_key,
            },
        )
        assert resp.status_code == 201, (
            f"POST /nec/calc-logs/test expected 201, got {resp.status_code}: {resp.text[:300]}"
        )
        body = resp.json()
        assert "log_id" in body, f"Response must contain 'log_id': {body}"
        assert body["log_id"], "log_id must not be empty"

        # Verify idempotency: same request returns same log_id
        resp2 = e2e_client.post(
            "/api/v1/nec/calc-logs/test",
            json={
                "calc_type": "voltage_drop",
                "inputs": _VOLTAGE_DROP_INPUTS,
                "result": _VOLTAGE_DROP_RESULT,
                "nec_guide_version": "2023",
                "is_offline_calc": True,
                "idempotency_key": idempotency_key,
            },
        )
        assert resp2.status_code == 201
        assert resp2.json()["log_id"] == body["log_id"], (
            "Idempotent re-submit must return the same log_id"
        )
