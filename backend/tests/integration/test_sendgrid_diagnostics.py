"""
SendGrid Diagnostics Test

This test provides diagnostic information about SendGrid configuration
and helps troubleshoot common issues like 403 Forbidden errors.

This is more of a utility test - it's not a pass/fail test but rather
provides information about the current configuration.
"""

import pytest
from sendgrid import SendGridAPIClient

from core.config import settings


@pytest.mark.integration
@pytest.mark.requires_sendgrid
def test_sendgrid_configuration_details():
    """Display SendGrid configuration for troubleshooting."""
    print("\n" + "=" * 60)
    print("SendGrid Configuration Diagnostics")
    print("=" * 60)

    # Check API Key
    print("\n1. API Key Check:")
    if not settings.SENDGRID_API_KEY:
        print("   ❌ SENDGRID_API_KEY not set")
        pytest.skip("SENDGRID_API_KEY not configured")
    print(
        f"   ✅ API Key: {settings.SENDGRID_API_KEY[:10]}...{settings.SENDGRID_API_KEY[-4:]}"
    )

    # Check configuration
    print("\n2. Configuration:")
    print(f"   From Email: {settings.SENDGRID_FROM_EMAIL}")
    print(f"   From Name: {settings.SENDGRID_FROM_NAME}")

    # Test API Key validity
    print("\n3. API Key Permissions Test:")
    try:
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)

        # Try to get API key scopes
        response = sg.client.scopes.get()
        print(f"   ✅ API key is valid (HTTP {response.status_code})")

        if response.status_code == 200:
            print(f"   Scopes: {response.body}")
    except Exception as e:
        print(f"   ❌ API key test failed: {e!s}")
        if "403" in str(e):
            print("\n   🔍 403 Forbidden suggests:")
            print("      1. API key may be invalid or expired")
            print("      2. API key may not have 'Mail Send' permissions")

    print("\n4. Sender Email Verification:")
    print(f"   Configured sender: {settings.SENDGRID_FROM_EMAIL}")
    print("\n   ⚠️  IMPORTANT: SendGrid requires sender verification!")
    print("\n   To fix 403 Forbidden errors:")
    print("   ")
    print("   Option A: Verify a single sender email")
    print("   1. Log into SendGrid dashboard: https://app.sendgrid.com/")
    print("   2. Go to Settings > Sender Authentication")
    print("   3. Click 'Verify a Single Sender'")
    print(f"   4. Add and verify: {settings.SENDGRID_FROM_EMAIL}")
    print("   5. Check your email for verification link")
    print("   ")
    print("   Option B: Authenticate your domain (recommended)")
    print("   1. Go to Settings > Sender Authentication")
    print("   2. Click 'Authenticate Your Domain'")
    print("   3. Follow DNS configuration steps")

    print("\n" + "=" * 60)

    # This test always passes - it's informational only
    assert True, "Diagnostic test completed"


@pytest.mark.integration
def test_sendgrid_quick_troubleshooting_guide():
    """Display quick troubleshooting guide."""
    print("\n" + "=" * 60)
    print("SendGrid Quick Troubleshooting Guide")
    print("=" * 60)

    print("\n🔴 Common Error: 403 Forbidden")
    print("   Cause: Sender email not verified in SendGrid")
    print("   Fix: Verify sender in SendGrid dashboard")
    print("   URL: https://app.sendgrid.com/settings/sender_auth")

    print("\n🟡 Common Error: 401 Unauthorized")
    print("   Cause: Invalid or expired API key")
    print("   Fix: Generate new API key in SendGrid")
    print("   URL: https://app.sendgrid.com/settings/api_keys")

    print("\n🟢 Email Test Recipient Recommendations:")
    print("   - Use your own email address for testing")
    print("   - Avoid using customer or production emails")
    print("   - Check spam folder if emails don't arrive")

    print("\n📊 Rate Limits (Free Tier):")
    print("   - 100 emails/day")
    print("   - Upgrade to $19.95/mo for 40,000 emails/month")

    print("\n" + "=" * 60)

    # This test always passes - it's informational only
    assert True, "Troubleshooting guide displayed"
