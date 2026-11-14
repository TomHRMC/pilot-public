"""
ALPHA-FIX-1 — Telnyx webhook ClientDisconnect handling (notifications_comms domain).

Verifies that when the Telnyx edge drops the connection mid-body, the webhook
handler returns 400 (RFC 7807 Problem Details) instead of surfacing an unhandled
500 / ASGI ExceptionGroup. 400 → Telnyx retries on a fresh connection.

Design §F.3 / §H.
"""

from unittest.mock import patch

import pytest
from starlette.requests import ClientDisconnect

pytestmark = [
    pytest.mark.domain_notifications_comms,
    pytest.mark.unit,
]


class TestTelnyxWebhookClientDisconnect:
    """ALPHA-FIX-1 — ClientDisconnect → 400 RFC 7807, no signature verify."""

    def test_client_disconnect_returns_400_rfc7807(self, client, test_tenant):
        """Request.body() raising ClientDisconnect → 400 with RFC 7807 body."""

        # Patch Request.body at the class level so the route handler's
        # `await request.body()` raises ClientDisconnect. This is pre-signature
        # verification — the carrier verify must never be invoked.
        async def _raise_disconnect(self, *args, **kwargs):
            raise ClientDisconnect()

        with (
            patch("starlette.requests.Request.body", new=_raise_disconnect),
            patch("services.sms_carrier.get_sms_carrier") as mock_carrier_factory,
        ):
            response = client.post(
                "/api/v1/webhooks/sms/telnyx-inbound",
                content=b'{"data": {"event_type": "message.received"}}',
                headers={
                    "content-type": "application/json",
                    "telnyx-signature-ed25519": "dGVzdA==",
                    "telnyx-timestamp": "1234567890",
                },
            )

        assert response.status_code == 400
        body = response.json()
        # RFC 7807 Problem Details dict is nested under FastAPI's "detail" key
        # (default HTTPException handler wraps the detail payload).
        problem = body["detail"]
        assert problem["type"] == "https://errors.pilotfortrades.com/validation-error"
        assert problem["title"] == "Validation Error"
        assert problem["status"] == 400
        assert "client disconnected" in problem["detail"].lower()

        # Signature verification must NOT have been invoked (body unreadable —
        # the 400 response proves the disconnect path ran before carrier verify).
        mock_carrier_factory.assert_not_called()
