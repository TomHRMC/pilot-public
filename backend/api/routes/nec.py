"""
NEC Calculation API Routes — MOB-B0

Endpoints:
  POST /api/v1/nec/calculate        — Run NEC calc online, persist to nec_calculation_log
  POST /api/v1/nec/calculate/test   — No-auth test endpoint (same _impl)
  POST /api/v1/nec/calc-logs        — Save offline calc result (sync endpoint)
  POST /api/v1/nec/calc-logs/test   — No-auth test endpoint
  GET  /api/v1/nec/calc-logs        — List calc logs for current tenant
  GET  /api/v1/nec/calc-logs/test   — No-auth test endpoint

RBAC: nec.calculate (already seeded in technician role — no new seed needed).
Multi-tenancy: All queries include .where(tenant_id == user_context.tenant_id).
db.get() is permanently banned on NecCalculationLog.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from api.schemas.nec import (
    NecCalcLogCreate,
    NecCalcLogResponse,
    NecCalculateRequest,
    NecCalculateResponse,
)
from app.models.fulfillment import NecCalculationLog
from core.auth import AuthenticatedUser
from core.db import get_db
from core.permissions import require_permission
from core.test_context import TestUserContext, get_test_context
from services import nec_service

router = APIRouter()


# ==================== SHARED BUSINESS LOGIC ====================


def _nec_calculate_impl(
    calc_in: NecCalculateRequest,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> NecCalculateResponse:
    """
    Run NEC calculation and persist result to nec_calculation_log.

    Idempotency: if idempotency_key provided and already exists, return existing result (200).
    No db.get() — always uses tenant-scoped select().
    """
    # 1. Idempotency check — return existing result if key already present
    if calc_in.idempotency_key:
        existing = db.exec(
            select(NecCalculationLog)
            .where(NecCalculationLog.idempotency_key == calc_in.idempotency_key)
            .where(NecCalculationLog.tenant_id == user_context.tenant_id)
        ).first()
        if existing:
            result_dict = existing.result_json
            return NecCalculateResponse(
                log_id=existing.id,
                calc_type=existing.calc_type,
                result=result_dict,
                nec_guide_version=existing.nec_guide_version,
                nec_citation=result_dict.get("nec_citation", ""),
            )

    # 2. Run NEC calculation via nec_service
    try:
        calc_result = nec_service.calculate(calc_in.calc_type, calc_in.inputs)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # 3. Persist to nec_calculation_log
    log = NecCalculationLog(
        tenant_id=user_context.tenant_id,
        user_id=user_context.id,
        job_id=calc_in.job_id,
        calc_type=calc_in.calc_type,
        nec_guide_version="2023",
        inputs_json=calc_in.inputs,
        result_json=calc_result.to_dict(),
        is_offline_calc=False,
        idempotency_key=calc_in.idempotency_key,
        created_by=user_context.id,
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    return NecCalculateResponse(
        log_id=log.id,
        calc_type=calc_in.calc_type,
        result=calc_result.to_dict(),
        nec_guide_version="2023",
        nec_citation=calc_result.nec_citation,
    )


def _nec_calc_log_create_impl(
    log_in: NecCalcLogCreate,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> dict:
    """
    Save a pre-computed offline NEC calculation result (mobile sync endpoint).

    Idempotent: if idempotency_key already saved, return existing log_id with 200.
    """
    if log_in.idempotency_key:
        existing = db.exec(
            select(NecCalculationLog)
            .where(NecCalculationLog.idempotency_key == log_in.idempotency_key)
            .where(NecCalculationLog.tenant_id == user_context.tenant_id)
        ).first()
        if existing:
            return {"log_id": existing.id}

    log = NecCalculationLog(
        tenant_id=user_context.tenant_id,
        user_id=user_context.id,
        job_id=log_in.job_id,
        calc_type=log_in.calc_type,
        nec_guide_version=log_in.nec_guide_version,
        inputs_json=log_in.inputs,
        result_json=log_in.result,
        is_offline_calc=True,
        idempotency_key=log_in.idempotency_key,
        client_capture_at=log_in.client_capture_at,
        created_by=user_context.id,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return {"log_id": log.id}


def _list_nec_calc_logs_impl(
    job_id: UUID | None,
    limit: int,
    offset: int,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> list[NecCalcLogResponse]:
    """List NEC calculation logs for current tenant, optionally filtered by job_id."""
    stmt = (
        select(NecCalculationLog)
        .where(NecCalculationLog.tenant_id == user_context.tenant_id)
        .order_by(NecCalculationLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if job_id:
        stmt = stmt.where(NecCalculationLog.job_id == job_id)

    logs = db.exec(stmt).all()
    return [
        NecCalcLogResponse(
            id=log.id,
            calc_type=log.calc_type,
            nec_guide_version=log.nec_guide_version,
            inputs_json=log.inputs_json,
            result_json=log.result_json,
            is_offline_calc=log.is_offline_calc,
            client_capture_at=log.client_capture_at,
            job_id=log.job_id,
            created_at=log.created_at,
        )
        for log in logs
    ]


# ==================== AUTHENTICATED ENDPOINTS ====================


@router.post("/calculate", status_code=status.HTTP_201_CREATED)
async def nec_calculate(
    calc_in: NecCalculateRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("nec.calculate")),
) -> NecCalculateResponse:
    """Run NEC calculation and persist result. RBAC: nec.calculate."""
    return _nec_calculate_impl(calc_in, db, current_user)


@router.post("/calc-logs", status_code=status.HTTP_201_CREATED)
async def create_nec_calc_log(
    log_in: NecCalcLogCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("nec.calculate")),
) -> dict:
    """Save offline calculation result (mobile sync). RBAC: nec.calculate."""
    return _nec_calc_log_create_impl(log_in, db, current_user)


@router.get("/calc-logs")
async def list_nec_calc_logs(
    job_id: UUID | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("nec.calculate")),
) -> list[NecCalcLogResponse]:
    """List NEC calc logs for current tenant. RBAC: nec.calculate."""
    return _list_nec_calc_logs_impl(job_id, limit, offset, db, current_user)


# ==================== TEST (NO-AUTH) ENDPOINTS ====================


@router.post("/calculate/test", status_code=status.HTTP_201_CREATED)
async def nec_calculate_test(
    calc_in: NecCalculateRequest,
    db: Session = Depends(get_db),
) -> NecCalculateResponse:
    """No-auth test endpoint — same logic as /calculate. Uses get_test_context()."""
    test_context = get_test_context()
    return _nec_calculate_impl(calc_in, db, test_context)


@router.post("/calc-logs/test", status_code=status.HTTP_201_CREATED)
async def create_nec_calc_log_test(
    log_in: NecCalcLogCreate,
    db: Session = Depends(get_db),
) -> dict:
    """No-auth test endpoint — same logic as /calc-logs. Uses get_test_context()."""
    test_context = get_test_context()
    return _nec_calc_log_create_impl(log_in, db, test_context)


@router.get("/calc-logs/test")
async def list_nec_calc_logs_test(
    job_id: UUID | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> list[NecCalcLogResponse]:
    """No-auth test endpoint — same logic as GET /calc-logs. Uses get_test_context()."""
    test_context = get_test_context()
    return _list_nec_calc_logs_impl(job_id, limit, offset, db, test_context)
