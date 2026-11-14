"""
Timezone awareness utilities for preventing naive datetime bugs.

This module provides helper functions to enforce timezone-aware datetimes
across the Pilot for Trades platform. Use these utilities in test contexts and
critical business logic to catch timezone-naive datetime bugs early.
"""

from datetime import UTC, datetime


class NaiveDatetimeError(ValueError):
    """
    Raised when a naive datetime is detected where an aware datetime is required.

    This error indicates a programming bug where timezone information was not
    properly attached to a datetime object. All Pilot for Trades datetimes must be
    timezone-aware (preferably UTC) to ensure consistent behavior across
    geographical regions and to comply with architecture requirements.
    """

    pass


def ensure_aware(dt: datetime, field_name: str = "datetime") -> datetime:
    """
    Validate that a datetime object is timezone-aware.

    Args:
        dt: Datetime object to validate
        field_name: Name of the field (for error messages)

    Returns:
        The same datetime object if it's timezone-aware

    Raises:
        NaiveDatetimeError: If the datetime is timezone-naive

    Example:
        from core.datetime_utils import ensure_aware

        def create_token(expires_at: datetime):
            expires_at = ensure_aware(expires_at, "expires_at")
            # ... rest of logic
    """
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise NaiveDatetimeError(
            f"Field '{field_name}' contains a timezone-naive datetime: {dt}. "
            f"All Pilot for Trades datetimes must be timezone-aware. "
            f"Use datetime.now(UTC) or datetime(..., tzinfo=UTC) instead."
        )
    return dt


def ensure_utc(dt: datetime, field_name: str = "datetime") -> datetime:
    """
    Validate that a datetime object is timezone-aware and in UTC.

    Args:
        dt: Datetime object to validate
        field_name: Name of the field (for error messages)

    Returns:
        The same datetime object if it's UTC-aware

    Raises:
        NaiveDatetimeError: If the datetime is timezone-naive or not UTC

    Example:
        from core.datetime_utils import ensure_utc

        def log_audit_event(occurred_at: datetime):
            occurred_at = ensure_utc(occurred_at, "occurred_at")
            # ... rest of logic
    """
    ensure_aware(dt, field_name)

    if dt.tzinfo != UTC:
        raise NaiveDatetimeError(
            f"Field '{field_name}' is not in UTC timezone: {dt} ({dt.tzinfo}). "
            f"Pilot for Trades requires all datetimes to be in UTC for consistency. "
            f"Convert using: dt.astimezone(UTC)"
        )
    return dt


def safe_now_utc() -> datetime:
    """
    Get current UTC time as a timezone-aware datetime.

    This is a convenience wrapper around datetime.now(UTC) that's more
    discoverable and less error-prone than importing UTC every time.

    Returns:
        Current UTC time with timezone information

    Example:
        from core.datetime_utils import safe_now_utc

        user.last_login_at = safe_now_utc()
    """
    from datetime import UTC

    return datetime.now(UTC)


def validate_model_datetimes(obj, field_names: list[str] | None = None) -> None:
    """
    Validate that all datetime fields on a model instance are timezone-aware.

    This is useful in test contexts to verify that model instances don't
    contain naive datetimes before committing to the database.

    Args:
        obj: Model instance to validate
        field_names: Optional list of field names to check. If None, checks all
                     attributes that are datetime instances.

    Raises:
        NaiveDatetimeError: If any datetime field is timezone-naive

    Example:
        from core.datetime_utils import validate_model_datetimes

        def test_user_creation(db_session):
            user = User(email="test@example.com")
            db_session.add(user)
            db_session.flush()

            # Verify no naive datetimes
            validate_model_datetimes(user)

            db_session.commit()
    """
    if field_names is None:
        # Auto-detect datetime fields
        field_names = [
            name
            for name in dir(obj)
            if not name.startswith("_")
            and isinstance(getattr(obj, name, None), datetime)
        ]

    for field_name in field_names:
        value = getattr(obj, field_name, None)
        if value is not None and isinstance(value, datetime):
            ensure_aware(value, f"{obj.__class__.__name__}.{field_name}")
