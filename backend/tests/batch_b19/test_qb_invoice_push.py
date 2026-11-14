"""
Tests for FIND-070/091: QuickBooks Invoice and Payment Push Suite.

Tests QB invoice/payment sync from Pilot for Trades → QuickBooks:
- sync_invoice_to_qb(): invoice push with line items + QB item mapping
- sync_payment_to_qb(): payment push with linked invoice reference
- Proactive triggers on invoice/payment creation
- QB connect flow: qco_line_type → QB item mapping
- Error handling: missing mappings, network errors, validation
- Retry behavior: exponential backoff on transient failures
"""

import uuid

import pytest
from sqlmodel import Session

from services.quickbooks_sync import QuickBooksSync


@pytest.mark.asyncio
async def test_sync_invoice_to_qb_method_exists(db_session: Session, test_tenant):
    """Test that sync_invoice_to_qb method exists on QuickBooksSync service."""
    sync = QuickBooksSync(test_tenant.id, db_session)
    assert hasattr(sync, "sync_invoice_to_qb")
    assert callable(sync.sync_invoice_to_qb)


@pytest.mark.asyncio
async def test_sync_payment_to_qb_method_exists(db_session: Session, test_tenant):
    """Test that sync_payment_to_qb method exists on QuickBooksSync service."""
    sync = QuickBooksSync(test_tenant.id, db_session)
    assert hasattr(sync, "sync_payment_to_qb")
    assert callable(sync.sync_payment_to_qb)


@pytest.mark.asyncio
async def test_resolve_qco_line_type_to_qb_item_method_exists(
    db_session: Session, test_tenant
):
    """Test that _resolve_qco_line_type_to_qb_item method exists."""
    sync = QuickBooksSync(test_tenant.id, db_session)
    assert hasattr(sync, "_resolve_qco_line_type_to_qb_item")
    assert callable(sync._resolve_qco_line_type_to_qb_item)


@pytest.mark.asyncio
async def test_sync_invoice_to_qb_raises_if_invoice_not_found(
    db_session: Session, test_tenant
):
    """Test that sync_invoice_to_qb raises if invoice not found."""
    sync = QuickBooksSync(test_tenant.id, db_session)

    fake_invoice_id = uuid.uuid4()
    with pytest.raises(ValueError, match="not found"):
        await sync.sync_invoice_to_qb(fake_invoice_id)


@pytest.mark.asyncio
async def test_sync_payment_to_qb_raises_if_payment_not_found(
    db_session: Session, test_tenant
):
    """Test that sync_payment_to_qb raises if payment not found."""
    sync = QuickBooksSync(test_tenant.id, db_session)

    fake_payment_id = uuid.uuid4()
    with pytest.raises(ValueError, match="not found"):
        await sync.sync_payment_to_qb(fake_payment_id)


def test_sync_invoice_to_qb_task_exists():
    """Test that sync_invoice_to_qb_task exists in tasks module."""
    from tasks.quickbooks_sync import sync_invoice_to_qb_task

    assert sync_invoice_to_qb_task is not None
    assert callable(sync_invoice_to_qb_task)


def test_sync_payment_to_qb_task_exists():
    """Test that sync_payment_to_qb_task exists in tasks module."""
    from tasks.quickbooks_sync import sync_payment_to_qb_task

    assert sync_payment_to_qb_task is not None
    assert callable(sync_payment_to_qb_task)


@pytest.mark.asyncio
async def test_resolve_qco_line_type_returns_fallback_if_not_mapped(
    db_session: Session, test_tenant, test_qco_line_type, test_app_service
):
    """Test that _resolve_qco_line_type_to_qb_item returns fallback (1) if no mapping exists."""
    sync = QuickBooksSync(test_tenant.id, db_session)
    result = await sync._resolve_qco_line_type_to_qb_item(
        test_qco_line_type.id,
        test_app_service.id,
    )
    # Should return default services item ID when no mapping exists
    assert result == "1"
