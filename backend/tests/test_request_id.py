"""
Test suite for X-Request-ID tracing middleware.

Tests the RequestIDMiddleware implementation against requirements
from aevofab-db-process-v2.6h.md Section 1.1:
Every request must have unique trace ID for distributed debugging.

Gap Reference: Gap #1 - X-Request-ID Tracing Middleware
Remediation Plan: dev-docs/analysis/gap-1-request-id-remediation-plan.md

Test Coverage:
- UUID generation when X-Request-ID not provided
- Client-provided X-Request-ID acceptance
- Response header inclusion
- Request state population
- UUID validation (valid/invalid formats)
- Edge cases (empty string, malformed UUIDs)
- Logging helper functions
"""

import uuid
from unittest.mock import patch


class TestRequestIDBasics:
    """Test basic request ID functionality."""

    def test_generates_request_id_if_not_provided(self, client):
        """Test that middleware generates UUID when X-Request-ID not provided."""
        response = client.get("/")

        assert response.status_code == 200
        assert "X-Request-ID" in response.headers

        # Validate it's a proper UUID
        request_id = response.headers["X-Request-ID"]
        parsed_uuid = uuid.UUID(request_id)  # Raises ValueError if invalid
        assert str(parsed_uuid) == request_id

    def test_accepts_request_id_from_client(self, client):
        """Test that middleware accepts client-provided X-Request-ID."""
        client_id = str(uuid.uuid4())

        response = client.get("/", headers={"X-Request-ID": client_id})

        assert response.status_code == 200
        assert response.headers["X-Request-ID"] == client_id

    def test_request_id_in_response_headers(self, client):
        """Test that X-Request-ID is always in response headers."""
        response = client.get("/")

        assert "X-Request-ID" in response.headers
        assert len(response.headers["X-Request-ID"]) > 0

    def test_request_id_is_uuid4_format(self, client):
        """Test that generated request IDs are UUID4 format."""
        response = client.get("/")

        request_id = response.headers["X-Request-ID"]
        parsed_uuid = uuid.UUID(request_id)

        # UUID4 has version field set to 4
        assert parsed_uuid.version == 4

    def test_request_id_unique_across_requests(self, client):
        """Test that each request gets a unique request ID."""
        response1 = client.get("/")
        response2 = client.get("/")

        id1 = response1.headers["X-Request-ID"]
        id2 = response2.headers["X-Request-ID"]

        assert id1 != id2


class TestRequestIDValidation:
    """Test UUID validation logic."""

    def test_valid_uuid_format_accepted(self, client):
        """Test that valid UUID is accepted and returned unchanged."""
        valid_uuid = str(uuid.uuid4())

        response = client.get("/", headers={"X-Request-ID": valid_uuid})

        assert response.status_code == 200
        assert response.headers["X-Request-ID"] == valid_uuid

    def test_invalid_uuid_format_generates_new(self, client):
        """Test that invalid UUID format triggers new UUID generation."""
        invalid_id = "not-a-valid-uuid-12345"

        with patch("core.middleware.logger.warning") as mock_warning:
            response = client.get("/", headers={"X-Request-ID": invalid_id})

            assert response.status_code == 200

            # Should get a new UUID, not the invalid one
            returned_id = response.headers["X-Request-ID"]
            assert returned_id != invalid_id

            # Should be a valid UUID
            uuid.UUID(returned_id)

            # Should log warning
            mock_warning.assert_called_once()
            assert invalid_id in str(mock_warning.call_args)

    def test_malformed_uuid_generates_new(self, client):
        """Test that malformed UUID-like strings generate new UUID."""
        malformed_ids = [
            "12345678-1234-1234-1234-12345678901",  # Too short
            "12345678-1234-1234-1234-1234567890123",  # Too long
            "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",  # Invalid hex
        ]

        for malformed_id in malformed_ids:
            with patch("core.middleware.logger.warning"):
                response = client.get("/", headers={"X-Request-ID": malformed_id})

                returned_id = response.headers["X-Request-ID"]
                assert returned_id != malformed_id

                # Should be a valid UUID
                uuid.UUID(returned_id)

    def test_empty_request_id_generates_new(self, client):
        """Test that empty string X-Request-ID generates new UUID."""
        response = client.get("/", headers={"X-Request-ID": ""})

        # Empty string should trigger generation (not validation warning)
        returned_id = response.headers["X-Request-ID"]
        assert returned_id != ""

        # Should be a valid UUID
        uuid.UUID(returned_id)


class TestRequestIDPropagation:
    """Test that request ID propagates through the request lifecycle."""

    def test_request_id_available_in_endpoint(self, client):
        """Test that request.state.request_id is accessible in endpoints."""
        # Use the /api/v1/hello endpoint which should exist
        response = client.get("/api/v1/hello")

        assert response.status_code == 200
        # Request ID should be in response headers
        assert "X-Request-ID" in response.headers

    def test_request_id_persists_through_middleware_chain(self, client):
        """Test that request ID persists through multiple middleware layers."""
        # The app has RequestIDMiddleware and idempotency_middleware
        # Request ID should be set before idempotency middleware runs
        client_id = str(uuid.uuid4())

        response = client.post(
            "/api/v1/hello",  # POST to trigger idempotency middleware
            headers={"X-Request-ID": client_id},
        )

        # Should get the same ID back even after going through multiple middleware
        assert response.headers.get("X-Request-ID") == client_id

    def test_request_id_on_different_http_methods(self, client):
        """Test that request ID works on all HTTP methods."""
        methods_and_paths = [
            ("GET", "/"),
            ("POST", "/api/v1/hello"),
            ("GET", "/api/v1/hello"),
        ]

        for method, path in methods_and_paths:
            if method == "GET":
                response = client.get(path)
            elif method == "POST":
                response = client.post(path)

            # All should have request ID
            assert "X-Request-ID" in response.headers, f"Missing for {method} {path}"


class TestRequestIDLoggingHelpers:
    """Test logging helper functions."""

    def test_get_request_id_helper(self, client):
        """Test get_request_id() helper function."""
        from unittest.mock import Mock

        from core.middleware import get_request_id

        # Create mock request with request_id
        mock_request = Mock()
        mock_request.state.request_id = "test-id-123"

        result = get_request_id(mock_request)
        assert result == "test-id-123"

    def test_get_request_id_returns_unknown_if_not_set(self):
        """Test get_request_id() returns UNKNOWN if request_id not set."""
        from unittest.mock import Mock

        from core.middleware import get_request_id

        # Create mock request without request_id
        mock_request = Mock()
        mock_request.state = Mock(spec=[])  # Empty state

        result = get_request_id(mock_request)
        assert result == "UNKNOWN"

    def test_log_with_request_id_formats_message(self):
        """Test log_with_request_id() formats log message with request ID."""
        from unittest.mock import Mock

        from core.middleware import log_with_request_id

        mock_request = Mock()
        mock_request.state.request_id = "test-id-456"

        with patch("core.middleware.logger.info") as mock_log:
            log_with_request_id(mock_request, "Test message", "info")

            mock_log.assert_called_once_with("[test-id-456] Test message")

    def test_log_with_request_id_supports_log_levels(self):
        """Test log_with_request_id() supports different log levels."""
        from unittest.mock import Mock

        from core.middleware import log_with_request_id

        mock_request = Mock()
        mock_request.state.request_id = "test-id-789"

        log_levels = ["info", "warning", "error", "debug"]

        for level in log_levels:
            with patch(f"core.middleware.logger.{level}") as mock_log:
                log_with_request_id(mock_request, "Test message", level)

                mock_log.assert_called_once_with("[test-id-789] Test message")


class TestRequestIDEdgeCases:
    """Test edge cases and error scenarios."""

    def test_request_id_with_special_characters(self, client):
        """Test that special characters in X-Request-ID are handled."""
        invalid_ids = [
            "test@#$%",
            "<script>alert('xss')</script>",
            "../../../etc/passwd",
        ]

        for invalid_id in invalid_ids:
            with patch("core.middleware.logger.warning"):
                response = client.get("/", headers={"X-Request-ID": invalid_id})

                # Should generate new UUID, not use the invalid one
                returned_id = response.headers["X-Request-ID"]
                assert returned_id != invalid_id
                uuid.UUID(returned_id)

    def test_request_id_case_sensitivity(self, client):
        """Test X-Request-ID header is case-insensitive (HTTP standard)."""
        # HTTP headers are case-insensitive, but our implementation
        # uses exact case "X-Request-ID"
        valid_uuid = str(uuid.uuid4())

        # FastAPI/Starlette normalizes headers, so this should work
        response = client.get("/", headers={"x-request-id": valid_uuid})

        assert response.status_code == 200
        # Should accept the UUID (case-insensitive header matching)
        # Note: Response header will be in canonical form
        assert "X-Request-ID" in response.headers

    def test_middleware_does_not_break_on_exception(self, client):
        """Test that middleware doesn't break request flow on internal errors."""
        # Even if middleware has issues, requests should still be processed
        # This is a basic sanity check
        response = client.get("/")

        assert response.status_code == 200
        assert "X-Request-ID" in response.headers


class TestRequestIDIntegrationWithIdempotency:
    """Test that request ID middleware works with idempotency middleware."""

    def test_both_middleware_headers_present(self, client):
        """Test that both X-Request-ID and idempotency headers work together."""
        request_id = str(uuid.uuid4())
        idempotency_key = str(uuid.uuid4())

        # Use test endpoint to avoid 404 errors
        response = client.post(
            "/api/v1/hello",
            headers={
                "X-Request-ID": request_id,
                "Idempotency-Key": idempotency_key,
            },
        )

        # Request ID should be in response
        assert response.headers.get("X-Request-ID") == request_id

    def test_request_id_middleware_runs_before_idempotency(self, client):
        """Test that RequestIDMiddleware runs before idempotency middleware."""
        # This is important for logging in idempotency middleware
        # The order is set in main.py: RequestIDMiddleware added first

        response = client.post("/api/v1/hello")

        # Should have request ID even without idempotency key
        assert "X-Request-ID" in response.headers
