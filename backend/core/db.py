import os
import uuid

from sqlalchemy import text
from sqlmodel import Session, create_engine

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://pilot_user:CHANGE_ME_LOCAL_DB_PW@localhost:5432/pilot_dev"
)
engine = create_engine(DATABASE_URL, echo=False)


def get_db():
    with Session(engine) as session:
        yield session


def set_audit_context_sync(db: Session, user_id: uuid.UUID) -> None:
    """
    Set PostgreSQL session variable for audit trail user tracking.

    This function sets the app.user_id session variable that the audit.log_changes()
    trigger function reads to capture which user made a change. Must be called within
    the same database transaction as the mutation being audited.

    Uses SET LOCAL which means the variable only lasts for the current transaction
    and is automatically cleaned up on COMMIT or ROLLBACK. This prevents cross-
    transaction contamination in connection pooling scenarios.

    Args:
        db: Active database session
        user_id: UUID of authenticated user making the change

    Example:
        from core.auth import get_current_user
        from core.db import set_audit_context_sync

        @router.post("/customers")
        def create_customer(
            customer: CustomerCreate,
            db: Session = Depends(get_db),
            current_user: AuthenticatedUser = Depends(get_current_user)
        ):
            # Set audit context before mutation
            set_audit_context_sync(db, current_user.id)

            # Create customer - trigger will capture user_id
            new_customer = Customer(**customer.dict(), tenant_id=current_user.tenant_id)
            db.add(new_customer)
            db.commit()  # Trigger fires here with user_id

            return new_customer

    Design Reference:
        Task #20 - Audit Event Logging
        Gap #29 in phase-1-4-implementation-gap-analysis.md
        dev-docs/analysis/phase-1-5-tasks/task-20-audit-logging-impl-plan.md
    """
    db.execute(text(f"SET LOCAL app.user_id = '{user_id}'"))


async def set_audit_context(db: Session, user_id: uuid.UUID) -> None:
    """
    Async version of set_audit_context_sync for async routes.

    Args:
        db: Active database session
        user_id: UUID of authenticated user making the change

    Note:
        Most Pilot for Trades routes are synchronous, so set_audit_context_sync() is preferred.
        This async version is provided for future async endpoints.
    """
    await db.execute(text(f"SET LOCAL app.user_id = '{user_id}'"))
