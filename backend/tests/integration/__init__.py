"""
Integration Tests for Pilot for Trades Backend

This package contains integration tests that interact with real external services
like SendGrid, Twilio, and the actual database. These tests are marked with
pytest markers to allow selective execution.

Markers:
- @pytest.mark.integration - General integration test
- @pytest.mark.requires_sendgrid - Requires SendGrid API credentials
- @pytest.mark.requires_telnyx - Requires Telnyx API credentials (B11/A59: replaced Twilio)
- @pytest.mark.e2e - End-to-end pipeline tests

Usage:
    # Run all tests (including integration)
    pytest

    # Run only unit tests (exclude integration)
    pytest -m "not integration"

    # Run only integration tests
    pytest -m integration

    # Run only SendGrid integration tests
    pytest -m requires_sendgrid

    # Run end-to-end tests
    pytest -m e2e
"""
