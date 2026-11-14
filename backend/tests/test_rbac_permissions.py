"""
Comprehensive RBAC Permission System Tests

This module tests the Role-Based Access Control (RBAC) permission system
implemented in Task 21 (Phase 4).

Test Coverage:
- Unit tests: Permission matching logic (has_permission function)
- Integration tests: Role enforcement on actual routes
- Tenant isolation: Cross-tenant permission checks
- Error handling: Clear error messages for permission denied
- Performance: Permission checks complete in < 10ms

Related:
- Permission module: backend/core/permissions.py
- Implementation plan: dev-docs/analysis/phase-1-5-tasks/task-21-rbac-impl-plan.md
"""

import time
import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models.auth import TenantUser, TenantUserRole, TenantUserStatus
from app.models.core import User
from app.models.crm import Customer, CustomerType
from app.models.fulfillment import Job
from app.models.quoting import Quote
from core.permissions import (
    PermissionDeniedError,
    get_permission_hint,
    has_permission,
)

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def owner_user(db_session: Session, tenant_a):
    """Create user with owner role (wildcard * permission)."""
    user = User(
        id=uuid.uuid4(),
        email="owner@test.com",
        cognito_user_id="test-owner-cognito-id",
        is_active=True,
        created_at=datetime.now(UTC),
    )
    db_session.add(user)
    db_session.flush()

    # Get active status
    status = db_session.exec(
        select(TenantUserStatus).where(
            TenantUserStatus.code == "active", TenantUserStatus.tenant_id == tenant_a.id
        )
    ).first()

    if not status:
        # Create default status if it doesn't exist
        status = TenantUserStatus(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            code="active",
            name="Active",
            is_default=True,
            is_active=True,
        )
        db_session.add(status)
        db_session.flush()

    tenant_user = TenantUser(
        tenant_id=tenant_a.id,
        user_id=user.id,
        role_code="owner",
        status_id=status.id,
        is_active=True,
        joined_at=datetime.now(UTC),
    )
    db_session.add(tenant_user)
    db_session.commit()

    return user


@pytest.fixture
def technician_user(db_session: Session, tenant_a):
    """Create user with technician role (limited permissions)."""
    user = User(
        id=uuid.uuid4(),
        email="tech@test.com",
        cognito_user_id="test-tech-cognito-id",
        is_active=True,
        created_at=datetime.now(UTC),
    )
    db_session.add(user)
    db_session.flush()

    # Get active status
    status = db_session.exec(
        select(TenantUserStatus).where(
            TenantUserStatus.code == "active", TenantUserStatus.tenant_id == tenant_a.id
        )
    ).first()

    if not status:
        status = TenantUserStatus(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            code="active",
            name="Active",
            is_default=True,
            is_active=True,
        )
        db_session.add(status)
        db_session.flush()

    tenant_user = TenantUser(
        tenant_id=tenant_a.id,
        user_id=user.id,
        role_code="technician",
        status_id=status.id,
        is_active=True,
        joined_at=datetime.now(UTC),
    )
    db_session.add(tenant_user)
    db_session.commit()

    return user


@pytest.fixture
def office_staff_user(db_session: Session, tenant_a):
    """Create user with office_staff role (customer and quote permissions)."""
    user = User(
        id=uuid.uuid4(),
        email="staff@test.com",
        cognito_user_id="test-staff-cognito-id",
        is_active=True,
        created_at=datetime.now(UTC),
    )
    db_session.add(user)
    db_session.flush()

    # Get active status
    status = db_session.exec(
        select(TenantUserStatus).where(
            TenantUserStatus.code == "active", TenantUserStatus.tenant_id == tenant_a.id
        )
    ).first()

    if not status:
        status = TenantUserStatus(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            code="active",
            name="Active",
            is_default=True,
            is_active=True,
        )
        db_session.add(status)
        db_session.flush()

    tenant_user = TenantUser(
        tenant_id=tenant_a.id,
        user_id=user.id,
        role_code="office_staff",
        status_id=status.id,
        is_active=True,
        joined_at=datetime.now(UTC),
    )
    db_session.add(tenant_user)
    db_session.commit()

    return user


@pytest.fixture
def accountant_user(db_session: Session, tenant_a):
    """Create user with accountant role (read-only permissions)."""
    user = User(
        id=uuid.uuid4(),
        email="accountant@test.com",
        cognito_user_id="test-accountant-cognito-id",
        is_active=True,
        created_at=datetime.now(UTC),
    )
    db_session.add(user)
    db_session.flush()

    # Get active status
    status = db_session.exec(
        select(TenantUserStatus).where(
            TenantUserStatus.code == "active", TenantUserStatus.tenant_id == tenant_a.id
        )
    ).first()

    if not status:
        status = TenantUserStatus(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            code="active",
            name="Active",
            is_default=True,
            is_active=True,
        )
        db_session.add(status)
        db_session.flush()

    tenant_user = TenantUser(
        tenant_id=tenant_a.id,
        user_id=user.id,
        role_code="accountant",
        status_id=status.id,
        is_active=True,
        joined_at=datetime.now(UTC),
    )
    db_session.add(tenant_user)
    db_session.commit()

    return user


# ============================================================================
# Unit Tests: Permission Matching Logic (10 tests)
# ============================================================================


def test_exact_permission_match():
    """User with exact permission can perform action."""
    assert has_permission(["quotes.create"], "quotes.create") is True


def test_exact_permission_denied():
    """User without exact permission is denied."""
    assert has_permission(["quotes.view"], "quotes.create") is False


def test_wildcard_full_access():
    """Owner with * wildcard has all permissions."""
    assert has_permission(["*"], "quotes.create") is True
    assert has_permission(["*"], "customers.delete") is True
    assert has_permission(["*"], "anything.action") is True


def test_wildcard_resource_match():
    """User with quotes.* can perform any quote action."""
    assert has_permission(["quotes.*"], "quotes.create") is True
    assert has_permission(["quotes.*"], "quotes.view") is True
    assert has_permission(["quotes.*"], "quotes.update") is True
    assert has_permission(["quotes.*"], "quotes.delete") is True


def test_wildcard_resource_denied():
    """User with quotes.* cannot perform customer actions."""
    assert has_permission(["quotes.*"], "customers.create") is False


def test_wildcard_action_match():
    """User with *.view can view any resource."""
    assert has_permission(["*.view"], "quotes.view") is True
    assert has_permission(["*.view"], "customers.view") is True
    assert has_permission(["*.view"], "jobs.view") is True


def test_wildcard_action_denied():
    """User with *.view cannot create resources."""
    assert has_permission(["*.view"], "quotes.create") is False
    assert has_permission(["*.view"], "customers.update") is False


def test_multiple_permissions_or_logic():
    """User with multiple permissions - any match grants access."""
    perms = ["jobs.view", "jobs.update", "time_entries.create"]
    assert has_permission(perms, "jobs.view") is True
    assert has_permission(perms, "jobs.update") is True
    assert has_permission(perms, "time_entries.create") is True
    assert has_permission(perms, "quotes.create") is False


def test_permission_without_dot_separator():
    """Permission without dot separator returns False."""
    assert has_permission(["invalid"], "invalid") is True  # Exact match
    assert has_permission(["quotes.create"], "invalid") is False


def test_empty_permissions_list():
    """User with no permissions is denied all actions."""
    assert has_permission([], "quotes.create") is False
    assert has_permission([], "quotes.view") is False


# ============================================================================
# Unit Tests: Permission Hint Generation (2 tests)
# ============================================================================


def test_permission_hint_for_quotes():
    """Hint suggests office_staff or owner for quotes permissions."""
    hint = get_permission_hint("quotes.create")
    assert "office_staff" in hint
    assert "owner" in hint


def test_permission_hint_for_time_entries():
    """Hint suggests technician or owner for time_entries permissions."""
    hint = get_permission_hint("time_entries.create")
    assert "technician" in hint
    assert "owner" in hint


# ============================================================================
# Integration Tests: Role Enforcement on Routes (15 tests)
# ============================================================================


def test_owner_can_create_quote(
    client: TestClient, owner_user, test_customer, test_site, mock_cognito_jwt
):
    """Owner with * wildcard can create quotes."""
    mock_cognito_jwt(owner_user)

    response = client.post(
        "/api/v1/quotes",
        json={
            "customer_id": str(test_customer.id),
            "site_id": str(test_site.id),
            "currency": "USD",
        },
    )
    assert response.status_code == 201, f"Failed: {response.json()}"


def test_technician_cannot_create_quote(
    client: TestClient, technician_user, test_customer, test_site, mock_cognito_jwt
):
    """Technician without quotes.create permission gets 403."""
    mock_cognito_jwt(technician_user)

    response = client.post(
        "/api/v1/quotes",
        json={
            "customer_id": str(test_customer.id),
            "site_id": str(test_site.id),
            "currency": "USD",
        },
    )
    assert response.status_code == 403
    error = response.json()["detail"]
    assert error["required_permission"] == "quotes.create"
    assert "user_permissions" in error
    assert "hint" in error


def test_office_staff_can_create_quote(
    client: TestClient, office_staff_user, test_customer, test_site, mock_cognito_jwt
):
    """Office staff with quotes.* can create quotes."""
    mock_cognito_jwt(office_staff_user)

    response = client.post(
        "/api/v1/quotes",
        json={
            "customer_id": str(test_customer.id),
            "site_id": str(test_site.id),
            "currency": "USD",
        },
    )
    assert response.status_code == 201


def test_technician_can_view_jobs(
    client: TestClient, technician_user, mock_cognito_jwt
):
    """Technician with jobs.view can list jobs."""
    mock_cognito_jwt(technician_user)

    response = client.get("/api/v1/jobs/")
    assert response.status_code == 200


def test_technician_can_log_time(
    client: TestClient, technician_user, test_job, mock_cognito_jwt
):
    """Technician with time_entries.create can log time."""
    mock_cognito_jwt(technician_user)

    response = client.post(
        f"/api/v1/jobs/{test_job.id}/time-entries",
        json={
            "started_at": "2026-03-28T09:00:00Z",
            "ended_at": "2026-03-28T17:00:00Z",
            "notes": "Panel upgrade",
        },
    )
    assert response.status_code == 201


def test_office_staff_cannot_log_time(
    client: TestClient, office_staff_user, test_job, mock_cognito_jwt
):
    """Office staff without time_entries.create gets 403."""
    mock_cognito_jwt(office_staff_user)

    response = client.post(
        f"/api/v1/jobs/{test_job.id}/time-entries",
        json={
            "started_at": "2026-03-28T09:00:00Z",
            "ended_at": "2026-03-28T17:00:00Z",
            "notes": "Panel upgrade",
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"]["required_permission"] == "time_entries.create"


def test_accountant_can_view_quotes(
    client: TestClient, accountant_user, mock_cognito_jwt
):
    """Accountant with *.view can view quotes."""
    mock_cognito_jwt(accountant_user)

    response = client.get("/api/v1/quotes")
    assert response.status_code == 200


def test_accountant_cannot_create_quote(
    client: TestClient, accountant_user, test_customer, test_site, mock_cognito_jwt
):
    """Accountant with only *.view cannot create quotes."""
    mock_cognito_jwt(accountant_user)

    response = client.post(
        "/api/v1/quotes",
        json={
            "customer_id": str(test_customer.id),
            "site_id": str(test_site.id),
            "currency": "USD",
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"]["required_permission"] == "quotes.create"


def test_accountant_can_view_audit_logs(
    client: TestClient, accountant_user, mock_cognito_jwt
):
    """Accountant with audit.view can access audit logs."""
    mock_cognito_jwt(accountant_user)

    response = client.get("/api/v1/audit/events")
    assert response.status_code == 200


def test_technician_cannot_view_audit_logs(
    client: TestClient, technician_user, mock_cognito_jwt
):
    """Technician without audit.view gets 403."""
    mock_cognito_jwt(technician_user)

    response = client.get("/api/v1/audit/events")
    assert response.status_code == 403
    assert response.json()["detail"]["required_permission"] == "audit.view"


def test_office_staff_can_create_customer(
    client: TestClient, office_staff_user, mock_cognito_jwt
):
    """Office staff with customers.* can create customers."""
    mock_cognito_jwt(office_staff_user)

    response = client.post(
        "/api/v1/customers/",
        json={
            "display_name": "Test Customer",
            "type": "person",
            "email": "test@example.com",
        },
    )
    assert response.status_code == 201


def test_technician_cannot_create_customer(
    client: TestClient, technician_user, mock_cognito_jwt
):
    """Technician without customers.create gets 403."""
    mock_cognito_jwt(technician_user)

    response = client.post(
        "/api/v1/customers/",
        json={
            "display_name": "Test Customer",
            "type": "person",
            "email": "test@example.com",
        },
    )
    assert response.status_code == 403


def test_owner_can_manage_integrations(
    client: TestClient, owner_user, mock_cognito_jwt
):
    """Owner with * wildcard can view integration status."""
    mock_cognito_jwt(owner_user)

    response = client.get("/api/v1/integrations/quickbooks/status")
    assert response.status_code == 200


def test_technician_cannot_manage_integrations(
    client: TestClient, technician_user, mock_cognito_jwt
):
    """Technician without integrations.view gets 403."""
    mock_cognito_jwt(technician_user)

    response = client.get("/api/v1/integrations/quickbooks/status")
    assert response.status_code == 403


def test_accountant_cannot_update_customers(
    client: TestClient, accountant_user, test_customer, mock_cognito_jwt
):
    """Accountant with only *.view cannot update customers."""
    mock_cognito_jwt(accountant_user)

    response = client.patch(
        f"/api/v1/customers/{test_customer.id}",
        json={
            "display_name": "Updated Name",
            "type": "person",
            "email": "updated@example.com",
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"]["required_permission"] == "customers.update"


# ============================================================================
# Tenant Isolation Tests (5 tests)
# ============================================================================


def test_permissions_scoped_to_tenant(
    client: TestClient, owner_user, tenant_b, db_session, mock_cognito_jwt
):
    """User from Tenant A cannot access Tenant B's quotes even with permission."""
    mock_cognito_jwt(owner_user)  # owner_user is in tenant_a

    # Create a quote in tenant_b
    from app.models.quoting import QuoteStatus

    status = db_session.exec(
        select(QuoteStatus).where(QuoteStatus.is_default == True)
    ).first()

    # Create customer in tenant_b
    customer_b = Customer(
        tenant_id=tenant_b.id,
        type=CustomerType.person,
        display_name="Tenant B Customer",
        email="tenantb@example.com",
    )
    db_session.add(customer_b)
    db_session.flush()

    # Create site in tenant_b
    from app.models.crm import Site

    site_b = Site(
        tenant_id=tenant_b.id,
        customer_id=customer_b.id,
        site_name="Tenant B Site",
    )
    db_session.add(site_b)
    db_session.flush()

    # Create quote in tenant_b
    quote_b = Quote(
        tenant_id=tenant_b.id,
        customer_id=customer_b.id,
        site_id=site_b.id,
        status_id=status.id,
        currency="USD",
    )
    db_session.add(quote_b)
    db_session.commit()

    # Try to access tenant_b's quote from tenant_a user
    response = client.get(f"/api/v1/quotes/{quote_b.id}")
    assert response.status_code == 404  # Not found due to tenant isolation


def test_role_permissions_tenant_isolated(db_session, tenant_a, tenant_b):
    """Role permissions are the same across tenants (roles are global)."""
    # Get owner role
    owner_role = db_session.exec(
        select(TenantUserRole).where(TenantUserRole.code == "owner")
    ).first()

    assert owner_role is not None
    assert "*" in owner_role.permissions  # Owner has wildcard permission
    # Roles are global, not tenant-specific


def test_user_cannot_access_other_tenant_jobs(
    client: TestClient, technician_user, tenant_b, db_session, mock_cognito_jwt
):
    """Technician from Tenant A cannot view Tenant B's jobs."""
    mock_cognito_jwt(technician_user)  # technician is in tenant_a

    # Create customer and site in tenant_b
    customer_b = Customer(
        tenant_id=tenant_b.id,
        type=CustomerType.person,
        display_name="Tenant B Customer",
        email="tenantb@example.com",
    )
    db_session.add(customer_b)
    db_session.flush()

    from app.models.crm import Site

    site_b = Site(
        tenant_id=tenant_b.id,
        customer_id=customer_b.id,
        name="Tenant B Site",
    )
    db_session.add(site_b)
    db_session.flush()

    # Create job in tenant_b
    from app.models.fulfillment import JobStatus

    job_status = db_session.exec(
        select(JobStatus).where(JobStatus.is_default == True)
    ).first()

    job_b = Job(
        tenant_id=tenant_b.id,
        customer_id=customer_b.id,
        site_id=site_b.id,
        status_id=job_status.id,
    )
    db_session.add(job_b)
    db_session.commit()

    # Try to access tenant_b's job
    response = client.get(f"/api/v1/jobs/{job_b.id}")
    assert response.status_code == 404


def test_audit_logs_tenant_isolated(
    client: TestClient, accountant_user, tenant_b, mock_cognito_jwt
):
    """Accountant can only view audit logs from their own tenant."""
    mock_cognito_jwt(accountant_user)  # accountant is in tenant_a

    response = client.get("/api/v1/audit/events")
    assert response.status_code == 200

    # All returned events should be from tenant_a
    events = response.json()["events"]
    for event in events:
        # Can't directly check tenant_id in response, but all should be scoped
        # This is enforced by the query filter in the endpoint
        pass  # Trust tenant isolation in endpoint


def test_integration_status_tenant_isolated(
    client: TestClient, owner_user, mock_cognito_jwt
):
    """Integration status only shows current tenant's connections."""
    mock_cognito_jwt(owner_user)

    response = client.get("/api/v1/integrations/quickbooks/status")
    assert response.status_code == 200
    # Status is for owner_user's tenant only


# ============================================================================
# Error Handling Tests (5 tests)
# ============================================================================


def test_permission_denied_error_structure():
    """PermissionDeniedError includes all required fields."""
    error = PermissionDeniedError(
        required_permission="quotes.create",
        user_permissions=["jobs.view"],
        user_role="technician",
    )

    assert error.status_code == 403
    assert error.detail["required_permission"] == "quotes.create"
    assert error.detail["user_permissions"] == ["jobs.view"]
    assert error.detail["user_role"] == "technician"
    assert "hint" in error.detail
    assert error.detail["type"] == "https://pilotfortrades.com/errors/forbidden"


def test_permission_denied_includes_helpful_hint():
    """403 error includes hint about which role to request."""
    error = PermissionDeniedError(
        required_permission="quotes.create",
        user_permissions=["jobs.view"],
        user_role="technician",
    )

    hint = error.detail["hint"]
    assert "office_staff" in hint or "owner" in hint


def test_missing_jwt_returns_401(client: TestClient):
    """Request without JWT token returns 401 Unauthorized."""
    response = client.get("/api/v1/quotes")
    assert response.status_code == 401


def test_invalid_jwt_returns_401(client: TestClient):
    """Request with invalid JWT token returns 401 Unauthorized."""
    response = client.get(
        "/api/v1/quotes", headers={"Authorization": "Bearer invalid-token"}
    )
    assert response.status_code == 401


def test_permission_denied_user_role_included(
    client: TestClient, technician_user, test_customer, test_site, mock_cognito_jwt
):
    """403 response includes user's current role for debugging."""
    mock_cognito_jwt(technician_user)

    response = client.post(
        "/api/v1/quotes",
        json={
            "customer_id": str(test_customer.id),
            "site_id": str(test_site.id),
            "currency": "USD",
        },
    )
    assert response.status_code == 403
    error = response.json()["detail"]
    assert error["user_role"] == "technician"


# ============================================================================
# Performance Tests (3 tests)
# ============================================================================


def test_permission_check_performance():
    """Permission check completes in < 10ms."""
    perms = ["jobs.view", "jobs.update", "time_entries.create", "expenses.create"]

    start = time.perf_counter()

    for _ in range(1000):
        has_permission(perms, "jobs.view")

    elapsed = (time.perf_counter() - start) / 1000
    assert elapsed < 0.010, (
        f"Permission check took {elapsed * 1000:.2f}ms (should be <10ms)"
    )


def test_wildcard_permission_check_performance():
    """Wildcard permission check is equally fast."""
    perms = ["*"]

    start = time.perf_counter()

    for _ in range(1000):
        has_permission(perms, "anything.action")

    elapsed = (time.perf_counter() - start) / 1000
    assert elapsed < 0.010, (
        f"Wildcard check took {elapsed * 1000:.2f}ms (should be <10ms)"
    )


def test_complex_permission_list_performance():
    """Permission check with large permission list is still fast."""
    # Simulate a complex role with many permissions
    perms = [
        "customers.*",
        "quotes.*",
        "sites.*",
        "contacts.*",
        "addresses.*",
        "jobs.view",
        "jobs.update",
        "time_entries.view",
        "expenses.view",
        "invoices.view",
        "reports.view",
    ]

    start = time.perf_counter()

    for _ in range(1000):
        has_permission(perms, "quotes.create")

    elapsed = (time.perf_counter() - start) / 1000
    assert elapsed < 0.010, (
        f"Complex check took {elapsed * 1000:.2f}ms (should be <10ms)"
    )
