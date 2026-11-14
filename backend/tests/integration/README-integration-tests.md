# Integration Tests

This directory contains integration tests that interact with real external services and infrastructure.

## Overview

Unlike unit tests which use mocks and stubs, integration tests verify that:
- Real API integrations work correctly (SendGrid, Telnyx, etc.)
- Database operations function as expected
- End-to-end workflows complete successfully
- External service error handling works properly

## Test Categories

### Email Integration Tests (`test_sendgrid_integration.py`)
Tests the SendGrid email service integration with real API calls.

**Markers:** `@pytest.mark.integration`, `@pytest.mark.requires_sendgrid`

**Requirements:**
- `SENDGRID_API_KEY` configured in `.env`
- `SENDGRID_FROM_EMAIL` configured (verified sender)
- `SENDGRID_FROM_NAME` configured

**What's Tested:**
- Email address validation
- Plain text email delivery
- Template-rendered emails
- HTML email delivery
- Template rendering with XSS prevention

### End-to-End Notification Tests (`test_notification_e2e.py`)
Tests the complete notification pipeline from database to delivery.

**Markers:** `@pytest.mark.e2e`, `@pytest.mark.integration`, `@pytest.mark.requires_sendgrid`, `@pytest.mark.requires_db`

**What's Tested:**
- Complete pipeline: API → Database → Celery → SendGrid → Database
- NotificationEvent creation
- NotificationOutbox processing
- Template rendering in production context
- NotificationDeliveryAttempt recording
- Status updates and error handling

## Running Integration Tests

### Run All Tests (Including Integration)
```bash
cd backend
source .venv/bin/activate
pytest
```

### Run Only Unit Tests (Exclude Integration)
```bash
pytest -m "not integration"
```

### Run Only Integration Tests
```bash
pytest -m integration
```

### Run Only SendGrid Tests
```bash
pytest -m requires_sendgrid
```

### Run Only End-to-End Tests
```bash
pytest -m e2e
```

### Run Specific Test File
```bash
pytest tests/integration/test_sendgrid_integration.py -v
```

### Run Specific Test Function
```bash
pytest tests/integration/test_sendgrid_integration.py::test_send_plain_text_email -v
```

## Configuration

Integration tests are automatically skipped if required credentials are not configured. This prevents CI/CD failures when external service credentials aren't available.

### Required Environment Variables

**For SendGrid Email Tests:**
```bash
SENDGRID_API_KEY=SG.xxx...
SENDGRID_FROM_EMAIL=verified@yourdomain.com
SENDGRID_FROM_NAME=Your Name
```

**For Telnyx SMS Tests (when implemented):**
```bash
# ── Telnyx Integration Testing (B21/FIND-173) ──────────────────────────────
SMS_CARRIER=telnyx
TELNYX_API_KEY=KEY...
TELNYX_PUBLIC_KEY=xxx...xxx
TELNYX_MESSAGING_PROFILE_ID=xxx...xxx
TELNYX_SANDBOX_FROM_NUMBER=+1xxxxxxxxxx
TELNYX_SANDBOX_TO_NUMBER=+1xxxxxxxxxx
```

**For Database Tests:**
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
```

## Best Practices

1. **Cost Awareness**: Integration tests that call external APIs may incur costs. Run them intentionally, not on every code change.

2. **Test Isolation**: Each test should be independent and not rely on the state of other tests.

3. **Cleanup**: Tests should clean up any resources they create (database records, external service data).

4. **Skip When Unconfigured**: Use `@pytest.mark.skipif` to skip tests when credentials aren't available.

5. **Idempotency**: Tests should produce the same result when run multiple times.

6. **Real Recipients**: Use your own email/phone for integration testing, not customer data.

## CI/CD Integration

In CI/CD pipelines, integration tests can be:
- **Skipped** by default using `-m "not integration"`
- **Run selectively** in staging deployments
- **Run on schedule** (e.g., nightly builds)
- **Run manually** before releases

Example GitHub Actions workflow:
```yaml
# Unit tests on every commit
- name: Run unit tests
  run: pytest -m "not integration"

# Integration tests on main branch only
- name: Run integration tests
  if: github.ref == 'refs/heads/main'
  run: pytest -m integration
  env:
    SENDGRID_API_KEY: ${{ secrets.SENDGRID_API_KEY }}
```

## Troubleshooting

### Tests Are Skipped
- Check that required environment variables are set
- Verify API credentials are valid
- Ensure services are accessible (not blocked by firewall)

### SendGrid 403 Forbidden
- Verify sender email is verified in SendGrid dashboard
- Check API key has "Mail Send" permissions
- Ensure API key hasn't expired

### Database Connection Errors
- Verify PostgreSQL is running (`docker ps`)
- Check DATABASE_URL is correct
- Ensure migrations are up to date (`alembic upgrade head`)

## Adding New Integration Tests

When adding new integration tests:

1. **Create test file** in `tests/integration/`
2. **Add pytest markers** at the top of the file:
   ```python
   pytestmark = [
       pytest.mark.integration,
       pytest.mark.requires_service_name
   ]
   ```
3. **Add skip conditions** for missing configuration:
   ```python
   pytest.mark.skipif(
       not settings.SERVICE_API_KEY,
       reason="SERVICE_API_KEY not configured"
   )
   ```
4. **Update pytest.ini** with new markers
5. **Document requirements** in this README
6. **Test locally** before committing

## Related Documentation

- [Testing Support Documentation](../../../dev-docs/testing-support/)
- [Task 14 Integration Test Results](../../../dev-docs/testing-support/qb-test-results/task-14-sendgrid-integration-test-results.md)
- [Celery Worker Testing Guide](../../../dev-docs/testing-support/archived/celery-worker-testing-guide.md)
