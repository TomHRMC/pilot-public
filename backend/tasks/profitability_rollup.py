"""
Background job to recalculate job profitability metrics.

This task updates job.actual_labor_cost_cents, job.actual_material_cost_cents,
and job.actual_profit_cents by summing related time entries and expenses.

Design Specification: Task #13 - Profitability Rollup Worker
Gap Reference: Gap #10, #25 in phase-1-4-implementation-gap-analysis.md

Usage:
    # Trigger after creating time entry or expense
    from tasks.profitability_rollup import calculate_job_profitability
    calculate_job_profitability.delay(str(job_id))

    # Manual execution for testing
    python -c "from tasks.profitability_rollup import recalculate_job_profitability_sync; recalculate_job_profitability_sync('job-uuid-here')"
"""

import logging
from typing import Any
from uuid import UUID

from sqlmodel import Session, func, select

from app.models.fulfillment import Job, JobExpense, JobTimeEntry
from core.celery_app import celery_app
from core.db import get_db

logger = logging.getLogger(__name__)


def _calculate_job_profitability_impl(job_id: str, db: Session) -> dict[str, Any]:
    """
    Internal implementation of profitability calculation.
    Separated for dependency injection in tests.

    Args:
        job_id: UUID string of the job to recalculate
        db: Database session to use

    Returns:
        dict with updated values for verification

    Raises:
        ValueError: If job_id is invalid or job not found
    """
    # Validate UUID format
    try:
        job_uuid = UUID(job_id)
    except (ValueError, AttributeError) as e:
        logger.error(f"Invalid job_id format: {job_id} - {e}")
        raise ValueError(f"Invalid job_id format: {job_id}")

    # Lock the job row for update (prevents race conditions)
    job = db.exec(select(Job).where(Job.id == job_uuid).with_for_update()).first()

    if not job:
        logger.error(f"Job not found: {job_id}")
        raise ValueError(f"Job not found: {job_id}")

    logger.info(
        f"Recalculating profitability for job {job_id} (tenant: {job.tenant_id})"
    )

    # Calculate labor costs (sum of all time entries)
    labor_result = db.exec(
        select(
            func.sum(JobTimeEntry.total_cost_cents).label("total"),
            func.count(JobTimeEntry.id).label("count"),
        ).where(JobTimeEntry.job_id == job_uuid)
    ).first()

    actual_labor_cost_cents = int(labor_result.total or 0)
    time_entry_count = int(labor_result.count or 0)

    # Calculate material costs (sum of all expenses)
    expense_result = db.exec(
        select(
            func.sum(JobExpense.cost_cents).label("total"),
            func.count(JobExpense.id).label("count"),
        )
        .where(JobExpense.job_id == job_uuid)
        .where(JobExpense.tenant_id == job.tenant_id)  # Extra safety
    ).first()

    actual_material_cost_cents = int(expense_result.total or 0)
    expense_count = int(expense_result.count or 0)

    # Calculate profit
    # For MVP: Use 0 for invoiced_total since Job model doesn't have this field yet
    # Future: Join to invoice table or add invoiced_total_cents to Job model
    invoiced_total_cents = 0  # TODO: Get from invoice when available
    actual_profit_cents = (
        invoiced_total_cents - actual_labor_cost_cents - actual_material_cost_cents
    )

    # Update job atomically
    job.actual_labor_cost_cents = actual_labor_cost_cents
    job.actual_material_cost_cents = actual_material_cost_cents
    job.actual_profit_cents = actual_profit_cents

    db.add(job)
    db.commit()
    db.refresh(job)

    result = {
        "job_id": str(job.id),
        "actual_labor_cost_cents": actual_labor_cost_cents,
        "actual_material_cost_cents": actual_material_cost_cents,
        "actual_profit_cents": actual_profit_cents,
        "time_entry_count": time_entry_count,
        "expense_count": expense_count,
    }

    logger.info(
        f"Profitability recalculated for job {job_id}: "
        f"labor=${actual_labor_cost_cents / 100:.2f}, "
        f"materials=${actual_material_cost_cents / 100:.2f}, "
        f"profit=${actual_profit_cents / 100:.2f}"
    )

    return result


@celery_app.task(name="calculate_job_profitability", bind=True, max_retries=3)
def calculate_job_profitability(self, job_id: str) -> dict[str, Any]:
    """
    Recalculate job profitability by summing:
    - job_time_entry.total_cost_cents → actual_labor_cost_cents
    - job_expense.cost_cents → actual_material_cost_cents
    - invoiced_total - actual_costs → actual_profit_cents

    Args:
        job_id: UUID string of the job to recalculate

    Returns:
        dict with updated values for verification:
        {
            "job_id": str,
            "actual_labor_cost_cents": int,
            "actual_material_cost_cents": int,
            "actual_profit_cents": int,
            "time_entry_count": int,
            "expense_count": int,
        }

    Raises:
        ValueError: If job_id is invalid or job not found
        Exception: Database errors (will retry up to 3 times)

    Example:
        >>> result = calculate_job_profitability.delay('a1b2c3d4-...')
        >>> result.get()
        {
            "job_id": "a1b2c3d4-...",
            "actual_labor_cost_cents": 68000,
            "actual_material_cost_cents": 12000,
            "actual_profit_cents": -80000,
            "time_entry_count": 1,
            "expense_count": 2
        }
    """
    # Get database session
    db: Session = next(get_db())

    try:
        result = _calculate_job_profitability_impl(job_id, db)
        return result

    except ValueError:
        # Don't retry validation errors — db.close() handled in finally
        db.rollback()
        raise

    except Exception as e:
        db.rollback()
        logger.error(f"Error recalculating profitability for job {job_id}: {e}")
        # Retry on database errors — db.close() handled in finally
        raise self.retry(exc=e, countdown=60)  # Retry after 1 minute

    finally:
        db.close()


# Standalone function for manual execution and testing
def recalculate_job_profitability_sync(
    job_id: str, db: Session = None
) -> dict[str, Any]:
    """
    Synchronous version for manual testing or scripts.

    Args:
        job_id: UUID string of the job to recalculate
        db: Optional database session (for testing)

    Returns:
        dict with updated profitability values

    Example:
        >>> from tasks.profitability_rollup import recalculate_job_profitability_sync
        >>> result = recalculate_job_profitability_sync('a1b2c3d4-...')
    """
    if db is None:
        # Production use: create new session
        db = next(get_db())
        try:
            return _calculate_job_profitability_impl(job_id, db)
        finally:
            db.close()
    else:
        # Test use: use provided session
        return _calculate_job_profitability_impl(job_id, db)


if __name__ == "__main__":
    """
    Run profitability recalculation manually for testing.
    
    Usage:
        python -m tasks.profitability_rollup
        
    Then enter job UUID when prompted.
    """
    import sys

    if len(sys.argv) > 1:
        job_id = sys.argv[1]
    else:
        job_id = input("Enter job UUID: ").strip()

    print(f"Recalculating profitability for job {job_id}...")
    result = recalculate_job_profitability_sync(job_id)
    print("\nResult:")
    print(f"  Job ID: {result['job_id']}")
    print(f"  Labor Cost: ${result['actual_labor_cost_cents'] / 100:.2f}")
    print(f"  Material Cost: ${result['actual_material_cost_cents'] / 100:.2f}")
    print(f"  Profit: ${result['actual_profit_cents'] / 100:.2f}")
    print(f"  Time Entries: {result['time_entry_count']}")
    print(f"  Expenses: {result['expense_count']}")
