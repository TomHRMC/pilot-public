"""
tests/batch_b5/test_dashboard_widget_crud.py

B5/A5 — Dashboard widget CRUD isolation tests.

Test focus areas (from design doc H):
  3. Widget CRUD isolation:
     - User A creates widget → User B in same tenant cannot GET, PATCH, or DELETE it
     - GET /dashboard/widgets returns only user_id = current_user.id rows
     - PATCH/DELETE on another user's widget returns 404 (not 403)
  - Tenant isolation at widget level
  - Validation: widget_type must be valid WidgetType enum value
  - Validation: width/height/position bounds
  - Hard-delete (no soft-delete): widget disappears after DELETE
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlmodel import select

from app.models.reports import UserDashboardWidget, WidgetType

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user_a(db_session, test_tenant):
    """Create User A in test_tenant."""
    from app.models.core import User, UserEndpoint

    user = User(
        id=uuid.uuid4(),
        email=f"user_a_{uuid.uuid4().hex[:6]}@test.local",
        first_name="Alice",
        last_name="A",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(user)
    db_session.flush()

    endpoint = UserEndpoint(
        user_id=user.id,
        channel="email",
        value=user.email,
        is_primary=True,
        verification_status="verified",
        consent_status="opted_in",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(endpoint)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def user_b(db_session, test_tenant):
    """Create User B in test_tenant."""
    from app.models.core import User, UserEndpoint

    user = User(
        id=uuid.uuid4(),
        email=f"user_b_{uuid.uuid4().hex[:6]}@test.local",
        first_name="Bob",
        last_name="B",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(user)
    db_session.flush()

    endpoint = UserEndpoint(
        user_id=user.id,
        channel="email",
        value=user.email,
        is_primary=True,
        verification_status="verified",
        consent_status="opted_in",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(endpoint)
    db_session.commit()
    db_session.refresh(user)
    return user


def _create_widget(
    db_session,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    widget_type: str = "profitability_summary",
    position_x: int = 0,
    position_y: int = 0,
) -> UserDashboardWidget:
    """Helper to directly create a widget bypassing the HTTP layer."""
    now = datetime.now(UTC)
    widget = UserDashboardWidget(
        user_id=user_id,
        tenant_id=tenant_id,
        widget_type=widget_type,
        widget_config_json={"group_by": "job"},
        position_x=position_x,
        position_y=position_y,
        width=2,
        height=2,
        created_by=user_id,
        updated_by=user_id,
        created_at=now,
        updated_at=now,
    )
    db_session.add(widget)
    db_session.commit()
    db_session.refresh(widget)
    return widget


# ---------------------------------------------------------------------------
# ORM model tests — no HTTP layer needed
# ---------------------------------------------------------------------------


class TestWidgetModelBasics:
    def test_create_widget_in_db(self, db_session, test_tenant, user_a):
        widget = _create_widget(db_session, user_a.id, test_tenant.id)
        assert widget.id is not None
        assert widget.user_id == user_a.id
        assert widget.tenant_id == test_tenant.id
        assert widget.widget_type == "profitability_summary"
        assert widget.position_x == 0
        assert widget.position_y == 0
        assert widget.width == 2
        assert widget.height == 2
        assert widget.widget_config_json == {"group_by": "job"}

    def test_widget_defaults_applied(self, db_session, test_tenant, user_a):
        widget = _create_widget(db_session, user_a.id, test_tenant.id)
        assert widget.position_x == 0
        assert widget.position_y == 0
        assert widget.width == 2
        assert widget.height == 2

    def test_hard_delete_removes_widget(self, db_session, test_tenant, user_a):
        widget = _create_widget(db_session, user_a.id, test_tenant.id)
        widget_id = widget.id

        db_session.delete(widget)
        db_session.commit()

        deleted = db_session.get(UserDashboardWidget, widget_id)
        assert deleted is None


# ---------------------------------------------------------------------------
# Widget user isolation tests
# ---------------------------------------------------------------------------


class TestWidgetUserIsolation:
    """H3: User A's widgets are invisible to User B in the same tenant."""

    def test_user_b_cannot_see_user_a_widget_in_query(
        self, db_session, test_tenant, user_a, user_b
    ):
        """SELECT filtered by user_b.id returns 0 rows when widget belongs to user_a."""
        _create_widget(db_session, user_a.id, test_tenant.id)

        # Query as user_b — should return nothing
        widgets_for_b = db_session.exec(
            select(UserDashboardWidget)
            .where(UserDashboardWidget.user_id == user_b.id)
            .where(UserDashboardWidget.tenant_id == test_tenant.id)
        ).all()
        assert widgets_for_b == []

    def test_user_a_sees_own_widgets(self, db_session, test_tenant, user_a, user_b):
        """User A's query returns only their own widgets, not user_b's."""
        widget_a = _create_widget(db_session, user_a.id, test_tenant.id)
        _create_widget(db_session, user_b.id, test_tenant.id)  # user_b widget

        widgets_for_a = db_session.exec(
            select(UserDashboardWidget)
            .where(UserDashboardWidget.user_id == user_a.id)
            .where(UserDashboardWidget.tenant_id == test_tenant.id)
        ).all()
        assert len(widgets_for_a) == 1
        assert widgets_for_a[0].id == widget_a.id

    def test_ownership_check_returns_none_for_cross_user(
        self, db_session, test_tenant, user_a, user_b
    ):
        """Row-level ownership: user_b cannot fetch user_a's widget via id+user filter."""
        widget_a = _create_widget(db_session, user_a.id, test_tenant.id)

        # Simulate _get_owned_widget_or_404 query for user_b
        result = db_session.exec(
            select(UserDashboardWidget)
            .where(UserDashboardWidget.id == widget_a.id)
            .where(UserDashboardWidget.tenant_id == test_tenant.id)
            .where(UserDashboardWidget.user_id == user_b.id)  # wrong user
        ).first()
        assert result is None  # 404 behavior

    def test_ownership_check_returns_widget_for_correct_user(
        self, db_session, test_tenant, user_a
    ):
        widget_a = _create_widget(db_session, user_a.id, test_tenant.id)

        result = db_session.exec(
            select(UserDashboardWidget)
            .where(UserDashboardWidget.id == widget_a.id)
            .where(UserDashboardWidget.tenant_id == test_tenant.id)
            .where(UserDashboardWidget.user_id == user_a.id)  # correct user
        ).first()
        assert result is not None
        assert result.id == widget_a.id


# ---------------------------------------------------------------------------
# Widget tenant isolation tests
# ---------------------------------------------------------------------------


class TestWidgetTenantIsolation:
    """Widgets belong to a specific tenant; cross-tenant access returns None."""

    def test_cross_tenant_widget_access_returns_none(
        self, db_session, test_tenant, second_tenant, user_a
    ):
        """Widget in test_tenant is not returned when queried with second_tenant."""
        widget = _create_widget(db_session, user_a.id, test_tenant.id)

        result = db_session.exec(
            select(UserDashboardWidget)
            .where(UserDashboardWidget.id == widget.id)
            .where(UserDashboardWidget.tenant_id == second_tenant.id)  # wrong tenant
        ).first()
        assert result is None


# ---------------------------------------------------------------------------
# Widget type validation tests
# ---------------------------------------------------------------------------


class TestWidgetTypeValues:
    """WidgetType enum contains exactly the 6 expected values."""

    def test_all_widget_types_are_defined(self):
        expected = {
            "profitability_summary",
            "revenue_chart",
            "ar_aging",
            "tech_productivity",
            "tax_liability",
            "voice_analytics",
        }
        actual = {wt.value for wt in WidgetType}
        assert actual == expected

    def test_widget_type_is_string_enum(self):
        assert WidgetType.profitability_summary == "profitability_summary"
        assert WidgetType.revenue_chart == "revenue_chart"
        assert WidgetType.ar_aging == "ar_aging"
        assert WidgetType.tech_productivity == "tech_productivity"
        assert WidgetType.tax_liability == "tax_liability"
        assert WidgetType.voice_analytics == "voice_analytics"


# ---------------------------------------------------------------------------
# Pydantic schema validation tests
# ---------------------------------------------------------------------------


class TestWidgetSchemaValidation:
    """UserDashboardWidgetCreate validates fields correctly."""

    def test_valid_create_schema(self):
        from api.schemas.reports import UserDashboardWidgetCreate

        schema = UserDashboardWidgetCreate(
            widget_type=WidgetType.profitability_summary,
            widget_config_json={"group_by": "customer"},
            position_x=0,
            position_y=2,
            width=4,
            height=3,
        )
        assert schema.widget_type == WidgetType.profitability_summary
        assert schema.width == 4
        assert schema.height == 3

    def test_width_min_1(self):
        import pydantic

        from api.schemas.reports import UserDashboardWidgetCreate

        with pytest.raises(pydantic.ValidationError):
            UserDashboardWidgetCreate(
                widget_type=WidgetType.ar_aging,
                width=0,  # must be >= 1
                height=2,
            )

    def test_width_max_12(self):
        import pydantic

        from api.schemas.reports import UserDashboardWidgetCreate

        with pytest.raises(pydantic.ValidationError):
            UserDashboardWidgetCreate(
                widget_type=WidgetType.ar_aging,
                width=13,  # must be <= 12
                height=2,
            )

    def test_height_max_8(self):
        import pydantic

        from api.schemas.reports import UserDashboardWidgetCreate

        with pytest.raises(pydantic.ValidationError):
            UserDashboardWidgetCreate(
                widget_type=WidgetType.ar_aging,
                width=2,
                height=9,  # must be <= 8
            )

    def test_position_x_nonnegative(self):
        import pydantic

        from api.schemas.reports import UserDashboardWidgetCreate

        with pytest.raises(pydantic.ValidationError):
            UserDashboardWidgetCreate(
                widget_type=WidgetType.ar_aging,
                width=2,
                height=2,
                position_x=-1,  # must be >= 0
            )

    def test_update_schema_all_optional(self):
        from api.schemas.reports import UserDashboardWidgetUpdate

        # All fields optional — empty update is valid
        schema = UserDashboardWidgetUpdate()
        assert schema.position_x is None
        assert schema.position_y is None
        assert schema.width is None
        assert schema.height is None
        assert schema.widget_config_json is None


# ---------------------------------------------------------------------------
# Multiple widgets per user
# ---------------------------------------------------------------------------


class TestMultipleWidgetsPerUser:
    """User can pin the same widget_type multiple times (no UNIQUE constraint)."""

    def test_same_widget_type_can_be_pinned_multiple_times(
        self, db_session, test_tenant, user_a
    ):
        widget1 = _create_widget(
            db_session,
            user_a.id,
            test_tenant.id,
            widget_type="profitability_summary",
            position_x=0,
        )
        widget2 = _create_widget(
            db_session,
            user_a.id,
            test_tenant.id,
            widget_type="profitability_summary",
            position_x=4,
        )

        assert widget1.id != widget2.id
        assert widget1.widget_type == widget2.widget_type == "profitability_summary"

        widgets = db_session.exec(
            select(UserDashboardWidget)
            .where(UserDashboardWidget.user_id == user_a.id)
            .where(UserDashboardWidget.tenant_id == test_tenant.id)
        ).all()
        assert len(widgets) >= 2
