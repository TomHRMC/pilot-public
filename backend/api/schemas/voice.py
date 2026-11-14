"""
Voice AI Schemas
================
Canonical Pydantic schemas for Voice AI context window and related data structures.

Task 1-C-5: Defines the canonical `ContextWindowSchema` for `conversation_session.context_window_json`.
Adds `safety_loto_verified` (bool, default False) and `current_technical_context` (dict)
to enforce LOTO checkpoint confirmation before job completion.

Task 1-E-3: Adds `NecVoltageDropArgs`, `NecVoltageDropResult`, `NecConduitFillArgs`,
and `NecConduitFillResult` Pydantic models for NEC calculation handler I/O.
"""

from typing import Any

from pydantic import BaseModel, Field


class ContextWindowSchema(BaseModel):
    """
    Canonical schema for `conversation_session.context_window_json` (JSONB).

    This model defines the expected shape of the JSON stored in the context window.
    It is used for read validation and write serialization in the Voice AI layer.
    The underlying DB column is JSONB — no migration required for field additions.

    LOTO Safety Fields (Task 1-C-5):
    - safety_loto_verified: bool — must be True before the Voice AI allows
      job.complete or time_entry.stop actions. The field technician confirms all
      lockout/tagout procedures are in place before closing out the job.
    - current_technical_context: dict — holds the active NEC calculation context,
      panel schedule, circuit details, or any structured technical data the AI
      should carry across turns (e.g., wire gauge selected, conduit fill result).

    Active Entity Tracking Fields:
    - active_quote_id: str | None — UUID of the quote currently being built
    - active_job_id: str | None — UUID of the job currently being worked
    - active_customer_id: str | None — UUID of the customer in focus
    - active_site_id: str | None — UUID of the site in focus
    - last_action: str | None — last intent type executed (e.g., "create_quote")
    - timestamp: str | None — ISO 8601 UTC timestamp of the last context update
    """

    # --- LOTO Safety Fields (Task 1-C-5) ---
    safety_loto_verified: bool = Field(
        default=False,
        description=(
            "LOTO checkpoint: must be True before job completion or time_entry.stop. "
            "The technician confirms all Lock Out / Tag Out procedures are in place. "
            "Resets to False whenever a new job becomes active in context."
        ),
    )
    current_technical_context: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Structured technical data carried across Voice AI turns. "
            "Examples: {'wire_gauge': '12 AWG', 'conduit_fill_pct': 34.2, "
            "'panel_amperage': 200, 'nec_article': '210.52'}. "
            "Populated by NEC calculation handlers and cleared on job close."
        ),
    )

    # --- Active Entity Tracking ---
    active_quote_id: str | None = Field(
        default=None,
        description="UUID of the quote currently being built in this session.",
    )
    active_job_id: str | None = Field(
        default=None,
        description="UUID of the job currently being worked in this session.",
    )
    active_customer_id: str | None = Field(
        default=None,
        description="UUID of the customer currently in focus.",
    )
    active_site_id: str | None = Field(
        default=None,
        description="UUID of the site currently in focus.",
    )
    last_action: str | None = Field(
        default=None,
        description="Last intent type executed (e.g., 'create_quote', 'add_line').",
    )
    timestamp: str | None = Field(
        default=None,
        description="ISO 8601 UTC timestamp of the last context window update.",
    )

    model_config = {"extra": "allow"}  # Allow unknown fields from older sessions

    def to_jsonb(self) -> dict[str, Any]:
        """Serialize to a plain dict for storage in the JSONB column."""
        return self.model_dump(exclude_none=False)

    @classmethod
    def from_jsonb(cls, data: dict[str, Any] | None) -> "ContextWindowSchema":
        """
        Deserialize from a JSONB dict (e.g., session.context_window_json).
        Safely handles None and legacy sessions that predate this schema.
        """
        if data is None:
            return cls()
        return cls.model_validate(data)


# ==================== NEC CALCULATION SCHEMAS (Task 1-E-3) ====================


class NecVoltageDropArgs(BaseModel):
    """
    Parsed intent arguments from Ollama for NEC voltage drop calculations.

    Represents the technician's spoken input after Ollama extracts entities
    like "Calculate voltage drop for 20 amps on 100 feet of 12 AWG".

    Formula used (single-phase):
        V_D = (2 × K × I × D) / CM
    where:
        K  = 12.9 (approximate copper resistivity constant, ohm-cmil/ft)
        I  = amperage (amps)
        D  = one-way distance in feet
        CM = circular mils from AWG gauge table
    """

    amperage: float = Field(
        ...,
        gt=0,
        description="Load amperage in amps (e.g., 20.0 for a 20-amp circuit).",
    )
    distance_feet: float = Field(
        ...,
        gt=0,
        description="One-way wire run distance in feet.",
    )
    wire_gauge: str = Field(
        ...,
        description="AWG wire gauge string (e.g., '12', '10', '8', '6', '4', '2', '1/0', '2/0', '3/0', '4/0').",
    )
    voltage: float = Field(
        default=120.0,
        gt=0,
        description="System voltage (120, 240, 208, 480). Defaults to 120V.",
    )
    phase: int = Field(
        default=1,
        ge=1,
        le=3,
        description="1 for single-phase, 3 for three-phase. Defaults to 1.",
    )


class NecVoltageDropResult(BaseModel):
    """
    Output of the NEC voltage drop calculation handler.

    Serialized by the Voice AI and read back to the technician.
    """

    voltage_drop: float = Field(
        ...,
        description="Calculated voltage drop in volts (e.g., 3.21).",
    )
    voltage_drop_pct: float = Field(
        ...,
        description="Voltage drop as a percentage of source voltage (e.g., 2.68).",
    )
    is_compliant: bool = Field(
        ...,
        description=(
            "True if voltage_drop_pct ≤ 3.0% (NEC 210.19 informational note: "
            "recommended max 3% for branch circuits)."
        ),
    )


class NecConduitFillArgs(BaseModel):
    """
    Parsed intent arguments from Ollama for NEC conduit fill calculations.

    NEC Chapter 9 Table 1 rules:
      - 1 conductor  → 53% max fill
      - 2 conductors → 31% max fill
      - 3+ conductors → 40% max fill (most common residential/commercial case)
    """

    conduit_trade_size: str = Field(
        ...,
        description="Conduit trade size string (e.g., '3/4', '1', '1-1/4', '1-1/2', '2').",
    )
    conduit_type: str = Field(
        default="EMT",
        description="Conduit type: 'EMT', 'RMC', 'IMC', 'PVC40', 'PVC80'. Defaults to EMT.",
    )
    wire_gauge: str = Field(
        ...,
        description="AWG wire gauge for the conductors (e.g., '12', '10', '8').",
    )
    num_conductors: int = Field(
        ...,
        ge=1,
        description="Number of current-carrying conductors in the conduit.",
    )


class NecConduitFillResult(BaseModel):
    """
    Output of the NEC conduit fill calculation handler.

    Serialized by the Voice AI and read back to the technician.
    """

    total_fill_sq_in: float = Field(
        ...,
        description="Total cross-sectional area of all conductors in square inches.",
    )
    conduit_area_sq_in: float = Field(
        ...,
        description="Internal cross-sectional area of the conduit in square inches.",
    )
    fill_pct: float = Field(
        ...,
        description="Actual fill percentage (total_fill / conduit_area × 100).",
    )
    max_fill_pct: float = Field(
        ...,
        description="Maximum allowed fill percentage per NEC Chapter 9 Table 1.",
    )
    is_compliant: bool = Field(
        ...,
        description="True if fill_pct ≤ max_fill_pct.",
    )
