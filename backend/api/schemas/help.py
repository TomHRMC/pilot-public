"""
Pydantic request/response schemas for the Help System (B16).

Covers A85 (corpus), A84 (chat), A86 (context payload), A87 (feedback).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ──────────────────────────────────────────────────────────────────────────────
# A85 — RAG retrieval schemas
# ──────────────────────────────────────────────────────────────────────────────


class HelpRetrieveRequest(BaseModel):
    """Request body for POST /api/v1/help/retrieve (internal)."""

    query_embedding: list[float] = Field(
        description="Pre-computed 1536-dim query embedding"
    )
    role: str = Field(description="Requesting user's role for audience filtering")
    category_hint: str | None = Field(
        default=None, description="Optional category slug to narrow search"
    )
    k: int = Field(default=5, ge=1, le=20, description="Number of top chunks to return")


class HelpChunkResult(BaseModel):
    chunk_id: str
    article_id: str
    section_title: str
    chunk_text: str
    score: float


class HelpRetrieveResponse(BaseModel):
    chunks: list[HelpChunkResult]


class HelpArticleResponse(BaseModel):
    """Response for GET /api/v1/help/articles/{article_id}."""

    model_config = ConfigDict(from_attributes=True)

    article_id: str
    title: str
    category: str
    content_markdown: str
    audience: list[str]
    last_updated: str  # ISO date string


class AdminReprocessResponse(BaseModel):
    status: str
    article_id: str


# ──────────────────────────────────────────────────────────────────────────────
# A84 — Help chat schemas
# ──────────────────────────────────────────────────────────────────────────────


class HelpContextPayload(BaseModel):
    """
    A86 — Surface context sent with each user message.
    Contract: route, entity_type, recent_actions, user_role, tenant_metadata.
    All fields are optional — client sends what's available.
    """

    route: str | None = Field(
        default=None,
        description="Current app route/page e.g. '/settings/integrations/quickbooks'",
    )
    entity_type: str | None = Field(
        default=None, description="Entity in focus e.g. 'quote', 'job'"
    )
    recent_actions: list[str] | None = Field(
        default=None, description="Recent user action labels"
    )
    user_role: str | None = Field(default=None, description="Current user's role")
    tenant_metadata: dict[str, Any] | None = Field(
        default=None, description="Non-PII tenant context e.g. {size, trade}"
    )


class HelpChatRequest(BaseModel):
    """Request body for POST /api/v1/help/chat."""

    session_id: UUID | None = Field(
        default=None, description="Existing session UUID or null to start new"
    )
    message: str = Field(
        min_length=1, max_length=4000, description="User's question text"
    )
    context_payload: HelpContextPayload | None = Field(default=None)


class HelpChatResponse(BaseModel):
    """Response for POST /api/v1/help/chat."""

    session_id: UUID
    message_id: UUID
    role: str
    content: str
    retrieved_article_ids: list[str]
    session_title: str | None


class HelpSessionSummary(BaseModel):
    """One item in the sessions list response."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    # FIND-169: HelpChatSession PK renamed from session_id → id
    # The API response uses 'session_id' for backwards-compat; model field is 'id'
    session_id: UUID = Field(alias="id")
    title: str | None
    outcome: str | None
    message_count: int
    last_activity_at: datetime
    started_at: datetime


class HelpSessionListResponse(BaseModel):
    sessions: list[HelpSessionSummary]
    total: int


class HelpMessageDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message_id: UUID
    role: str
    content: str
    created_at: datetime
    voice_used: bool


class HelpSessionDetailResponse(BaseModel):
    """Response for GET /api/v1/help/sessions/{session_id}."""

    session_id: UUID
    title: str | None
    outcome: str | None
    messages: list[HelpMessageDetail]


class HelpSessionFeedbackRequest(BaseModel):
    """Request for POST /api/v1/help/sessions/{session_id}/feedback."""

    signal: str = Field(description="One of: resolved, escalated, abandoned")


class HelpSessionFeedbackResponse(BaseModel):
    session_id: UUID
    outcome: str


class HelpSessionDeleteResponse(BaseModel):
    """Response for DELETE /api/v1/help/sessions/{session_id}."""

    message: str
    session_id: UUID


# ──────────────────────────────────────────────────────────────────────────────
# A87 — Feedback submission schemas
# ──────────────────────────────────────────────────────────────────────────────


class FeedbackSubmitRequest(BaseModel):
    """Request body for POST /api/v1/feedback."""

    category: str = Field(description="bug | feature_request | question | general")
    body: str = Field(min_length=10, max_length=10000, description="Full feedback text")
    from_help_chat_session_id: UUID | None = Field(default=None)


class FeedbackSubmitResponse(BaseModel):
    submission_id: UUID
    category: str
    submitted_at: datetime
    confirmation_message: str
