"""
Test context helper for unauthenticated test endpoints.

This module provides TestUserContext, a mock user context that enables
testing API endpoints without JWT authentication in dev/qa environments.

Security:
    - Only available when TEST_ENDPOINT_ENABLED=true
    - Only available in dev/qa environments (blocked in staging/production)
    - Returns HTTP 403 if disabled or in wrong environment

Usage:
    from core.test_context import get_test_context

    @router.post("/test")
    def create_resource_test(data: ResourceCreate, db: Session = Depends(get_db)):
        test_context = get_test_context()  # Raises 403 if disabled
        return _create_resource_impl(data, db, test_context)
"""

from uuid import UUID

from fastapi import HTTPException, status
from pydantic import BaseModel, ConfigDict

from .config import is_test_endpoint_allowed, settings
from .datetime_utils import validate_model_datetimes


class TestUserContext(BaseModel):
    """
    Mock user context for test endpoints.

    Designed to have an identical interface to the User model for
    compatibility with shared business logic functions.

    Attributes:
        id: Test user UUID
        tenant_id: Test tenant UUID (hardcoded test isolation)
        email: Test user email (test@pilot.local)
        first_name: Test user first name
        last_name: Test user last name

    Note:
        This class provides tenant_id attribute that the User model
        currently lacks (Gap #40). Once Gap #40 is resolved, both
        User and TestUserContext will have symmetric interfaces.
    """

    __test__ = False  # Tell pytest not to collect this as a test class

    id: UUID
    tenant_id: UUID
    email: str = "test@pilot.local"
    first_name: str = "Test"
    last_name: str = "User"
    # STRIPE-CONNECT-1 A4: role_code for owner-guard checks on /test endpoints.
    # The canonical test user (TEST_USER_ID) is the owner of the test tenant.
    role_code: str = "owner"

    model_config = ConfigDict(frozen=True)  # Immutable for safety

    def headers(self) -> dict:
        """
        Return minimal headers dict for test endpoint requests.

        Test endpoints use Depends(get_test_context) which injects the context
        via FastAPI dependency injection, so no special headers are required.
        This method returns an empty dict to satisfy test code that calls it.

        Returns:
            Empty dict (test endpoints don't require authentication headers)
        """
        return {}


def get_test_context() -> TestUserContext:
    """
    Get test user context for unauthenticated test endpoints.

    This function serves as a FastAPI dependency replacement for
    get_current_user() in test endpoint variants.

    Returns:
        TestUserContext with hardcoded test tenant and user IDs

    Raises:
        HTTPException(403): If test endpoints are disabled via environment
                           variables or if running in staging/production

    Example:
        @router.post("/customers/test")
        def create_customer_test(
            customer_in: CustomerCreate,
            db: Session = Depends(get_db),
        ):
            test_context = get_test_context()  # No JWT needed
            return _create_customer_impl(customer_in, db, test_context)

    Security:
        - Checks TEST_ENDPOINT_ENABLED environment variable
        - Checks ENVIRONMENT is 'dev' or 'qa'
        - Fails closed (403) if checks don't pass
    """
    if not is_test_endpoint_allowed():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "test_endpoints_disabled",
                "message": (
                    "Test endpoints are only available in DEV/QA environments "
                    "when TEST_ENDPOINT_ENABLED=true. "
                    f"Current environment: {settings.ENVIRONMENT}, "
                    f"TEST_ENDPOINT_ENABLED={settings.TEST_ENDPOINT_ENABLED}"
                ),
                "hint": (
                    "If you're in development, set TEST_ENDPOINT_ENABLED=true "
                    "and ENVIRONMENT=dev in your .env file"
                ),
            },
        )

    return TestUserContext(
        id=UUID(settings.TEST_USER_ID), tenant_id=UUID(settings.TEST_TENANT_ID)
    )


def validate_test_model(obj) -> None:
    """
    Validate that a model instance created in tests has timezone-aware datetimes.

    This function should be called after creating model instances in test
    contexts to catch naive datetime bugs early.

    Note: This is a test-time safeguard. In production, Pydantic's AwareDatetime
    type prevents naive datetimes from entering via API requests.

    Usage:
        from core.test_context import validate_test_model

        def test_quote_creation(db_session):
            quote = Quote(...)
            db_session.add(quote)
            db_session.flush()

            validate_test_model(quote)  # Raises if any datetimes are naive

            db_session.commit()
    """
    validate_model_datetimes(obj)
