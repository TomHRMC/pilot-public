"""
NEC Calculation API Schemas — MOB-B0

Request/Response schemas for POST /api/v1/nec/calculate,
POST /api/v1/nec/calc-logs, and GET /api/v1/nec/calc-logs.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class NecCalculateRequest(BaseModel):
    """Request body for POST /api/v1/nec/calculate."""

    calc_type: str = Field(
        ...,
        description="Calculation type: 'voltage_drop' | 'conduit_fill' | 'ampacity'",
    )
    inputs: dict = Field(
        ...,
        description="Calculation inputs — keys depend on calc_type",
    )
    job_id: uuid.UUID | None = Field(
        default=None,
        description="Optional job UUID to link this calculation to a job",
    )
    idempotency_key: uuid.UUID | None = Field(
        default=None,
        description="Optional UUID for dedup (used by offline sync replay)",
    )


class NecCalculateResponse(BaseModel):
    """Response body for POST /api/v1/nec/calculate (201)."""

    log_id: uuid.UUID
    calc_type: str
    result: dict  # NecCalcResult.to_dict() output
    nec_guide_version: str
    nec_citation: str


class NecCalcLogCreate(BaseModel):
    """Request body for POST /api/v1/nec/calc-logs (offline sync endpoint)."""

    calc_type: str
    inputs: dict
    result: dict
    nec_guide_version: str = "2023"
    is_offline_calc: bool = True
    client_capture_at: datetime | None = None
    idempotency_key: uuid.UUID | None = None
    job_id: uuid.UUID | None = None


class NecCalcLogResponse(BaseModel):
    """Response body item for GET /api/v1/nec/calc-logs."""

    id: uuid.UUID
    calc_type: str
    nec_guide_version: str
    inputs_json: dict
    result_json: dict
    is_offline_calc: bool
    client_capture_at: datetime | None
    job_id: uuid.UUID | None
    created_at: datetime
