# backend/api/schemas/recurrence.py
# B21: Request/response schemas for job recurrence rule CRUD endpoints.

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

RecurrencePattern = Literal["daily", "weekly", "monthly", "annually"]


class RecurrenceRuleCreate(BaseModel):
    customer_id: uuid.UUID
    site_id: uuid.UUID
    pattern: RecurrencePattern
    interval_count: int = Field(default=1, ge=1)
    starts_on: date
    ends_on: date | None = None
    max_occurrences: int | None = Field(default=None, ge=1)
    estimated_duration_minutes: int | None = Field(default=None, ge=1)
    default_tech_user_id: uuid.UUID | None = None
    notes_template: str | None = None

    @model_validator(mode="after")
    def validate_end_conditions(self) -> "RecurrenceRuleCreate":
        if self.ends_on and self.starts_on and self.ends_on < self.starts_on:
            raise ValueError("ends_on must be on or after starts_on")
        if self.ends_on and self.max_occurrences:
            raise ValueError("Specify ends_on OR max_occurrences, not both")
        return self


class RecurrenceRuleUpdate(BaseModel):
    """Only these fields are patchable. pattern/interval_count/starts_on are immutable."""

    is_active: bool | None = None
    ends_on: date | None = None
    max_occurrences: int | None = Field(default=None, ge=1)
    default_tech_user_id: uuid.UUID | None = None
    notes_template: str | None = None
    estimated_duration_minutes: int | None = Field(default=None, ge=1)


class RecurrenceRuleResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    customer_id: uuid.UUID
    site_id: uuid.UUID
    pattern: str
    interval_count: int
    starts_on: date
    ends_on: date | None
    max_occurrences: int | None
    occurrences_created: int
    next_job_at: datetime | None
    last_job_created_at: datetime | None
    estimated_duration_minutes: int | None
    default_tech_user_id: uuid.UUID | None
    notes_template: str | None
    is_active: bool
    first_job_id: uuid.UUID | None = None  # only set on POST create response

    model_config = {"from_attributes": True}


class RecurrenceRuleListItem(BaseModel):
    id: uuid.UUID
    pattern: str
    interval_count: int
    customer_name: str | None
    site_address: str | None
    next_job_at: datetime | None
    occurrences_created: int
    is_active: bool
    default_tech_display_name: str | None

    model_config = {"from_attributes": True}


class RecurrenceRuleListResponse(BaseModel):
    items: list[RecurrenceRuleListItem]
    total: int
