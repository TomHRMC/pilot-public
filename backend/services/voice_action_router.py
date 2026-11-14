"""
Voice Action Execution Router

Routes parsed intents from Ollama to business logic handlers.
Implements Gap #17 - Intent-Based Action Execution.

Reference:
- gap-17-voice-action-execution-remediation-plan.md (private design doc, not in this snapshot)
- dev-docs/implementation-prompts/phase-1-4-prompts/task-10-prompt.md
"""

import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlmodel import Session, select

# Import existing business logic implementations
from api.routes.customers import _create_customer_impl
from api.routes.jobs import (
    _create_job_expense_impl,
    _create_job_impl,
    _create_job_time_entry_impl,
)
from api.routes.quotes import _create_quote_impl
from api.schemas.quotes import QuoteCreate
from api.schemas.schemas import (
    CustomerCreate,
    JobCreate,
    JobExpenseCreate,
    JobTimeEntryCreate,
)
from api.schemas.voice import (
    ContextWindowSchema,
    NecConduitFillArgs,
    NecConduitFillResult,
    NecVoltageDropArgs,
    NecVoltageDropResult,
)
from app.models.ai import ConversationSession
from app.models.crm import Customer, CustomerType, Site
from app.models.fulfillment import Job, JobExpenseCategory
from app.models.help import HelpChatMessage, HelpChatSession
from app.models.quoting import Quote, QuoteLine
from core.auth import AuthenticatedUser
from core.test_context import TestUserContext
from services import nec_service

# Re-export NEC tables for backward compatibility
# (existing tests import these directly from voice_action_router)
from services.nec_service import (
    _AWG_CIRCULAR_MILS,
    _AWG_WIRE_AREA_SQ_IN,
    _CONDUIT_AREA_SQ_IN,
    _normalize_gauge,
)

logger = logging.getLogger(__name__)


# ==================== MAIN ROUTER ====================


async def execute_action(
    intent_type: str,
    entities: dict,
    current_user: AuthenticatedUser | TestUserContext,
    db: Session,
    session: ConversationSession,
) -> dict[str, Any]:
    """
    Route parsed intent to appropriate business logic handler.

    B12/A67 extension: After the handler produces its result dict, the
    `message` field is replaced by a tone-aware string from
    voice_persona_renderer.render(). The original inline message is preserved
    as `data.fallback_message` and is returned as-is when Ollama is unavailable.

    Args:
        intent_type: The intent detected by Ollama (e.g., "create_quote")
        entities: Extracted entities from user utterance
        current_user: Authenticated user or test context
        db: Database session
        session: Active conversation session

    Returns:
        Structured response dict for mobile app rendering

    Example Response:
        {
            "action": "create_quote",
            "success": True,
            "message": "Created Quote #123 for Mike's Diner",
            "data": {"quote_id": "uuid", "customer_name": "Mike's Diner"},
            "next_prompts": ["Add line items", "Send to customer"]
        }
    """
    # Validate intent exists
    if not intent_type or intent_type not in INTENT_HANDLERS:
        return _handle_unknown_intent(intent_type)

    # Execute handler
    handler = INTENT_HANDLERS[intent_type]
    try:
        logger.info(f"Executing voice action: {intent_type} with entities: {entities}")
        result = await handler(entities, current_user, db, session)
        logger.info(f"Voice action {intent_type} completed successfully")

        # B12/A67: Render tone-aware message via voice_persona_renderer.
        # Original inline message is stored as fallback_message so the renderer
        # can return it unchanged when Ollama is unavailable.
        result = _apply_tone_aware_message(result, intent_type, current_user, db)

        return result
    except Exception as e:
        logger.error(f"Voice action {intent_type} failed: {e!s}", exc_info=True)
        return _handle_execution_error(intent_type, str(e))


def _apply_tone_aware_message(
    result: dict[str, Any],
    intent_type: str,
    current_user: AuthenticatedUser | TestUserContext,
    db: Session,
) -> dict[str, Any]:
    """
    B12/A67: Replace the handler's inline message with a tone-aware string.

    Builds a renderer payload from the result dict and calls
    voice_persona_renderer.render(). Falls back to the original inline
    message if the renderer raises or returns empty.

    Args:
        result:       The raw result dict from an intent handler.
        intent_type:  The intent key (e.g., "create_quote").
        current_user: Authenticated user or test context.
        db:           Active SQLModel session.

    Returns:
        The result dict with `message` replaced by the tone-aware string.
    """
    try:
        from services.voice_persona_renderer import render as render_tone_message

        original_message = result.get("message", "")
        data = dict(result.get("data") or {})
        # Preserve original message as fallback for renderer error path
        data["fallback_message"] = original_message
        # Add a human-readable data summary for the template
        data["data_summary"] = ", ".join(
            f"{k}={v}" for k, v in data.items() if k != "fallback_message"
        )

        payload = {
            "intent": intent_type,
            "outcome": "success" if result.get("success") else "error",
            "data": data,
        }

        tenant_id = getattr(current_user, "tenant_id", None)
        user_id = getattr(current_user, "id", None) or getattr(
            current_user, "user_id", None
        )

        if tenant_id and user_id:
            tone_message = render_tone_message(
                payload=payload,
                user_id=user_id,
                db=db,
                tenant_id=tenant_id,
            )
            if tone_message:
                result = dict(result)
                result["message"] = tone_message

    except Exception as exc:
        # Renderer errors are non-fatal — always return original result
        logger.warning(
            "voice_persona_renderer failed for intent '%s': %s; using inline message",
            intent_type,
            exc,
        )

    return result


# ==================== HANDLER 1: CREATE QUOTE ====================


async def create_quote_via_voice(
    entities: dict,
    current_user: AuthenticatedUser | TestUserContext,
    db: Session,
    session: ConversationSession,
) -> dict:
    """
    Handle: "Create a quote for Mike's Diner"

    Entities:
        - customer_name: "Mike's Diner"

    Returns:
        Success response with quote_id and context window updated
    """
    customer_name = entities.get("customer_name")

    if not customer_name:
        return {
            "action": "create_quote",
            "success": False,
            "error": "Missing customer name",
            "message": "Which customer is this quote for?",
            "next_prompts": ["Try again with customer name"],
        }

    # Find or create customer (fuzzy match)
    customer = db.exec(
        select(Customer)
        .where(Customer.tenant_id == current_user.tenant_id)
        .where(Customer.display_name.ilike(f"%{customer_name}%"))
    ).first()

    if not customer:
        # Create customer on the fly
        customer = Customer(
            tenant_id=current_user.tenant_id,
            display_name=customer_name,
            type=CustomerType.company,
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)
        logger.info(f"Created new customer via voice: {customer.display_name}")

    # Find or create default site
    site = db.exec(select(Site).where(Site.customer_id == customer.id)).first()

    if not site:
        site = Site(
            tenant_id=current_user.tenant_id,
            customer_id=customer.id,
            name=f"{customer.display_name} - Main Site",
        )
        db.add(site)
        db.commit()
        db.refresh(site)
        logger.info(f"Created default site for customer: {customer.display_name}")

    # Create quote using existing business logic
    quote_in = QuoteCreate(
        customer_id=customer.id,
        site_id=site.id,
        currency="USD",
    )
    quote = _create_quote_impl(quote_in, db, current_user)

    # Update context window — preserve LOTO safety fields via ContextWindowSchema
    ctx = ContextWindowSchema.from_jsonb(session.context_window_json)
    ctx.active_quote_id = str(quote.id)
    ctx.active_customer_id = str(customer.id)
    ctx.active_site_id = str(site.id)
    ctx.last_action = "create_quote"
    ctx.timestamp = datetime.now(UTC).isoformat()
    # Reset LOTO when a new quote/job context is established
    ctx.safety_loto_verified = False
    session.context_window_json = ctx.to_jsonb()
    db.add(session)
    db.commit()

    quote_id_short = str(quote.id)[:8]
    return {
        "action": "create_quote",
        "success": True,
        "message": f"Created Quote #{quote_id_short} for {customer.display_name}. What would you like to add?",
        "data": {
            "quote_id": str(quote.id),
            "customer_id": str(customer.id),
            "customer_name": customer.display_name,
            "total_cents": quote.total_cents,
        },
        "next_prompts": [
            "Add line items",
            "Send to customer",
            "Cancel quote",
        ],
    }


# ==================== HANDLER 2: ADD QUOTE LINE ====================


async def add_line_via_voice(
    entities: dict,
    current_user: AuthenticatedUser | TestUserContext,
    db: Session,
    session: ConversationSession,
) -> dict:
    """
    Handle: "Add 10 feet of 12-gauge wire"

    Entities:
        - quantity: 10
        - unit: "feet"
        - item: "12-gauge wire"

    Requires active quote in context window.
    """
    # Resolve active quote from context
    context = session.context_window_json or {}
    active_quote_id = context.get("active_quote_id")

    if not active_quote_id:
        return {
            "action": "add_quote_line",
            "success": False,
            "error": "No active quote",
            "message": "I need a quote first. Say 'Create quote for [customer]'.",
            "next_prompts": ["Create new quote"],
        }

    # Verify quote exists and belongs to tenant
    quote = db.exec(
        select(Quote)
        .where(Quote.id == UUID(active_quote_id))
        .where(Quote.tenant_id == current_user.tenant_id)
    ).first()

    if not quote:
        return {
            "action": "add_quote_line",
            "success": False,
            "error": "Quote not found",
            "message": "That quote doesn't exist anymore. Want to create a new one?",
            "next_prompts": ["Create new quote"],
        }

    # Extract entities
    description = entities.get("item", entities.get("description", "Unknown item"))
    quantity = entities.get("quantity", 1)
    unit = entities.get("unit", "ea")

    # Convert quantity to Decimal if it's a number
    try:
        quantity = Decimal(str(quantity))
    except (ValueError, TypeError):
        quantity = Decimal("1.0")

    # Get next position
    max_position = (
        db.exec(
            select(QuoteLine.position)
            .where(QuoteLine.quote_id == quote.id)
            .order_by(QuoteLine.position.desc())
        ).first()
        or 0
    )

    # Find default line type
    from app.models.quoting import QcoLineType

    line_type = db.exec(
        select(QcoLineType)
        .where(
            (QcoLineType.tenant_id == current_user.tenant_id)
            | (QcoLineType.tenant_id == None)
        )
        .where(QcoLineType.is_default == True)
    ).first()

    if not line_type:
        # Fallback to first available
        line_type = db.exec(select(QcoLineType)).first()

    if not line_type:
        return {
            "action": "add_quote_line",
            "success": False,
            "error": "No line type configured",
            "message": "System error: No quote line types configured.",
        }

    # Create quote line directly (no _impl function exists yet)
    quote_line = QuoteLine(
        tenant_id=quote.tenant_id,
        quote_id=quote.id,
        position=max_position + 1,
        qco_line_type_id=line_type.id,
        description=description,
        quantity=quantity,
        unit=unit,
        unit_price_cents=0,  # MVP: Manual pricing later
        line_total_cents=0,
    )

    db.add(quote_line)
    db.commit()
    db.refresh(quote_line)

    return {
        "action": "add_quote_line",
        "success": True,
        "message": f"Added {quantity} {unit} of {description}. Anything else?",
        "data": {
            "quote_line_id": str(quote_line.id),
            "quote_id": str(quote.id),
            "description": description,
            "quantity": float(quantity),
            "unit": unit,
        },
        "next_prompts": [
            "Add more items",
            "Set price",
            "Send quote",
        ],
    }


# ==================== HANDLER 3: QUERY JOB PROFIT ====================


async def get_job_profitability(
    entities: dict,
    current_user: AuthenticatedUser | TestUserContext,
    db: Session,
    session: ConversationSession,
) -> dict:
    """
    Handle: "What's the profit on the Smith job?"

    Entities:
        - job_reference: "Smith job" or job_id

    Returns job profitability data from cached fields.
    """
    job_reference = entities.get("job_reference") or entities.get("customer_name")

    if not job_reference:
        # Use active job from context
        context = session.context_window_json or {}
        active_job_id = context.get("active_job_id")

        if not active_job_id:
            return {
                "action": "query_job_profit",
                "success": False,
                "error": "No job specified",
                "message": "Which job are you asking about?",
                "next_prompts": ["Show active jobs"],
            }

        job = db.exec(
            select(Job)
            .where(Job.id == UUID(active_job_id))
            .where(Job.tenant_id == current_user.tenant_id)
        ).first()
    else:
        # Find job by customer name or job ID
        job = db.exec(
            select(Job)
            .join(Customer, Job.customer_id == Customer.id)
            .where(Job.tenant_id == current_user.tenant_id)
            .where(Customer.display_name.ilike(f"%{job_reference}%"))
        ).first()

    if not job:
        return {
            "action": "query_job_profit",
            "success": False,
            "error": "Job not found",
            "message": f"I couldn't find a job for '{job_reference}'.",
            "next_prompts": ["Show all jobs"],
        }

    # Get customer name — FIND-132: tenant-scoped query
    customer = db.exec(
        select(Customer).where(
            Customer.id == job.customer_id,
            Customer.tenant_id == current_user.tenant_id,
        )
    ).first()
    customer_name = customer.display_name if customer else "Unknown"

    # Calculate profit data from cached fields
    total_cost = job.actual_labor_cost_cents + job.actual_material_cost_cents
    profit = job.actual_profit_cents

    return {
        "action": "query_job_profit",
        "success": True,
        "message": f"The {customer_name} job has ${profit / 100:.2f} profit so far.",
        "data": {
            "job_id": str(job.id),
            "customer_name": customer_name,
            "labor_cost_cents": job.actual_labor_cost_cents,
            "material_cost_cents": job.actual_material_cost_cents,
            "total_cost_cents": total_cost,
            "profit_cents": profit,
            "profit_dollars": f"${profit / 100:.2f}",
        },
        "next_prompts": [
            "Show job details",
            "Add expense",
            "Log time",
        ],
    }


# ==================== NEC WIRE GAUGE TABLES ====================
# Circular mils (CM) per AWG gauge — values from NFPA 70 (NEC), Chapter 9 Table 8.
# NEC and NFPA 70 are registered trademarks of the National Fire Protection Association.
# Used in the voltage drop formula: V_D = (2 × K × I × D) / CM
# K = 12.9 for copper (DC constant), I = amperage, D = one-way distance.

_AWG_CIRCULAR_MILS: dict[str, float] = {
    "14": 4110.0,
    "12": 6530.0,
    "10": 10380.0,
    "8": 16510.0,
    "6": 26240.0,
    "4": 41740.0,
    "3": 52620.0,
    "2": 66360.0,
    "1": 83690.0,
    "1/0": 105600.0,
    "2/0": 133100.0,
    "3/0": 167800.0,
    "4/0": 211600.0,
    "250": 250000.0,
    "300": 300000.0,
    "350": 350000.0,
    "400": 400000.0,
    "500": 500000.0,
}

# Wire cross-sectional areas in square inches (for conduit fill calculations).
# Source: NEC Chapter 9 Table 5 — THHN/THWN-2 conductor outer diameter.

_AWG_WIRE_AREA_SQ_IN: dict[str, float] = {
    "14": 0.0097,
    "12": 0.0133,
    "10": 0.0211,
    "8": 0.0366,
    "6": 0.0507,
    "4": 0.0824,
    "3": 0.0973,
    "2": 0.1158,
    "1": 0.1562,
    "1/0": 0.1855,
    "2/0": 0.2223,
    "3/0": 0.2660,
    "4/0": 0.3197,
    "250": 0.3904,
    "300": 0.4608,
    "350": 0.5281,
    "400": 0.5958,
    "500": 0.7297,
}

# EMT conduit internal cross-sectional areas in square inches.
# Source: NEC Chapter 9 Table 4 — Electrical Metallic Tubing (EMT).

_CONDUIT_AREA_SQ_IN: dict[str, dict[str, float]] = {
    "EMT": {
        "1/2": 0.304,
        "3/4": 0.533,
        "1": 0.864,
        "1-1/4": 1.496,
        "1-1/2": 2.036,
        "2": 3.356,
        "2-1/2": 5.858,
        "3": 8.846,
        "3-1/2": 11.545,
        "4": 14.753,
    },
    "RMC": {
        "1/2": 0.314,
        "3/4": 0.549,
        "1": 0.887,
        "1-1/4": 1.526,
        "1-1/2": 2.071,
        "2": 3.408,
        "2-1/2": 5.452,
        "3": 8.688,
        "3-1/2": 11.663,
        "4": 14.854,
    },
    "PVC40": {
        "1/2": 0.285,
        "3/4": 0.508,
        "1": 0.832,
        "1-1/4": 1.453,
        "1-1/2": 1.986,
        "2": 3.291,
        "2-1/2": 4.695,
        "3": 7.268,
        "3-1/2": 9.737,
        "4": 12.554,
    },
}


def _normalize_gauge(wire_gauge: str) -> str:
    """
    Normalize wire gauge input to match the lookup table keys.
    Handles inputs like "12 AWG", "12awg", "12 gauge", "#12", "12".
    """
    import re

    gauge = wire_gauge.strip().upper()
    # Strip common suffixes
    gauge = re.sub(r"\s*(AWG|GAUGE|GA\.?|#)", "", gauge).strip()
    return gauge


# ==================== HANDLER 4: CALCULATE VOLTAGE DROP ====================


async def calculate_nec_voltage_drop(
    entities: dict,
    current_user: AuthenticatedUser | TestUserContext,
    db: Session,
    session: ConversationSession,
) -> dict:
    """
    Handle: "Calculate voltage drop for 20 amps on 100 feet of 12 AWG"

    NEC single-phase formula:  V_D = (2 × K × I × D) / CM
    NEC three-phase formula:   V_D = (1.732 × K × I × D) / CM
    where K=12.9 (copper), I=amperage, D=one-way distance, CM=circular mils.

    Compliance threshold: ≤ 3% drop recommended (NEC 210.19 informational note).

    Entities:
        - amperage: 20 (amps)
        - distance_feet / distance: 100 (feet)
        - wire_gauge: "12 AWG"
        - voltage: 120 (default)
        - phase: 1 (default)

    Task 1-E-3: Full NEC implementation.
    MOB-B0: Now delegates pure formula to nec_service.calculate().
    Session context update logic remains here (voice-specific).
    """
    # --- Parse & validate inputs using existing Pydantic schema ---
    try:
        args = NecVoltageDropArgs(
            amperage=float(entities.get("amperage", 0)),
            distance_feet=float(
                entities.get("distance_feet") or entities.get("distance", 0)
            ),
            wire_gauge=str(
                entities.get("wire_gauge", entities.get("wire", ""))
            ).strip(),
            voltage=float(entities.get("voltage", 120.0)),
            phase=int(entities.get("phase", 1)),
        )
    except (ValueError, TypeError) as e:
        return {
            "action": "calculate_voltage_drop",
            "success": False,
            "error": f"Invalid input: {e}",
            "message": "Please provide amperage, distance in feet, and wire gauge (e.g., '20 amps, 100 feet, 12 AWG').",
            "next_prompts": ["Try again with wire specs"],
        }

    if not args.wire_gauge:
        return {
            "action": "calculate_voltage_drop",
            "success": False,
            "error": "Missing wire gauge",
            "message": "What AWG wire gauge are you using?",
            "next_prompts": ["Specify wire gauge"],
        }

    # --- Delegate pure formula to nec_service ---
    try:
        calc_result = nec_service.calculate(
            "voltage_drop",
            {
                "amperage": args.amperage,
                "distance_feet": args.distance_feet,
                "wire_gauge": args.wire_gauge,
                "voltage": args.voltage,
                "phase": args.phase,
            },
        )
    except ValueError as e:
        return {
            "action": "calculate_voltage_drop",
            "success": False,
            "error": str(e),
            "message": str(e),
            "next_prompts": ["Try a standard AWG gauge"],
        }

    result = NecVoltageDropResult(
        voltage_drop=calc_result.details["voltage_drop"],
        voltage_drop_pct=calc_result.details["voltage_drop_pct"],
        is_compliant=calc_result.is_compliant,
    )
    normalized_gauge = calc_result.details["wire_gauge_normalized"]

    # --- Session context update — voice-specific, stays here ---
    ctx = ContextWindowSchema.from_jsonb(session.context_window_json)
    ctx.current_technical_context.update(
        {
            "last_nec_calculation": "voltage_drop",
            "wire_gauge": args.wire_gauge,
            "wire_gauge_normalized": normalized_gauge,
            "amperage": args.amperage,
            "distance_feet": args.distance_feet,
            "voltage": args.voltage,
            "phase": args.phase,
            "voltage_drop_volts": result.voltage_drop,
            "voltage_drop_pct": result.voltage_drop_pct,
            "voltage_drop_compliant": result.is_compliant,
        }
    )
    ctx.last_action = "calculate_voltage_drop"
    ctx.timestamp = datetime.now(UTC).isoformat()
    session.context_window_json = ctx.to_jsonb()
    db.add(session)
    db.commit()

    compliance_msg = (
        "✓ Compliant" if result.is_compliant else "⚠ Exceeds 3% NEC recommendation"
    )
    phase_label = "single-phase" if args.phase == 1 else "three-phase"
    message = (
        f"Voltage drop for {args.wire_gauge} at {args.distance_feet} ft "
        f"({args.amperage}A, {args.voltage}V {phase_label}): "
        f"{result.voltage_drop:.2f}V ({result.voltage_drop_pct:.2f}%). {compliance_msg}."
    )

    return {
        "action": "calculate_voltage_drop",
        "success": True,
        "message": message,
        "data": result.model_dump(),
        "next_prompts": [
            "Calculate conduit fill",
            "Add to quote",
            "Try a larger gauge",
        ],
    }


# ==================== HANDLER 5: CALCULATE CONDUIT FILL ====================


async def calculate_conduit_fill(
    entities: dict,
    current_user: AuthenticatedUser | TestUserContext,
    db: Session,
    session: ConversationSession,
) -> dict:
    """
    Handle: "Will 6 conductors of 12 AWG fit in 3/4 inch EMT?"

    NEC Chapter 9 Table 1 fill rules:
        1 conductor  → 53% max
        2 conductors → 31% max
        3+ conductors → 40% max  (most common residential / commercial case)

    Entities:
        - conduit_trade_size: "3/4" (inches)
        - conduit_type: "EMT" (default)
        - wire_gauge: "12 AWG"
        - num_conductors: 6

    Task 1-E-3: Full NEC Chapter 9 implementation.
    On success, updates current_technical_context in the active ConversationSession.
    """
    # --- Parse & validate inputs using existing Pydantic schema ---
    try:
        args = NecConduitFillArgs(
            conduit_trade_size=str(
                entities.get("conduit_trade_size", entities.get("conduit_size", ""))
            ).strip(),
            conduit_type=str(entities.get("conduit_type", "EMT")).strip().upper(),
            wire_gauge=str(
                entities.get("wire_gauge", entities.get("wire", ""))
            ).strip(),
            num_conductors=int(
                entities.get("num_conductors", entities.get("conductors", 0))
            ),
        )
    except (ValueError, TypeError) as e:
        return {
            "action": "calculate_conduit_fill",
            "success": False,
            "error": f"Invalid input: {e}",
            "message": "Please specify conduit size, type, wire gauge, and number of conductors.",
            "next_prompts": ["Try again with conduit specs"],
        }

    if not args.conduit_trade_size:
        return {
            "action": "calculate_conduit_fill",
            "success": False,
            "error": "Missing conduit size",
            "message": "What conduit trade size are you using (e.g., 3/4 inch EMT)?",
            "next_prompts": ["Specify conduit size"],
        }

    if not args.wire_gauge:
        return {
            "action": "calculate_conduit_fill",
            "success": False,
            "error": "Missing wire gauge",
            "message": "What AWG wire gauge are you pulling?",
            "next_prompts": ["Specify wire gauge"],
        }

    # --- Delegate pure formula to nec_service ---
    try:
        calc_result = nec_service.calculate(
            "conduit_fill",
            {
                "conduit_trade_size": args.conduit_trade_size,
                "conduit_type": args.conduit_type,
                "wire_gauge": args.wire_gauge,
                "num_conductors": args.num_conductors,
            },
        )
    except ValueError as e:
        return {
            "action": "calculate_conduit_fill",
            "success": False,
            "error": str(e),
            "message": str(e),
            "next_prompts": ["Try a standard conduit size"],
        }

    result = NecConduitFillResult(
        total_fill_sq_in=calc_result.details["total_fill_sq_in"],
        conduit_area_sq_in=calc_result.details["conduit_area_sq_in"],
        fill_pct=calc_result.details["fill_pct"],
        max_fill_pct=calc_result.details["max_fill_pct"],
        is_compliant=calc_result.is_compliant,
    )
    normalized_gauge = calc_result.details["wire_gauge_normalized"]
    conduit_type_key = calc_result.details["conduit_type"]

    # --- Session context update — voice-specific, stays here ---
    ctx = ContextWindowSchema.from_jsonb(session.context_window_json)
    ctx.current_technical_context.update(
        {
            "last_nec_calculation": "conduit_fill",
            "wire_gauge": args.wire_gauge,
            "wire_gauge_normalized": normalized_gauge,
            "conduit_trade_size": args.conduit_trade_size,
            "conduit_type": conduit_type_key,
            "num_conductors": args.num_conductors,
            "fill_pct": result.fill_pct,
            "max_fill_pct": result.max_fill_pct,
            "conduit_fill_compliant": result.is_compliant,
        }
    )
    ctx.last_action = "calculate_conduit_fill"
    ctx.timestamp = datetime.now(UTC).isoformat()
    session.context_window_json = ctx.to_jsonb()
    db.add(session)
    db.commit()

    compliance_msg = (
        "✓ Compliant"
        if result.is_compliant
        else f"⚠ Exceeds {result.max_fill_pct:.0f}% NEC Chapter 9 limit"
    )
    message = (
        f"{args.num_conductors} conductors of {args.wire_gauge} in "
        f'{args.conduit_trade_size}" {conduit_type_key}: '
        f"{result.fill_pct:.2f}% fill (max {result.max_fill_pct:.0f}%). {compliance_msg}."
    )

    return {
        "action": "calculate_conduit_fill",
        "success": True,
        "message": message,
        "data": result.model_dump(),
        "next_prompts": [
            "Calculate voltage drop",
            "Try a larger conduit",
            "Add to quote",
        ],
    }


# ==================== HANDLER 6: NAVIGATE ====================


async def return_navigation_command(
    entities: dict,
    current_user: AuthenticatedUser | TestUserContext,
    db: Session,
    session: ConversationSession,
) -> dict:
    """
    Handle: "Show me active jobs" / "Go to quotes"

    Entities:
        - screen: "jobs", "quotes", "customers", etc.
        - filter: "active", "recent", etc.

    Returns navigation command for mobile app.
    """
    screen = entities.get("screen", "home")
    filter_type = entities.get("filter", "all")

    # Map common voice phrases to screens
    screen_mapping = {
        "jobs": "jobs",
        "quotes": "quotes",
        "customers": "customers",
        "home": "home",
        "dashboard": "dashboard",
        "settings": "settings",
    }

    target_screen = screen_mapping.get(screen.lower(), screen)

    return {
        "action": "navigate",
        "success": True,
        "message": f"Showing {filter_type} {target_screen}.",
        "data": {
            "screen": target_screen,
            "filter": filter_type,
            "navigation_command": True,
        },
        "next_prompts": [
            "Create new item",
            "Search",
        ],
    }


# ==================== HANDLER 6: CREATE CUSTOMER ====================


async def create_customer_via_voice(
    entities: dict,
    current_user: AuthenticatedUser | TestUserContext,
    db: Session,
    session: ConversationSession,
) -> dict:
    """
    Handle: "Create customer John Smith at 123 Main Street"

    Entities:
        - name: "John Smith"
        - first_name: "John"
        - last_name: "Smith"
        - email: "john@example.com"
        - phone: "555-1234"
        - type: "person" or "company"
    """
    name = entities.get("name") or entities.get("customer_name")

    if not name:
        return {
            "action": "create_customer",
            "success": False,
            "error": "Missing customer name",
            "message": "What's the customer's name?",
        }

    # Determine type
    customer_type = entities.get("type", "person")
    if customer_type not in ["person", "company"]:
        customer_type = "person"

    customer_in = CustomerCreate(
        type=customer_type,
        display_name=name,
        first_name=entities.get("first_name"),
        last_name=entities.get("last_name"),
        company_name=entities.get("company_name")
        if customer_type == "company"
        else None,
        email=entities.get("email"),
        mobile_phone=entities.get("phone"),
    )

    try:
        customer = _create_customer_impl(customer_in, db, current_user)
    except Exception as e:
        return {
            "action": "create_customer",
            "success": False,
            "error": str(e),
            "message": f"Couldn't create customer: {e!s}",
        }

    # Update context — preserve LOTO safety fields via ContextWindowSchema
    ctx = ContextWindowSchema.from_jsonb(session.context_window_json)
    ctx.active_customer_id = str(customer.id)
    ctx.last_action = "create_customer"
    ctx.timestamp = datetime.now(UTC).isoformat()
    # Reset LOTO when a new customer context is established
    ctx.safety_loto_verified = False
    session.context_window_json = ctx.to_jsonb()
    db.add(session)
    db.commit()

    return {
        "action": "create_customer",
        "success": True,
        "message": f"Created customer {customer.display_name}.",
        "data": {
            "customer_id": str(customer.id),
            "display_name": customer.display_name,
            "email": customer.email,
        },
        "next_prompts": ["Create quote", "Add contact info"],
    }


# ==================== HANDLER 7: CREATE JOB ====================


async def create_job_via_voice(
    entities: dict,
    current_user: AuthenticatedUser | TestUserContext,
    db: Session,
    session: ConversationSession,
) -> dict:
    """
    Handle: "Create a service call job for Site 42"

    Entities:
        - customer_name: "ABC Electric"
        - site_name: "Site 42"
        - job_type: "service call"

    Can use active customer from context.
    """
    customer_name = entities.get("customer_name")

    # Try to get customer from context if not specified
    context = session.context_window_json or {}
    if not customer_name:
        active_customer_id = context.get("active_customer_id")
        if active_customer_id:
            # FIND-132: tenant-scoped query — context_window_json is user-controlled input
            customer = db.exec(
                select(Customer).where(
                    Customer.id == UUID(active_customer_id),
                    Customer.tenant_id == current_user.tenant_id,
                )
            ).first()
            if customer:
                customer_name = customer.display_name
            else:
                active_customer_id = None

    if not customer_name and not active_customer_id:
        return {
            "action": "create_job",
            "success": False,
            "error": "Missing customer",
            "message": "Which customer is this job for?",
        }

    # Find customer
    if not active_customer_id:
        customer = db.exec(
            select(Customer)
            .where(Customer.tenant_id == current_user.tenant_id)
            .where(Customer.display_name.ilike(f"%{customer_name}%"))
        ).first()
    else:
        # FIND-132: tenant-scoped query
        customer = db.exec(
            select(Customer).where(
                Customer.id == UUID(active_customer_id),
                Customer.tenant_id == current_user.tenant_id,
            )
        ).first()

    if not customer:
        return {
            "action": "create_job",
            "success": False,
            "error": "Customer not found",
            "message": f"I couldn't find customer '{customer_name}'.",
        }

    # Find or create default site
    site = db.exec(select(Site).where(Site.customer_id == customer.id)).first()

    if not site:
        site = Site(
            tenant_id=current_user.tenant_id,
            customer_id=customer.id,
            name=f"{customer.display_name} - Main Site",
        )
        db.add(site)
        db.commit()
        db.refresh(site)

    # Create job
    job_in = JobCreate(
        customer_id=customer.id,
        site_id=site.id,
        quote_id=context.get("active_quote_id"),  # Link to quote if in context
    )

    try:
        job = _create_job_impl(job_in, db, current_user)
    except Exception as e:
        return {
            "action": "create_job",
            "success": False,
            "error": str(e),
            "message": f"Couldn't create job: {e!s}",
        }

    # Update context — preserve LOTO safety fields via ContextWindowSchema
    ctx = ContextWindowSchema.from_jsonb(session.context_window_json)
    ctx.active_job_id = str(job.id)
    ctx.active_customer_id = str(customer.id)
    ctx.last_action = "create_job"
    ctx.timestamp = datetime.now(UTC).isoformat()
    # Reset LOTO when a new job becomes active — technician must re-confirm on-site
    ctx.safety_loto_verified = False
    session.context_window_json = ctx.to_jsonb()
    db.add(session)
    db.commit()

    job_id_short = str(job.id)[:8]
    return {
        "action": "create_job",
        "success": True,
        "message": f"Created Job #{job_id_short} for {customer.display_name}.",
        "data": {
            "job_id": str(job.id),
            "customer_id": str(customer.id),
            "customer_name": customer.display_name,
        },
        "next_prompts": [
            "Log time",
            "Add expense",
            "Show job details",
        ],
    }


# ==================== HANDLER 8a: CONFIRM LOTO (B20/A89) ====================


async def clock_in_via_voice(
    entities: dict,
    current_user: AuthenticatedUser | TestUserContext,
    db: Session,
    session: ConversationSession,
) -> dict:
    """
    Handle: "Clock in on the Johnson job" / "Clock in"

    Entities:
        - job_reference: "Johnson job" (optional; uses active_job_id if not provided)

    Behavior:
    1. Resolve job from context (active_job_id) or voice entity (job_reference)
    2. Resolve labor rate from LaborRateVersion catalog (tenant + skill_level_code)
    3. Create open JobTimeEntry with started_at=now(), ended_at=NULL, hourly_rate_cents=resolved_rate
    4. Return success response with confirmation message and next prompts

    B20/A90: Hands-free time tracking — real-time presence logging.
    """
    context = session.context_window_json or {}
    job_reference = entities.get("job_reference")

    # Find job
    if not job_reference:
        active_job_id = context.get("active_job_id")
        if not active_job_id:
            return {
                "action": "clock_in",
                "success": False,
                "error": "No job specified",
                "message": "Which job are you clocking in on? Please specify a job or set an active job first.",
            }
        job = db.exec(
            select(Job)
            .where(Job.id == UUID(active_job_id))
            .where(Job.tenant_id == current_user.tenant_id)
        ).first()
    else:
        # Find by customer name
        job = db.exec(
            select(Job)
            .join(Customer, Job.customer_id == Customer.id)
            .where(Job.tenant_id == current_user.tenant_id)
            .where(Customer.display_name.ilike(f"%{job_reference}%"))
        ).first()

    if not job or job.tenant_id != current_user.tenant_id:
        return {
            "action": "clock_in",
            "success": False,
            "error": "Job not found",
            "message": "I couldn't find that job.",
        }

    # Resolve labor rate from LaborRateVersion catalog
    # Get user's skill level
    from app.models.auth import TenantUser
    from app.models.catalog import LaborRateVersion

    tenant_user = db.exec(
        select(TenantUser)
        .where(TenantUser.tenant_id == current_user.tenant_id)
        .where(TenantUser.user_id == current_user.id)
    ).first()

    skill_level_code = tenant_user.skill_level_code if tenant_user else None
    if not skill_level_code:
        # Fallback to default_labor_rate_cents from settings
        from services.setting_resolver import get_effective_setting

        default_rate, _ = get_effective_setting(
            db, current_user.tenant_id, "default_labor_rate_cents", fallback=5000
        )
        hourly_rate_cents = int(default_rate) if default_rate else 5000
    else:
        # Query labor rate for this tenant + skill level at current time
        rate_record = db.exec(
            select(LaborRateVersion).where(
                LaborRateVersion.tenant_id == current_user.tenant_id,
                LaborRateVersion.skill_level_code == skill_level_code,
                # valid_period @> now() — psycopg2/sqlalchemy range overlap check
            )
        ).first()

        if rate_record:
            # Compute burdened rate: hourly_rate_cents * (1 + burden_pct)
            hourly_rate_cents = int(
                rate_record.hourly_rate_cents * (1 + rate_record.burden_pct)
            )
        else:
            # Fallback to default_labor_rate_cents
            from services.setting_resolver import get_effective_setting

            default_rate, _ = get_effective_setting(
                db, current_user.tenant_id, "default_labor_rate_cents", fallback=5000
            )
            hourly_rate_cents = int(default_rate) if default_rate else 5000

    # Create open JobTimeEntry (ended_at=NULL)
    now = datetime.now(UTC)
    from app.models.fulfillment import JobTimeEntry

    entry = JobTimeEntry(
        tenant_id=current_user.tenant_id,
        job_id=job.id,
        user_id=current_user.id,
        started_at=now,
        ended_at=None,  # Open entry
        hours=None,
        hourly_rate_cents=hourly_rate_cents,
        total_cost_cents=0,
        created_by=current_user.id,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    # Fetch customer for response message
    customer = db.exec(
        select(Customer).where(
            Customer.id == job.customer_id,
            Customer.tenant_id == current_user.tenant_id,
        )
    ).first()
    customer_name = customer.display_name if customer else "Unknown"

    return {
        "action": "clock_in",
        "success": True,
        "message": f"Clocked in on {customer_name} job at {now.strftime('%I:%M %p')}.",
        "data": {
            "time_entry_id": str(entry.id),
            "job_id": str(job.id),
            "started_at": now.isoformat(),
            "hourly_rate_cents": hourly_rate_cents,
        },
        "next_prompts": [
            "Log time",
            "Confirm LOTO",
            "Add expense",
            "Clock out",
        ],
    }


async def clock_out_via_voice(
    entities: dict,
    current_user: AuthenticatedUser | TestUserContext,
    db: Session,
    session: ConversationSession,
) -> dict:
    """
    Handle: "Clock out" / "Clock out of Johnson job"

    Entities: (none required — finds open entry by user + active job)

    Behavior:
    1. Find open JobTimeEntry (ended_at IS NULL, user_id=tech, job_id=active_job)
    2. If no open entry → return error
    3. Set ended_at=now(), compute hours=(ended_at-started_at)/3600
    4. Resolve burdened labor rate from LaborRateVersion catalog
    5. Compute total_cost_cents = hours × burdened_rate_cents
    6. Return success response with hours and total cost

    B20/A90: Hands-free time tracking — clocking out stops the timer and records labor cost.
    """
    context = session.context_window_json or {}
    active_job_id = context.get("active_job_id")

    if not active_job_id:
        return {
            "action": "clock_out",
            "success": False,
            "error": "No active job",
            "message": "You don't have an active job set. Which job did you work on?",
        }

    # Find open time entry: ended_at IS NULL, user_id=tech, job_id=active_job
    from app.models.fulfillment import JobTimeEntry

    open_entry = db.exec(
        select(JobTimeEntry)
        .where(JobTimeEntry.user_id == current_user.id)
        .where(JobTimeEntry.job_id == UUID(active_job_id))
        .where(JobTimeEntry.ended_at.is_(None))
        .order_by(JobTimeEntry.started_at.desc())
    ).first()

    if not open_entry:
        return {
            "action": "clock_out",
            "success": False,
            "error": "No open clock-in",
            "message": "I don't see an open clock-in for you on this job.",
        }

    # Set ended_at and compute hours
    now = datetime.now(UTC)
    open_entry.ended_at = now
    hours = (now - open_entry.started_at).total_seconds() / 3600

    # Resolve labor rate from LaborRateVersion catalog
    from app.models.auth import TenantUser
    from app.models.catalog import LaborRateVersion

    tenant_user = db.exec(
        select(TenantUser)
        .where(TenantUser.tenant_id == current_user.tenant_id)
        .where(TenantUser.user_id == current_user.id)
    ).first()

    skill_level_code = tenant_user.skill_level_code if tenant_user else None
    if not skill_level_code:
        # Fallback to default_labor_rate_cents
        from services.setting_resolver import get_effective_setting

        default_rate, _ = get_effective_setting(
            db, current_user.tenant_id, "default_labor_rate_cents", fallback=5000
        )
        hourly_rate_cents = int(default_rate) if default_rate else 5000
    else:
        # Query labor rate for this tenant + skill level at current time
        rate_record = db.exec(
            select(LaborRateVersion).where(
                LaborRateVersion.tenant_id == current_user.tenant_id,
                LaborRateVersion.skill_level_code == skill_level_code,
            )
        ).first()

        if rate_record:
            # Compute burdened rate: hourly_rate_cents * (1 + burden_pct)
            hourly_rate_cents = int(
                rate_record.hourly_rate_cents * (1 + rate_record.burden_pct)
            )
        else:
            # Fallback to default_labor_rate_cents
            from services.setting_resolver import get_effective_setting

            default_rate, _ = get_effective_setting(
                db, current_user.tenant_id, "default_labor_rate_cents", fallback=5000
            )
            hourly_rate_cents = int(default_rate) if default_rate else 5000

    # Update entry
    open_entry.hours = hours
    open_entry.total_cost_cents = int(hours * hourly_rate_cents)
    db.add(open_entry)
    db.commit()

    # Fetch job/customer for response
    job = db.exec(
        select(Job)
        .where(Job.id == UUID(active_job_id))
        .where(Job.tenant_id == current_user.tenant_id)
    ).first()
    customer = (
        db.exec(
            select(Customer).where(
                Customer.id == job.customer_id,
                Customer.tenant_id == current_user.tenant_id,
            )
        ).first()
        if job
        else None
    )
    customer_name = customer.display_name if customer else "Unknown"

    return {
        "action": "clock_out",
        "success": True,
        "message": f"Clocked out of {customer_name} job. {hours:.2f} hours logged.",
        "data": {
            "time_entry_id": str(open_entry.id),
            "job_id": str(job.id) if job else active_job_id,
            "hours": round(hours, 2),
            "cost_cents": open_entry.total_cost_cents,
        },
        "next_prompts": [
            "Add expense",
            "Show job profit",
            "Clock in on another job",
        ],
    }


async def confirm_loto_via_voice(
    entities: dict,
    current_user: AuthenticatedUser | TestUserContext,
    db: Session,
    session: ConversationSession,
) -> dict:
    """
    Handle: "Confirm LOTO" / "LOTO confirmed" / "Locked out"

    Entities: (none required — job_id read from context window)

    Behavior:
    1. Read active_job_id from context window
    2. INSERT loto_confirmation row (confirmed_at=now(), created_by=current_user.id)
    3. Set ctx.safety_loto_verified = True
    4. Return success response

    B20/A89: Works regardless of loto_confirmation_required setting — optional audit
    capture when setting is disabled, mandatory gate relief when enabled.
    """
    context = session.context_window_json or {}
    active_job_id = context.get("active_job_id")
    if not active_job_id:
        return {
            "action": "confirm_loto",
            "success": False,
            "error": "No active job",
            "message": "Which job are you confirming LOTO for? Please set an active job first.",
        }

    # Tenant-scoped job fetch — db.get() BANNED per §6.2
    from app.models.fulfillment import LotoConfirmation

    job = db.exec(
        select(Job)
        .where(Job.id == UUID(active_job_id))
        .where(Job.tenant_id == current_user.tenant_id)
    ).first()
    if not job:
        return {
            "action": "confirm_loto",
            "success": False,
            "error": "Job not found",
            "message": "I couldn't find the active job. Please check your job selection.",
        }

    now = datetime.now(UTC)

    # Idempotency: check for existing active LOTO for this (job, user)
    existing = db.exec(
        select(LotoConfirmation)
        .where(LotoConfirmation.job_id == job.id)
        .where(LotoConfirmation.user_id == current_user.id)
        .where(LotoConfirmation.is_active == True)
    ).first()

    if not existing:
        record = LotoConfirmation(
            tenant_id=current_user.tenant_id,
            job_id=job.id,
            user_id=current_user.id,
            confirmed_at=now,
            created_by=current_user.id,
        )
        db.add(record)
        db.commit()

    # Set safety_loto_verified = True in context window
    ctx = ContextWindowSchema.from_jsonb(session.context_window_json)
    ctx.safety_loto_verified = True
    session.context_window_json = ctx.to_jsonb()
    db.add(session)
    db.commit()

    return {
        "action": "confirm_loto",
        "success": True,
        "message": "LOTO confirmed. Lock Out / Tag Out recorded for this job. You may proceed.",
        "data": {
            "job_id": str(job.id),
            "confirmed_at": now.isoformat(),
        },
        "next_prompts": [
            "Log time",
            "Add expense",
            "Show job details",
        ],
    }


# ==================== HANDLER 8: LOG TIME ENTRY ====================


async def log_time_entry_via_voice(
    entities: dict,
    current_user: AuthenticatedUser | TestUserContext,
    db: Session,
    session: ConversationSession,
) -> dict:
    """
    Handle: "Log 3 hours on the Johnson panel upgrade"

    Entities:
        - hours: 3
        - job_reference: "Johnson panel upgrade"
        - notes: "Panel upgrade work"

    Requires active job in context or job reference.
    """
    hours = entities.get("hours")

    if not hours:
        return {
            "action": "log_time_entry",
            "success": False,
            "error": "Missing hours",
            "message": "How many hours did you work?",
        }

    # Convert to float
    try:
        hours = float(hours)
    except (ValueError, TypeError):
        return {
            "action": "log_time_entry",
            "success": False,
            "error": "Invalid hours format",
            "message": f"I didn't understand '{hours}' as a number of hours.",
        }

    # Find job
    job_reference = entities.get("job_reference")
    context = session.context_window_json or {}

    if not job_reference:
        active_job_id = context.get("active_job_id")
        if not active_job_id:
            return {
                "action": "log_time_entry",
                "success": False,
                "error": "No job specified",
                "message": "Which job are you logging time for?",
            }
        job = db.exec(
            select(Job)
            .where(Job.id == UUID(active_job_id))
            .where(Job.tenant_id == current_user.tenant_id)
        ).first()
    else:
        # Find by customer name
        job = db.exec(
            select(Job)
            .join(Customer, Job.customer_id == Customer.id)
            .where(Job.tenant_id == current_user.tenant_id)
            .where(Customer.display_name.ilike(f"%{job_reference}%"))
        ).first()

    if not job or job.tenant_id != current_user.tenant_id:
        return {
            "action": "log_time_entry",
            "success": False,
            "error": "Job not found",
            "message": "I couldn't find that job.",
        }

    # Resolve labor rate from LaborRateVersion catalog (FIND-056 pattern)
    from app.models.auth import TenantUser
    from app.models.catalog import LaborRateVersion

    tenant_user = db.exec(
        select(TenantUser)
        .where(TenantUser.tenant_id == current_user.tenant_id)
        .where(TenantUser.user_id == current_user.id)
    ).first()

    skill_level_code = tenant_user.skill_level_code if tenant_user else None
    if not skill_level_code:
        # Fallback to default_labor_rate_cents from settings
        from services.setting_resolver import get_effective_setting

        default_rate, _ = get_effective_setting(
            db, current_user.tenant_id, "default_labor_rate_cents", fallback=5000
        )
        hourly_rate_cents = int(default_rate) if default_rate else 5000
    else:
        # Query labor rate for this tenant + skill level at current time
        rate_record = db.exec(
            select(LaborRateVersion).where(
                LaborRateVersion.tenant_id == current_user.tenant_id,
                LaborRateVersion.skill_level_code == skill_level_code,
            )
        ).first()

        if rate_record:
            # Compute burdened rate: hourly_rate_cents * (1 + burden_pct)
            hourly_rate_cents = int(
                rate_record.hourly_rate_cents * (1 + rate_record.burden_pct)
            )
        else:
            # Fallback to default_labor_rate_cents
            from services.setting_resolver import get_effective_setting

            default_rate, _ = get_effective_setting(
                db, current_user.tenant_id, "default_labor_rate_cents", fallback=5000
            )
            hourly_rate_cents = int(default_rate) if default_rate else 5000

    # B20/A89: LOTO guard — check before time-entry stop (ended_at is always set in MVP)
    # Gate fires only when loto_confirmation_required=true AND safety_loto_verified is not True
    now = datetime.now(UTC)
    from services.setting_resolver import get_effective_setting

    loto_required, _ = get_effective_setting(
        db, current_user.tenant_id, "loto_confirmation_required", fallback=False
    )
    if loto_required is True:
        ctx = ContextWindowSchema.from_jsonb(session.context_window_json)
        if ctx.safety_loto_verified is not True:
            return {
                "action": "log_time_entry",
                "success": False,
                "message": "LOTO confirmation required before clocking out. "
                "Please confirm Lock Out / Tag Out first.",
                "next_prompts": ["Confirm LOTO", "Cancel"],
            }

    # Create time entry
    entry_in = JobTimeEntryCreate(
        user_id=current_user.id,
        started_at=now,
        ended_at=now,  # MVP: Single timestamp
        hours=hours,
        hourly_rate_cents=hourly_rate_cents,
        notes=entities.get("notes"),
    )

    try:
        entry = _create_job_time_entry_impl(job.id, entry_in, db, current_user)
    except Exception as e:
        return {
            "action": "log_time_entry",
            "success": False,
            "error": str(e),
            "message": f"Couldn't log time: {e!s}",
        }

    # FIND-132: tenant-scoped query
    customer = db.exec(
        select(Customer).where(
            Customer.id == job.customer_id,
            Customer.tenant_id == current_user.tenant_id,
        )
    ).first()
    customer_name = customer.display_name if customer else "Unknown"

    return {
        "action": "log_time_entry",
        "success": True,
        "message": f"Logged {hours} hours on {customer_name} job.",
        "data": {
            "time_entry_id": str(entry.id),
            "job_id": str(job.id),
            "hours": hours,
            "cost_cents": entry.total_cost_cents,
        },
        "next_prompts": [
            "Log more time",
            "Add expense",
            "Show job profit",
        ],
    }


# ==================== HANDLER 9: ADD EXPENSE ====================


async def add_expense_via_voice(
    entities: dict,
    current_user: AuthenticatedUser | TestUserContext,
    db: Session,
    session: ConversationSession,
) -> dict:
    """
    Handle: "Add $45.99 expense for breakers from the supply house"

    Entities:
        - amount: 45.99
        - description: "breakers"
        - vendor: "Home Depot"
        - job_reference: optional

    Requires active job in context or job reference.
    """
    amount = entities.get("amount")
    description = entities.get("description", "Unknown expense")

    if not amount:
        return {
            "action": "add_expense",
            "success": False,
            "error": "Missing amount",
            "message": "How much was the expense?",
        }

    # Convert to cents
    try:
        amount_float = float(amount)
        cost_cents = int(amount_float * 100)
    except (ValueError, TypeError):
        return {
            "action": "add_expense",
            "success": False,
            "error": "Invalid amount format",
            "message": f"I didn't understand '{amount}' as a dollar amount.",
        }

    # Find job
    job_reference = entities.get("job_reference")
    context = session.context_window_json or {}

    if not job_reference:
        active_job_id = context.get("active_job_id")
        if not active_job_id:
            return {
                "action": "add_expense",
                "success": False,
                "error": "No job specified",
                "message": "Which job is this expense for?",
            }
        job = db.exec(
            select(Job)
            .where(Job.id == UUID(active_job_id))
            .where(Job.tenant_id == current_user.tenant_id)
        ).first()
    else:
        job = db.exec(
            select(Job)
            .join(Customer, Job.customer_id == Customer.id)
            .where(Job.tenant_id == current_user.tenant_id)
            .where(Customer.display_name.ilike(f"%{job_reference}%"))
        ).first()

    if not job or job.tenant_id != current_user.tenant_id:
        return {
            "action": "add_expense",
            "success": False,
            "error": "Job not found",
            "message": "I couldn't find that job.",
        }

    # Find default expense category
    expense_category = db.exec(
        select(JobExpenseCategory)
        .where(
            (JobExpenseCategory.tenant_id == current_user.tenant_id)
            | (JobExpenseCategory.tenant_id == None)
        )
        .where(JobExpenseCategory.is_default == True)
    ).first()

    if not expense_category:
        expense_category = db.exec(select(JobExpenseCategory)).first()

    if not expense_category:
        return {
            "action": "add_expense",
            "success": False,
            "error": "No expense category configured",
            "message": "System error: No expense categories configured.",
        }

    # Create expense
    now = datetime.now(UTC)
    expense_in = JobExpenseCreate(
        job_expense_category_code=expense_category.code,
        description=description,
        vendor_name=entities.get("vendor"),
        incurred_at=now,
        cost_cents=cost_cents,
        is_billable=True,
    )

    try:
        expense = _create_job_expense_impl(job.id, expense_in, db, current_user)
    except Exception as e:
        return {
            "action": "add_expense",
            "success": False,
            "error": str(e),
            "message": f"Couldn't add expense: {e!s}",
        }

    # FIND-132: tenant-scoped query
    customer = db.exec(
        select(Customer).where(
            Customer.id == job.customer_id,
            Customer.tenant_id == current_user.tenant_id,
        )
    ).first()
    customer_name = customer.display_name if customer else "Unknown"

    return {
        "action": "add_expense",
        "success": True,
        "message": f"Added ${cost_cents / 100:.2f} expense to {customer_name} job.",
        "data": {
            "expense_id": str(expense.id),
            "job_id": str(job.id),
            "cost_cents": cost_cents,
            "description": description,
        },
        "next_prompts": [
            "Add more expenses",
            "Show job profit",
            "Log time",
        ],
    }


# ==================== HANDLER 10: SEND QUOTE ====================


async def send_quote_via_voice(
    entities: dict,
    current_user: AuthenticatedUser | TestUserContext,
    db: Session,
    session: ConversationSession,
) -> dict:
    """
    Handle: "Send quote #123 to the customer"

    Entities:
        - quote_id: "123" or from context
        - recipient: email address (optional)

    MVP: Returns placeholder (email sending is Gap #26).
    """
    # Resolve quote
    quote_reference = entities.get("quote_id") or entities.get("quote_reference")
    context = session.context_window_json or {}

    if not quote_reference:
        active_quote_id = context.get("active_quote_id")
        if not active_quote_id:
            return {
                "action": "send_quote",
                "success": False,
                "error": "No quote specified",
                "message": "Which quote do you want to send?",
            }
        quote = db.get(Quote, UUID(active_quote_id))
    else:
        # Try to find by ID or customer name
        try:
            quote = db.get(Quote, UUID(quote_reference))
        except (ValueError, TypeError):
            # Search by customer name
            quote = db.exec(
                select(Quote)
                .join(Customer, Quote.customer_id == Customer.id)
                .where(Quote.tenant_id == current_user.tenant_id)
                .where(Customer.display_name.ilike(f"%{quote_reference}%"))
            ).first()

    if not quote or quote.tenant_id != current_user.tenant_id:
        return {
            "action": "send_quote",
            "success": False,
            "error": "Quote not found",
            "message": "I couldn't find that quote.",
        }

    # Get customer — FIND-132: tenant-scoped query
    customer = db.exec(
        select(Customer).where(
            Customer.id == quote.customer_id,
            Customer.tenant_id == current_user.tenant_id,
        )
    ).first()
    if not customer:
        return {
            "action": "send_quote",
            "success": False,
            "error": "Customer not found",
            "message": "Couldn't find the customer for this quote.",
        }

    # MVP: Return placeholder (actual email sending is Gap #26 - Notification Outbox Worker)
    return {
        "action": "send_quote",
        "success": True,
        "message": f"Quote sending coming soon! For now, manually email Quote #{str(quote.id)[:8]} to {customer.display_name}.",
        "data": {
            "quote_id": str(quote.id),
            "customer_id": str(customer.id),
            "customer_name": customer.display_name,
            "customer_email": customer.email,
            "note": "MVP placeholder - full email integration in Phase 2 (Gap #26)",
        },
        "next_prompts": [
            "Create another quote",
            "Show all quotes",
        ],
    }


# ==================== HANDLER 11: SCHEDULE JOB ====================


async def schedule_job_via_voice(
    entities: dict,
    current_user: AuthenticatedUser | TestUserContext,
    db: Session,
    session: ConversationSession,
) -> dict:
    """Handle: "Schedule the Johnson job for tomorrow 9am to 11am"

    Entities:
        - job_id:          UUID string of the job to schedule (or from context)
        - scheduled_start_at: ISO 8601 datetime string for start
        - scheduled_end_at:   ISO 8601 datetime string for end
        - tech_user_id:    Optional UUID string of tech to assign as primary

    Behaviour:
        1. Resolve job (entity or active context).
        2. Parse scheduled_start_at / scheduled_end_at.
        3. If tech_user_id is provided, call check_slot_feasibility; reject if
           hard conflicts exist (availability_block, double_booking, drive_time).
        4. Persist updated scheduled times to the Job row.
        5. Update context window.
    """
    from services.scheduling_service import check_slot_feasibility

    # --- 1. Resolve job ---
    job_id_str = entities.get("job_id")
    context = session.context_window_json or {}

    if not job_id_str:
        job_id_str = context.get("active_job_id")

    if not job_id_str:
        return {
            "action": "schedule_job",
            "success": False,
            "error": "No job specified",
            "message": "Which job would you like to schedule?",
            "next_prompts": ["Say the job ID or customer name"],
        }

    try:
        job_uuid = UUID(job_id_str)
    except ValueError:
        return {
            "action": "schedule_job",
            "success": False,
            "error": "Invalid job ID",
            "message": f"'{job_id_str}' is not a valid job ID.",
        }

    job = db.exec(
        select(Job)
        .where(Job.id == job_uuid)
        .where(Job.tenant_id == current_user.tenant_id)
        .where(Job.is_active == True)
    ).first()

    if not job:
        return {
            "action": "schedule_job",
            "success": False,
            "error": "Job not found",
            "message": "I couldn't find that job.",
        }

    # --- 2. Parse times ---
    start_str = entities.get("scheduled_start_at")
    end_str = entities.get("scheduled_end_at")

    if not start_str or not end_str:
        return {
            "action": "schedule_job",
            "success": False,
            "error": "Missing schedule times",
            "message": "Please provide both a start and end time for the job.",
            "next_prompts": ["Specify start and end datetime"],
        }

    try:
        proposed_start = datetime.fromisoformat(start_str)
        proposed_end = datetime.fromisoformat(end_str)
        if proposed_start.tzinfo is None:
            proposed_start = proposed_start.replace(tzinfo=UTC)
        if proposed_end.tzinfo is None:
            proposed_end = proposed_end.replace(tzinfo=UTC)
    except ValueError:
        return {
            "action": "schedule_job",
            "success": False,
            "error": "Invalid datetime format",
            "message": "I couldn't parse those times. Use ISO 8601 format (e.g., 2026-04-25T09:00:00Z).",
        }

    if proposed_end <= proposed_start:
        return {
            "action": "schedule_job",
            "success": False,
            "error": "Invalid time range",
            "message": "The end time must be after the start time.",
        }

    # --- 3. Conflict detection (only when a tech is specified) ---
    tech_user_id_str = entities.get("tech_user_id")
    conflicts_found = []

    if tech_user_id_str:
        try:
            tech_uuid = UUID(tech_user_id_str)
        except ValueError:
            return {
                "action": "schedule_job",
                "success": False,
                "error": "Invalid tech_user_id",
                "message": f"'{tech_user_id_str}' is not a valid user ID.",
            }

        feasibility = check_slot_feasibility(
            db=db,
            tenant_id=current_user.tenant_id,
            tech_user_id=tech_uuid,
            proposed_start=proposed_start,
            proposed_end=proposed_end,
            exclude_job_id=job.id,
        )

        hard_conflict_types = {"availability_block", "double_booking", "drive_time"}
        hard_conflicts = [
            c
            for c in feasibility["conflicts"]
            if c["conflict_type"] in hard_conflict_types
        ]

        if hard_conflicts:
            conflict_msgs = "; ".join(c["description"] for c in hard_conflicts)
            return {
                "action": "schedule_job",
                "success": False,
                "error": "scheduling_conflict",
                "message": f"Cannot schedule: {conflict_msgs}. Please choose a different time or tech.",
                "data": {"conflicts": feasibility["conflicts"]},
                "next_prompts": ["Choose a different time", "Assign a different tech"],
            }

        conflicts_found = feasibility.get("conflicts", [])

    # --- 4. Persist ---
    job.scheduled_start_at = proposed_start
    job.scheduled_end_at = proposed_end
    job.updated_by = current_user.id
    db.add(job)
    db.commit()
    db.refresh(job)

    # --- 5. Update context ---
    ctx = ContextWindowSchema.from_jsonb(session.context_window_json)
    ctx.active_job_id = str(job.id)
    ctx.last_action = "schedule_job"
    ctx.timestamp = datetime.now(UTC).isoformat()
    session.context_window_json = ctx.to_jsonb()
    db.add(session)
    db.commit()

    warning_note = ""
    if conflicts_found:
        warning_note = " ⚠ Drive-time warning — verify manually."

    return {
        "action": "schedule_job",
        "success": True,
        "message": (
            f"Job scheduled from {proposed_start.strftime('%b %d %H:%M')} "
            f"to {proposed_end.strftime('%H:%M UTC')}.{warning_note}"
        ),
        "data": {
            "job_id": str(job.id),
            "scheduled_start_at": proposed_start.isoformat(),
            "scheduled_end_at": proposed_end.isoformat(),
            "warnings": conflicts_found,
        },
        "next_prompts": ["Assign a technician", "Show dispatch board"],
    }


# ==================== HANDLER 12: REASSIGN JOB ====================


async def reassign_job_via_voice(
    entities: dict,
    current_user: AuthenticatedUser | TestUserContext,
    db: Session,
    session: ConversationSession,
) -> dict:
    """Handle: "Reassign the Johnson job to tech Mike"

    Entities:
        - job_id:       UUID string of the job (or from context)
        - tech_user_id: UUID string of the new primary technician

    Behaviour:
        1. Resolve job.
        2. Resolve new tech UUID.
        3. Validate new tech can take the slot (check_slot_feasibility).
        4. Soft-delete existing primary assignment.
        5. Insert new primary assignment.
        6. Update context window.
    """
    from app.models.scheduling import JobTechAssignment
    from services.scheduling_service import check_slot_feasibility

    # --- 1. Resolve job ---
    job_id_str = entities.get("job_id")
    context = session.context_window_json or {}

    if not job_id_str:
        job_id_str = context.get("active_job_id")

    if not job_id_str:
        return {
            "action": "reassign_job",
            "success": False,
            "error": "No job specified",
            "message": "Which job would you like to reassign?",
        }

    try:
        job_uuid = UUID(job_id_str)
    except ValueError:
        return {
            "action": "reassign_job",
            "success": False,
            "error": "Invalid job ID",
            "message": f"'{job_id_str}' is not a valid job ID.",
        }

    job = db.exec(
        select(Job)
        .where(Job.id == job_uuid)
        .where(Job.tenant_id == current_user.tenant_id)
        .where(Job.is_active == True)
    ).first()

    if not job:
        return {
            "action": "reassign_job",
            "success": False,
            "error": "Job not found",
            "message": "I couldn't find that job.",
        }

    # --- 2. Resolve new tech ---
    tech_user_id_str = entities.get("tech_user_id")

    if not tech_user_id_str:
        return {
            "action": "reassign_job",
            "success": False,
            "error": "No technician specified",
            "message": "Which technician should I assign this job to?",
        }

    try:
        tech_uuid = UUID(tech_user_id_str)
    except ValueError:
        return {
            "action": "reassign_job",
            "success": False,
            "error": "Invalid tech_user_id",
            "message": f"'{tech_user_id_str}' is not a valid user ID.",
        }

    # --- 3. Conflict detection (requires scheduled times) ---
    if job.scheduled_start_at and job.scheduled_end_at:
        feasibility = check_slot_feasibility(
            db=db,
            tenant_id=current_user.tenant_id,
            tech_user_id=tech_uuid,
            proposed_start=job.scheduled_start_at,
            proposed_end=job.scheduled_end_at,
            exclude_job_id=job.id,
        )

        hard_conflict_types = {"availability_block", "double_booking", "drive_time"}
        hard_conflicts = [
            c
            for c in feasibility["conflicts"]
            if c["conflict_type"] in hard_conflict_types
        ]

        if hard_conflicts:
            conflict_msgs = "; ".join(c["description"] for c in hard_conflicts)
            return {
                "action": "reassign_job",
                "success": False,
                "error": "scheduling_conflict",
                "message": (
                    f"Cannot reassign: {conflict_msgs}. "
                    "The technician is not available during the scheduled window."
                ),
                "data": {"conflicts": feasibility["conflicts"]},
                "next_prompts": ["Choose a different tech", "Change job schedule"],
            }

    # --- 4. Soft-delete existing primary assignment ---
    existing_primary = db.exec(
        select(JobTechAssignment)
        .where(JobTechAssignment.tenant_id == current_user.tenant_id)
        .where(JobTechAssignment.job_id == job.id)
        .where(JobTechAssignment.role == "primary")
        .where(JobTechAssignment.is_active == True)
    ).first()

    if existing_primary:
        existing_primary.is_active = False
        existing_primary.updated_by = current_user.id
        db.add(existing_primary)

    # --- 5. Create new primary assignment ---
    new_assignment = JobTechAssignment(
        tenant_id=current_user.tenant_id,
        job_id=job.id,
        user_id=tech_uuid,
        role="primary",
        ordinal=1,
        assigned_by_user_id=current_user.id,
        is_active=True,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    db.add(new_assignment)
    job.updated_by = current_user.id
    db.add(job)
    db.commit()

    # --- 6. Update context ---
    ctx = ContextWindowSchema.from_jsonb(session.context_window_json)
    ctx.active_job_id = str(job.id)
    ctx.last_action = "reassign_job"
    ctx.timestamp = datetime.now(UTC).isoformat()
    session.context_window_json = ctx.to_jsonb()
    db.add(session)
    db.commit()

    return {
        "action": "reassign_job",
        "success": True,
        "message": f"Job {str(job.id)[:8]} reassigned to technician {tech_user_id_str[:8]}.",
        "data": {
            "job_id": str(job.id),
            "new_tech_user_id": str(tech_uuid),
            "assignment_id": str(new_assignment.id),
        },
        "next_prompts": ["Show dispatch board", "Schedule another job"],
    }


# ==================== HANDLER 13: RESCHEDULE JOB ====================


async def reschedule_job_via_voice(
    entities: dict,
    current_user: AuthenticatedUser | TestUserContext,
    db: Session,
    session: ConversationSession,
) -> dict:
    """Handle: "Move the Johnson job to Thursday at 2pm"

    Entities:
        - job_id:          UUID string of the job to reschedule (or from context)
        - scheduled_start_at: ISO 8601 datetime string for new start
        - scheduled_end_at:   ISO 8601 datetime string for new end

    Behaviour:
        1. Resolve job (entity or active context).
        2. Parse new scheduled_start_at / scheduled_end_at.
        3. Call conflict check service: does assigned tech have conflict?
        4. If conflict → multi-turn confirmation: pending_confirmation=True, return conflict message.
        5. On second turn (if confirmed) → call _update_job_schedule_impl.
        6. Write VoiceCommandEntityLink row: action='rescheduled'.
        7. Notification already emitted by _update_job_schedule_impl (FIND-082).
    """
    from app.models.voice_helpers import _link_voice_to_entity
    from services.scheduling_service import check_slot_feasibility

    # Check if this is a confirmation turn
    context = session.context_window_json or {}
    pending = context.get("pending_confirmation", {})

    if pending.get("action") == "reschedule_job" and pending.get("job_id"):
        # ---- Second turn: User confirmed the reschedule ----
        job_id_str = pending["job_id"]
        try:
            job_uuid = UUID(job_id_str)
        except ValueError:
            return {
                "action": "reschedule_job",
                "success": False,
                "error": "Invalid job ID",
                "message": "Invalid job ID in pending confirmation.",
            }

        job = db.exec(
            select(Job)
            .where(Job.id == job_uuid)
            .where(Job.tenant_id == current_user.tenant_id)
            .where(Job.is_active == True)
        ).first()

        if not job:
            return {
                "action": "reschedule_job",
                "success": False,
                "error": "Job not found",
                "message": "Job not found.",
            }

        # Apply the new schedule from pending
        proposed_start_str = pending.get("proposed_start_at")
        proposed_end_str = pending.get("proposed_end_at")

        try:
            proposed_start = datetime.fromisoformat(proposed_start_str)
            proposed_end = datetime.fromisoformat(proposed_end_str)
            if proposed_start.tzinfo is None:
                proposed_start = proposed_start.replace(tzinfo=UTC)
            if proposed_end.tzinfo is None:
                proposed_end = proposed_end.replace(tzinfo=UTC)
        except (ValueError, TypeError):
            return {
                "action": "reschedule_job",
                "success": False,
                "error": "Invalid datetime format",
                "message": "Invalid datetime in pending confirmation.",
            }

        # Update job schedule
        job.scheduled_start_at = proposed_start
        job.scheduled_end_at = proposed_end
        job.updated_by = current_user.id
        db.add(job)
        db.commit()
        db.refresh(job)

        # Emit schedule_changed notifications to all assigned techs (already done by _update_job_schedule_impl pattern,
        # but we're doing direct update here, so we need to emit)
        from app.models.scheduling import JobTechAssignment

        assigned_techs = db.exec(
            select(JobTechAssignment)
            .where(JobTechAssignment.tenant_id == current_user.tenant_id)
            .where(JobTechAssignment.job_id == job.id)
            .where(JobTechAssignment.is_active == True)
        ).all()

        for assignment in assigned_techs:
            from api.routes.scheduling import _emit_schedule_changed_notification

            _emit_schedule_changed_notification(
                db=db,
                tenant_id=current_user.tenant_id,
                job_id=job.id,
                tech_user_id=assignment.user_id,
                assigner_user_id=current_user.id,
            )
        db.commit()

        # Write VoiceCommandEntityLink (if voice_command_log exists in session)
        if hasattr(session, "voice_command_log_id") and session.voice_command_log_id:
            link = _link_voice_to_entity(
                db=db,
                tenant_id=current_user.tenant_id,
                voice_command_log_id=session.voice_command_log_id,
                entity_type="job",
                entity_id=job.id,
                action="rescheduled",
                created_by=current_user.id,
            )
            db.add(link)
            db.commit()

        # Clear pending confirmation
        context.pop("pending_confirmation", None)
        session.context_window_json = context
        db.add(session)
        db.commit()

        return {
            "action": "reschedule_job",
            "success": True,
            "message": (
                f"Job rescheduled from {proposed_start.strftime('%b %d %H:%M')} "
                f"to {proposed_end.strftime('%H:%M UTC')}."
            ),
            "data": {
                "job_id": str(job.id),
                "scheduled_start_at": proposed_start.isoformat(),
                "scheduled_end_at": proposed_end.isoformat(),
            },
            "next_prompts": ["Show dispatch board", "Check next job"],
        }

    # ---- First turn: Check for conflicts ----
    job_id_str = entities.get("job_id")

    if not job_id_str:
        job_id_str = context.get("active_job_id")

    if not job_id_str:
        return {
            "action": "reschedule_job",
            "success": False,
            "error": "No job specified",
            "message": "Which job would you like to reschedule?",
            "next_prompts": ["Say the job ID or customer name"],
        }

    try:
        job_uuid = UUID(job_id_str)
    except ValueError:
        return {
            "action": "reschedule_job",
            "success": False,
            "error": "Invalid job ID",
            "message": f"'{job_id_str}' is not a valid job ID.",
        }

    job = db.exec(
        select(Job)
        .where(Job.id == job_uuid)
        .where(Job.tenant_id == current_user.tenant_id)
        .where(Job.is_active == True)
    ).first()

    if not job:
        return {
            "action": "reschedule_job",
            "success": False,
            "error": "Job not found",
            "message": "I couldn't find that job.",
        }

    # Parse new times
    start_str = entities.get("scheduled_start_at")
    end_str = entities.get("scheduled_end_at")

    if not start_str or not end_str:
        return {
            "action": "reschedule_job",
            "success": False,
            "error": "Missing schedule times",
            "message": "Please provide both a start and end time for the job.",
            "next_prompts": ["Specify new start and end datetime"],
        }

    try:
        proposed_start = datetime.fromisoformat(start_str)
        proposed_end = datetime.fromisoformat(end_str)
        if proposed_start.tzinfo is None:
            proposed_start = proposed_start.replace(tzinfo=UTC)
        if proposed_end.tzinfo is None:
            proposed_end = proposed_end.replace(tzinfo=UTC)
    except ValueError:
        return {
            "action": "reschedule_job",
            "success": False,
            "error": "Invalid datetime format",
            "message": "I couldn't parse those times. Use ISO 8601 format (e.g., 2026-04-25T09:00:00Z).",
        }

    if proposed_end <= proposed_start:
        return {
            "action": "reschedule_job",
            "success": False,
            "error": "Invalid time range",
            "message": "The end time must be after the start time.",
        }

    # Check for conflicts with assigned tech's schedule
    from app.models.scheduling import JobTechAssignment

    primary_assignment = db.exec(
        select(JobTechAssignment)
        .where(JobTechAssignment.tenant_id == current_user.tenant_id)
        .where(JobTechAssignment.job_id == job.id)
        .where(JobTechAssignment.role == "primary")
        .where(JobTechAssignment.is_active == True)
    ).first()

    conflicts_found = []

    if primary_assignment:
        feasibility = check_slot_feasibility(
            db=db,
            tenant_id=current_user.tenant_id,
            tech_user_id=primary_assignment.user_id,
            proposed_start=proposed_start,
            proposed_end=proposed_end,
            exclude_job_id=job.id,
        )

        hard_conflict_types = {"availability_block", "double_booking", "drive_time"}
        hard_conflicts = [
            c
            for c in feasibility["conflicts"]
            if c["conflict_type"] in hard_conflict_types
        ]

        if hard_conflicts:
            # Write pending confirmation
            conflict_msgs = "; ".join(c["description"] for c in hard_conflicts)
            context["pending_confirmation"] = {
                "action": "reschedule_job",
                "job_id": str(job.id),
                "proposed_start_at": proposed_start.isoformat(),
                "proposed_end_at": proposed_end.isoformat(),
                "conflict_message": conflict_msgs,
            }
            session.context_window_json = context
            db.add(session)
            db.commit()

            return {
                "action": "reschedule_job",
                "success": False,
                "error": "scheduling_conflict",
                "pending_confirmation": True,
                "message": f"There's a conflict: {conflict_msgs}. Reschedule anyway?",
                "data": {"conflicts": feasibility["conflicts"]},
                "next_prompts": ["Yes, reschedule it", "No, cancel"],
            }

        conflicts_found = feasibility.get("conflicts", [])

    # No hard conflicts — apply schedule immediately
    job.scheduled_start_at = proposed_start
    job.scheduled_end_at = proposed_end
    job.updated_by = current_user.id
    db.add(job)
    db.commit()
    db.refresh(job)

    # Emit notifications
    if primary_assignment:
        from api.routes.scheduling import _emit_schedule_changed_notification

        _emit_schedule_changed_notification(
            db=db,
            tenant_id=current_user.tenant_id,
            job_id=job.id,
            tech_user_id=primary_assignment.user_id,
            assigner_user_id=current_user.id,
        )
        db.commit()

    # Write VoiceCommandEntityLink
    if hasattr(session, "voice_command_log_id") and session.voice_command_log_id:
        link = _link_voice_to_entity(
            db=db,
            tenant_id=current_user.tenant_id,
            voice_command_log_id=session.voice_command_log_id,
            entity_type="job",
            entity_id=job.id,
            action="rescheduled",
            created_by=current_user.id,
        )
        db.add(link)
        db.commit()

    warning_note = ""
    if conflicts_found:
        warning_note = " ⚠ Drive-time warning — verify manually."

    return {
        "action": "reschedule_job",
        "success": True,
        "message": (
            f"Job rescheduled from {proposed_start.strftime('%b %d %H:%M')} "
            f"to {proposed_end.strftime('%H:%M UTC')}.{warning_note}"
        ),
        "data": {
            "job_id": str(job.id),
            "scheduled_start_at": proposed_start.isoformat(),
            "scheduled_end_at": proposed_end.isoformat(),
            "warnings": conflicts_found,
        },
        "next_prompts": ["Show dispatch board", "Check next job"],
    }


# ==================== HANDLER 14: CHECK NEXT JOB ====================


async def check_next_job_via_voice(
    entities: dict,
    current_user: AuthenticatedUser | TestUserContext,
    db: Session,
    session: ConversationSession,
) -> dict:
    """Handle: "What's my next job?"

    Behaviour:
        1. Read-only — no DB writes, no VoiceCommandEntityLink row.
        2. Query job_assignment WHERE user_id=current_user.id AND scheduled_start > now()
           ORDER BY scheduled_start ASC LIMIT 1.
        3. Return job details (customer, address, time, description).
        4. If no upcoming jobs: return "no upcoming scheduled jobs" message.
    """
    from app.models.crm import Customer
    from app.models.scheduling import JobTechAssignment

    # Query for the next upcoming job assigned to this user
    next_assignment = db.exec(
        select(JobTechAssignment)
        .join(Job)
        .where(JobTechAssignment.tenant_id == current_user.tenant_id)
        .where(JobTechAssignment.user_id == current_user.id)
        .where(JobTechAssignment.is_active == True)
        .where(Job.scheduled_start_at > datetime.now(UTC))
        .order_by(Job.scheduled_start_at.asc())
        .limit(1)
    ).first()

    if not next_assignment:
        return {
            "action": "check_next_job",
            "success": True,
            "message": "You have no upcoming scheduled jobs.",
            "data": {"next_job": None},
            "next_prompts": ["Create a job", "Show dispatch board"],
        }

    # Get the job details
    job = db.exec(
        select(Job)
        .where(Job.id == next_assignment.job_id)
        .where(Job.tenant_id == current_user.tenant_id)
        .where(Job.scheduled_start_at > datetime.now(UTC))
    ).first()

    if not job:
        return {
            "action": "check_next_job",
            "success": True,
            "message": "You have no upcoming scheduled jobs.",
            "data": {"next_job": None},
            "next_prompts": ["Create a job", "Show dispatch board"],
        }

    customer = db.exec(select(Customer).where(Customer.id == job.customer_id)).first()

    customer_name = customer.display_name if customer else "Unknown Customer"
    address = "Site address"
    scheduled_start = job.scheduled_start_at

    # Format response
    time_str = scheduled_start.strftime("%A at %I:%M %p")

    return {
        "action": "check_next_job",
        "success": True,
        "message": f"Your next job is {customer_name} at {address}, scheduled for {time_str}.",
        "data": {
            "next_job": {
                "job_id": str(job.id),
                "customer_name": customer_name,
                "address": address,
                "scheduled_start_at": scheduled_start.isoformat(),
            }
        },
        "next_prompts": ["Reschedule this job", "Show dispatch board"],
    }


# ==================== HANDLER REGISTRY ====================

# ==================== A31: VOICE INTENT GRAMMAR FOR APPROVAL ACTIONS ====================


async def approve_quote_via_voice(
    entities: dict,
    current_user: AuthenticatedUser | TestUserContext,
    db: Session,
    session: ConversationSession,
) -> dict:
    """
    A31: Handle 'approve_quote' voice intent.

    Pattern: §16.3 Confirm-as-Turn — writes pending_confirmation to session
    context_window_json before executing. Next affirmative turn commits.

    Entities: { "quote_identifier": "Johnson panel" } (optional)
    """
    from app.models.quoting import Quote
    from services.quote_service import get_quote_status_code

    # Check if this is a confirmation of a pending action
    context = getattr(session, "context_window_json", {}) or {}
    pending = context.get("pending_confirmation", {})

    if pending.get("action") == "approve_quote" and pending.get("quote_id"):
        # Second turn — user confirmed → execute approval
        quote_id_str = pending["quote_id"]
        try:
            quote_id = UUID(quote_id_str)
        except (ValueError, TypeError):
            return {
                "action": "approve_quote",
                "success": False,
                "message": "Invalid quote reference in pending confirmation.",
            }

        quote = db.exec(
            select(Quote)
            .where(Quote.id == quote_id)
            .where(Quote.tenant_id == current_user.tenant_id)
            .where(Quote.is_active == True)
        ).first()

        if not quote:
            return {
                "action": "approve_quote",
                "success": False,
                "message": "Quote not found.",
            }

        current_status = get_quote_status_code(quote, db)
        if current_status == "approved":
            return {
                "action": "approve_quote",
                "success": True,
                "message": "That quote is already approved.",
            }
        if current_status != "pending_approval":
            return {
                "action": "approve_quote",
                "success": False,
                "message": f"That quote is not pending approval — it's currently '{current_status}'.",
            }

        from datetime import UTC
        from datetime import datetime as dt

        from services.quote_service import transition_quote_status

        quote.approved_by_user_id = current_user.id
        quote.approved_at = dt.now(UTC)
        db.add(quote)
        quote = transition_quote_status(quote, "approved", db, current_user.tenant_id)

        # Clear pending confirmation
        context.pop("pending_confirmation", None)
        session.context_window_json = context
        db.add(session)
        db.commit()

        return {
            "action": "approve_quote",
            "success": True,
            "quote_id": str(quote.id),
            "status": "approved",
            "message": "Quote approved.",
        }

    # First turn — prompt for confirmation
    quote_identifier = entities.get("quote_identifier", "")
    context["pending_confirmation"] = {
        "action": "approve_quote",
        "quote_identifier": quote_identifier,
        "quote_id": entities.get("quote_id"),  # may be pre-resolved by NLU
    }
    session.context_window_json = context
    db.add(session)
    db.commit()

    identifier_text = f'"{quote_identifier}"' if quote_identifier else "this quote"
    return {
        "action": "approve_quote",
        "success": True,
        "requires_confirmation": True,
        "message": f"Are you sure you want to approve {identifier_text}? Say 'yes' or 'confirm' to proceed.",
    }


async def reject_quote_via_voice(
    entities: dict,
    current_user: AuthenticatedUser | TestUserContext,
    db: Session,
    session: ConversationSession,
) -> dict:
    """
    A31: Handle 'reject_quote' voice intent.

    Requires reason. Entities: { "quote_id": UUID, "reason": str }
    """
    from app.models.quoting import Quote
    from services.quote_service import get_quote_status_code, transition_quote_status

    quote_id_str = entities.get("quote_id")
    reason = entities.get("reason", "")

    if not reason:
        return {
            "action": "reject_quote",
            "success": False,
            "message": "Please provide a reason for rejecting the quote.",
        }

    if not quote_id_str:
        return {
            "action": "reject_quote",
            "success": False,
            "message": "Please specify which quote to reject.",
        }

    try:
        quote_id = UUID(quote_id_str)
    except (ValueError, TypeError):
        return {
            "action": "reject_quote",
            "success": False,
            "message": "Invalid quote reference.",
        }

    quote = db.exec(
        select(Quote)
        .where(Quote.id == quote_id)
        .where(Quote.tenant_id == current_user.tenant_id)
        .where(Quote.is_active == True)
    ).first()

    if not quote:
        return {
            "action": "reject_quote",
            "success": False,
            "message": "Quote not found.",
        }

    current_status = get_quote_status_code(quote, db)
    if current_status != "pending_approval":
        return {
            "action": "reject_quote",
            "success": False,
            "message": f"Cannot reject — quote is '{current_status}', not pending approval.",
        }

    quote = transition_quote_status(quote, "rejected", db, current_user.tenant_id)

    return {
        "action": "reject_quote",
        "success": True,
        "quote_id": str(quote.id),
        "status": "rejected",
        "message": "Quote rejected.",
    }


async def kickback_quote_via_voice(
    entities: dict,
    current_user: AuthenticatedUser | TestUserContext,
    db: Session,
    session: ConversationSession,
) -> dict:
    """
    A31: Handle 'kickback_quote' voice intent (return to tech for revisions).

    Pattern: §16.3 Confirm-as-Turn.
    Entities: { "quote_id": UUID, "comment": str }
    """
    from app.models.quoting import Quote

    # Check pending confirmation
    context = getattr(session, "context_window_json", {}) or {}
    pending = context.get("pending_confirmation", {})

    if pending.get("action") == "kickback_quote" and pending.get("quote_id"):
        from app.models.quoting import QuoteApprovalComment, QuoteVersion
        from services.quote_service import transition_quote_status

        try:
            quote_id = UUID(pending["quote_id"])
        except (ValueError, TypeError):
            return {
                "action": "kickback_quote",
                "success": False,
                "message": "Invalid quote reference.",
            }

        quote = db.exec(
            select(Quote).where(
                Quote.id == quote_id, Quote.tenant_id == current_user.tenant_id
            )
        ).first()
        if not quote:
            return {
                "action": "kickback_quote",
                "success": False,
                "message": "Quote not found.",
            }

        # Add kickback comment
        latest_version = db.exec(
            select(QuoteVersion)
            .where(
                QuoteVersion.quote_id == quote_id,
                QuoteVersion.tenant_id == current_user.tenant_id,
            )
            .order_by(QuoteVersion.version_no.desc())
        ).first()

        if latest_version and pending.get("comment"):
            comment = QuoteApprovalComment(
                tenant_id=current_user.tenant_id,
                quote_id=quote_id,
                quote_version_id=latest_version.id,
                author_user_id=current_user.id,
                comment_type="kickback",
                content=pending["comment"],
                created_by=current_user.id,
            )
            db.add(comment)
            db.flush()

        quote = transition_quote_status(quote, "draft", db, current_user.tenant_id)

        context.pop("pending_confirmation", None)
        session.context_window_json = context
        db.add(session)
        db.commit()

        return {
            "action": "kickback_quote",
            "success": True,
            "quote_id": str(quote.id),
            "status": "draft",
            "message": "Quote sent back to the technician for revisions.",
        }

    # First turn — request confirmation
    quote_id_str = entities.get("quote_id")
    comment = entities.get("comment", "Please revise and resubmit.")
    context["pending_confirmation"] = {
        "action": "kickback_quote",
        "quote_id": quote_id_str,
        "comment": comment,
    }
    session.context_window_json = context
    db.add(session)
    db.commit()

    return {
        "action": "kickback_quote",
        "success": True,
        "requires_confirmation": True,
        "message": f"Are you sure you want to send this quote back with the comment: '{comment}'? Say 'yes' to confirm.",
    }


async def list_pending_quotes_via_voice(
    entities: dict,
    current_user: AuthenticatedUser | TestUserContext,
    db: Session,
    session: ConversationSession,
) -> dict:
    """
    A31: Handle 'list_pending_quotes' voice intent.

    Returns a summary of all quotes in pending_approval status for the tenant.
    """
    from services.quote_service import get_quote_pending_approval_summary

    summaries = get_quote_pending_approval_summary(current_user.tenant_id, db)

    if not summaries:
        return {
            "action": "list_pending_quotes",
            "success": True,
            "pending_count": 0,
            "message": "No quotes are pending your approval.",
            "quotes": [],
        }

    quote_list = [
        f"Quote {s['quote_id'][:8]}... — ${s['total_cents'] / 100:.2f}"
        for s in summaries[:5]  # cap at 5 for voice
    ]
    message = f"{len(summaries)} quote(s) pending approval: " + ", ".join(quote_list)

    return {
        "action": "list_pending_quotes",
        "success": True,
        "pending_count": len(summaries),
        "quotes": summaries,
        "message": message,
    }


# ==================== A10: VOICE SESSION MANAGEMENT HANDLERS ====================


async def rename_session_via_voice(
    entities: dict,
    current_user: AuthenticatedUser | TestUserContext,
    db: Session,
    session: ConversationSession,
) -> dict:
    """
    A10: Handle 'rename_session' voice intent.

    Entities expected:
        - session_number (int, optional): which session to rename; defaults to current
        - new_title (str): the new title for the session

    Behavior:
        - Sets title to new_title, title_auto_generated=False (user-set, frozen)
        - If session_number refers to a different session, that session is renamed
    """
    from services.voice_session_service import resolve_session_by_number

    new_title = entities.get("new_title") or entities.get("title")
    if not new_title:
        return {
            "action": "rename_session",
            "success": False,
            "message": "I need a new name for the session. What should I call it?",
        }

    new_title = str(new_title).strip()[:80]

    # Determine target session
    session_number = entities.get("session_number")
    target_session = session  # default to current session

    if session_number is not None:
        try:
            session_number = int(session_number)
        except (ValueError, TypeError):
            session_number = None

    if session_number is not None:
        resolved = resolve_session_by_number(
            db=db,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            session_number=session_number,
        )
        if resolved is None:
            from services.voice_session_service import get_sessions_with_numbers

            available, _, _ = get_sessions_with_numbers(
                db=db,
                tenant_id=current_user.tenant_id,
                user_id=current_user.id,
                limit=10,
            )
            available_nums = [s["session_number"] for s in available]
            return {
                "action": "rename_session",
                "success": True,
                "requires_disambiguation": True,
                "message": (
                    f"I don't have a Chat {session_number} from today. "
                    f"You have {len(available)} chat(s) — {', '.join(f'Chat {n}' for n in available_nums)}. "
                    f"Which one did you mean?"
                ),
                "disambiguation_data": {
                    "requested_number": session_number,
                    "available_sessions": [
                        {"session_number": s["session_number"], "title": s.get("title")}
                        for s in available
                    ],
                },
            }
        target_session = resolved

    old_title = (
        target_session.title
        or target_session.context_summary
        or f"Chat {session_number or '(current)'}"
    )
    target_session.title = new_title
    target_session.title_auto_generated = False  # user-set → frozen
    db.add(target_session)
    db.commit()

    return {
        "action": "rename_session",
        "success": True,
        "message": f"Renamed '{old_title}' to '{new_title}'.",
        "data": {
            "session_id": str(target_session.id),
            "new_title": new_title,
        },
    }


async def delete_session_via_voice(
    entities: dict,
    current_user: AuthenticatedUser | TestUserContext,
    db: Session,
    session: ConversationSession,
) -> dict:
    """
    A10: Handle 'delete_session' voice intent with confirm-as-turn pattern.

    Pattern: §16.3 Confirm-as-Turn (same as approve_quote_via_voice).
    First turn → writes pending_confirmation, returns requires_confirmation=True.
    Second turn (intent = 'confirm' or 'yes') → executes soft-delete.
    """
    from services.voice_session_service import (
        get_sessions_with_numbers,
        resolve_session_by_number,
    )

    ctx = ContextWindowSchema.from_jsonb(session.context_window_json)

    # Check if this is the confirmation turn
    pending = ctx.get("pending_confirmation", {}) if hasattr(ctx, "get") else {}
    if isinstance(ctx, dict):
        pending = ctx.get("pending_confirmation", {})
    else:
        # ContextWindowSchema object
        ctx_dict = ctx.to_jsonb() if hasattr(ctx, "to_jsonb") else {}
        pending = ctx_dict.get("pending_confirmation", {})

    if pending.get("action") == "delete_session" and pending.get("target_session_id"):
        # Confirmation turn — execute the delete
        target_session_id = pending["target_session_id"]
        target_title = pending.get("target_session_title", "that session")

        target_session = db.exec(
            select(ConversationSession)
            .where(ConversationSession.id == target_session_id)
            .where(ConversationSession.tenant_id == current_user.tenant_id)
        ).first()

        # Clear pending confirmation regardless of outcome
        if hasattr(ctx, "to_jsonb"):
            ctx_dict = ctx.to_jsonb()
        else:
            ctx_dict = dict(ctx) if ctx else {}
        ctx_dict.pop("pending_confirmation", None)
        session.context_window_json = ctx_dict
        db.add(session)

        if not target_session:
            db.commit()
            return {
                "action": "delete_session",
                "success": False,
                "message": f"Session '{target_title}' no longer exists.",
            }

        # Soft-delete: set is_active=False
        target_session.is_active = False
        db.add(target_session)
        db.commit()

        return {
            "action": "delete_session",
            "success": True,
            "message": f"Deleted '{target_title}'.",
            "data": {"session_id": target_session_id},
        }

    # First turn — determine target session and request confirmation
    session_number = entities.get("session_number")
    target_session = session  # default to current session

    if session_number is not None:
        try:
            session_number = int(session_number)
        except (ValueError, TypeError):
            session_number = None

    if session_number is not None:
        resolved = resolve_session_by_number(
            db=db,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            session_number=session_number,
        )
        if resolved is None:
            available, _, _ = get_sessions_with_numbers(
                db=db,
                tenant_id=current_user.tenant_id,
                user_id=current_user.id,
                limit=10,
            )
            return {
                "action": "delete_session",
                "success": True,
                "requires_disambiguation": True,
                "message": (
                    f"I don't have a Chat {session_number} from today. "
                    f"You have {len(available)} chat(s). Which one did you mean?"
                ),
                "disambiguation_data": {
                    "requested_number": session_number,
                    "available_sessions": [
                        {"session_number": s["session_number"], "title": s.get("title")}
                        for s in available
                    ],
                },
            }
        target_session = resolved

    target_title = (
        target_session.title or target_session.context_summary or "this session"
    )

    # Write pending confirmation to context_window_json
    if hasattr(ctx, "to_jsonb"):
        ctx_dict = ctx.to_jsonb()
    else:
        ctx_dict = dict(ctx) if ctx else {}
    ctx_dict["pending_confirmation"] = {
        "action": "delete_session",
        "target_session_id": str(target_session.id),
        "target_session_title": target_title,
    }
    session.context_window_json = ctx_dict
    db.add(session)
    db.commit()

    return {
        "action": "delete_session",
        "success": True,
        "requires_confirmation": True,
        "message": f"Are you sure you want to delete '{target_title}'? Say 'yes' to confirm.",
        "data": {"session_id": str(target_session.id), "title": target_title},
    }


async def open_session_via_voice(
    entities: dict,
    current_user: AuthenticatedUser | TestUserContext,
    db: Session,
    session: ConversationSession,
) -> dict:
    """
    A10: Handle 'open_session' voice intent.

    Returns navigation data for the client to switch to the specified session.
    Entities expected:
        - session_number (int): which session to open
        - title_fragment (str, optional): partial title match as fallback
    """
    from services.voice_session_service import (
        get_sessions_with_numbers,
        resolve_session_by_number,
    )

    session_number = entities.get("session_number")

    if session_number is not None:
        try:
            session_number = int(session_number)
        except (ValueError, TypeError):
            session_number = None

    target_session = None
    if session_number is not None:
        target_session = resolve_session_by_number(
            db=db,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            session_number=session_number,
        )

    if target_session is None and session_number is not None:
        available, _, _ = get_sessions_with_numbers(
            db=db,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            limit=10,
        )
        return {
            "action": "open_session",
            "success": True,
            "requires_disambiguation": True,
            "message": (
                f"I don't have a Chat {session_number} from today. "
                f"You have {len(available)} chat(s). Which one did you mean?"
            ),
            "disambiguation_data": {
                "requested_number": session_number,
                "available_sessions": [
                    {"session_number": s["session_number"], "title": s.get("title")}
                    for s in available
                ],
            },
        }

    if target_session is None:
        return {
            "action": "open_session",
            "success": False,
            "message": "I need a session number to open. Which chat did you mean?",
        }

    title = (
        target_session.title
        or target_session.context_summary
        or f"Chat {session_number}"
    )
    return {
        "action": "open_session",
        "success": True,
        "message": f"Opening '{title}'.",
        "data": {
            "session_id": str(target_session.id),
            "title": title,
            "navigate_to": f"/voice/sessions/{target_session.id}",
        },
    }


async def query_session_summary_via_voice(
    entities: dict,
    current_user: AuthenticatedUser | TestUserContext,
    db: Session,
    session: ConversationSession,
) -> dict:
    """
    A10: Handle 'query_session_summary' voice intent.

    Returns the title/summary of the current or specified session.
    Entities expected:
        - session_number (int, optional): which session; defaults to current
    """
    from services.voice_session_service import (
        get_sessions_with_numbers,
        resolve_session_by_number,
    )

    session_number = entities.get("session_number")

    if session_number is not None:
        try:
            session_number = int(session_number)
        except (ValueError, TypeError):
            session_number = None

    target_session = session  # default to current

    if session_number is not None:
        resolved = resolve_session_by_number(
            db=db,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            session_number=session_number,
        )
        if resolved is None:
            available, _, _ = get_sessions_with_numbers(
                db=db,
                tenant_id=current_user.tenant_id,
                user_id=current_user.id,
                limit=10,
            )
            return {
                "action": "query_session_summary",
                "success": True,
                "requires_disambiguation": True,
                "message": (
                    f"I don't have a Chat {session_number} from today. "
                    f"You have {len(available)} chat(s). Which one did you mean?"
                ),
                "disambiguation_data": {
                    "requested_number": session_number,
                    "available_sessions": [
                        {"session_number": s["session_number"], "title": s.get("title")}
                        for s in available
                    ],
                },
            }
        target_session = resolved

    title = target_session.title or target_session.context_summary
    summary = target_session.context_summary

    if not title and not summary:
        message = "This session doesn't have a title or summary yet."
    elif title and summary and title != summary:
        message = f"Session title: '{title}'. Summary: {summary}"
    else:
        message = f"Session: '{title or summary}'."

    return {
        "action": "query_session_summary",
        "success": True,
        "message": message,
        "data": {
            "session_id": str(target_session.id),
            "title": title,
            "context_summary": summary,
            "status": target_session.status,
        },
    }


# ==================== A22: CUSTOMER COMMUNICATIONS VOICE HANDLERS (B4) ====================
# Pattern: confirm-as-turn (§16.3 arch)
#   1. Resolve customer (context → fuzzy name match → disambiguation)
#   2. Call render_communication_preview() — pure render, no writes
#   3. Write pending_confirmation to session.context_window_json
#   4. Return preview text as the spoken response
#
# On the NEXT turn, execute_action() reads pending_confirmation and
# calls the send endpoint with the same parameters.


def _resolve_customer_for_voice(
    entities: dict,
    current_user: "AuthenticatedUser | TestUserContext",
    db: Session,
    session: ConversationSession,
) -> "Customer | None | dict":
    """
    Customer resolution priority chain (A22 / D.5):
      1. context_window_json.active_customer_id — customer already in session context
      2. Named in utterance → fuzzy ilike match on Customer.display_name
      3. Multiple matches → disambiguation dict returned (not a Customer)
      4. No name and no context → clarification dict returned

    Returns:
      - Customer object on success
      - dict with 'clarification_needed': True on ambiguity/no-name
    """
    tenant_id = current_user.tenant_id

    # Tier 1: session context
    ctx = ContextWindowSchema.from_jsonb(session.context_window_json)
    if ctx.active_customer_id:
        customer = db.exec(
            select(Customer)
            .where(Customer.id == ctx.active_customer_id)
            .where(Customer.tenant_id == tenant_id)
        ).first()
        if customer:
            return customer

    # Tier 2: name in entities
    customer_name = entities.get("customer_name") or entities.get("customer")
    if not customer_name:
        return {
            "clarification_needed": True,
            "action": "tell_customer",
            "success": False,
            "message": "Who would you like to message? Please say the customer's name.",
            "next_prompts": [
                "Tell Johnson I'm 20 out",
                "Tell the Davis customer I arrived",
            ],
        }

    matches = db.exec(
        select(Customer)
        .where(Customer.tenant_id == tenant_id)
        .where(Customer.display_name.ilike(f"%{customer_name}%"))
        .where(Customer.is_active == True)
    ).all()

    if len(matches) == 0:
        return {
            "clarification_needed": True,
            "action": "tell_customer",
            "success": False,
            "message": f"No customer found matching '{customer_name}'. Check the spelling or try a different name.",
            "next_prompts": ["List customers", "Create customer"],
        }

    if len(matches) > 1:
        names = ", ".join(c.display_name for c in matches[:3])
        return {
            "clarification_needed": True,
            "action": "tell_customer",
            "success": False,
            "message": f"Multiple customers match '{customer_name}': {names}. Which one?",
            "next_prompts": [f"Tell {c.display_name}" for c in matches[:3]],
        }

    return matches[0]


def _build_comms_pending_confirmation(
    intent_type: str,
    customer: "Customer",
    template_code: str,
    variables: dict,
    preview_text: str,
    actual_channel: str,
) -> dict:
    """Build the pending_confirmation payload for confirm-as-turn gate (§16.3)."""
    return {
        "intent_type": intent_type,
        "entities": {
            "customer_id": str(customer.id),
            "template_code": template_code,
            **variables,
        },
        "preview_text": preview_text,
        "actual_channel": actual_channel,
        "summary_prompt": (
            f"Ready to send to {customer.display_name} via {actual_channel.upper()}: "
            f"'{preview_text[:80]}{'...' if len(preview_text) > 80 else ''}' — confirm?"
        ),
        "expires_at": (
            datetime.now(UTC).replace(second=0, microsecond=0).isoformat() + "Z"
        ),
    }


async def tell_customer_via_voice(
    entities: dict,
    current_user: "AuthenticatedUser | TestUserContext",
    db: Session,
    session: ConversationSession,
) -> dict[str, Any]:
    """
    A22: 'Tell Johnson I'm 20 out' → on_my_way template.

    Handles: on_my_way, parts_delay, confirm_appointment (sub-entity routing).
    Confirm-as-turn gate: renders preview, writes pending_confirmation, returns
    preview as spoken response.
    """
    from services.customer_comms_service import render_communication_preview

    result = _resolve_customer_for_voice(entities, current_user, db, session)
    if isinstance(result, dict):
        return result  # clarification or disambiguation response
    customer = result

    # Sub-entity routing: default to on_my_way unless entities say otherwise
    template_code = entities.get("template_code", "on_my_way")
    variables = {
        k: v
        for k, v in entities.items()
        if k in ("eta", "minutes_late", "date_time", "site_address") and v
    }

    try:
        preview = render_communication_preview(
            db=db,
            tenant_id=current_user.tenant_id,
            customer_id=customer.id,
            template_code=template_code,
            variables=variables,
            sender_name=getattr(current_user, "display_name", None),
        )
    except ValueError as e:
        return {
            "action": "tell_customer",
            "success": False,
            "message": str(e),
            "next_prompts": ["Update customer phone", "Use email instead"],
        }

    pending = _build_comms_pending_confirmation(
        "tell_customer",
        customer,
        template_code,
        variables,
        preview.rendered_body,
        preview.actual_channel,
    )

    ctx = ContextWindowSchema.from_jsonb(session.context_window_json)
    ctx.active_customer_id = str(customer.id)
    ctx.last_action = "tell_customer"
    ctx.timestamp = datetime.now(UTC).isoformat()
    ctx_dict = ctx.to_jsonb()
    ctx_dict["pending_confirmation"] = pending
    session.context_window_json = ctx_dict
    db.add(session)
    db.commit()

    return {
        "action": "tell_customer",
        "success": True,
        "pending_confirmation": True,
        "message": pending["summary_prompt"],
        "preview_text": preview.rendered_body,
        "actual_channel": preview.actual_channel,
        "recipient": customer.display_name,
        "next_prompts": ["Yes, send it", "Cancel", "Change to email"],
    }


async def tell_customer_running_late_via_voice(
    entities: dict,
    current_user: "AuthenticatedUser | TestUserContext",
    db: Session,
    session: ConversationSession,
) -> dict[str, Any]:
    """
    A22: 'Tell Davis I'm running 30 minutes late' → running_late template.
    """
    from services.customer_comms_service import render_communication_preview

    result = _resolve_customer_for_voice(entities, current_user, db, session)
    if isinstance(result, dict):
        return result
    customer = result

    minutes_late = str(entities.get("minutes_late", "")) or "a few"
    variables = {"minutes_late": minutes_late}

    try:
        preview = render_communication_preview(
            db=db,
            tenant_id=current_user.tenant_id,
            customer_id=customer.id,
            template_code="running_late",
            variables=variables,
            sender_name=getattr(current_user, "display_name", None),
        )
    except ValueError as e:
        return {
            "action": "tell_customer_running_late",
            "success": False,
            "message": str(e),
            "next_prompts": ["Update customer phone"],
        }

    pending = _build_comms_pending_confirmation(
        "tell_customer_running_late",
        customer,
        "running_late",
        variables,
        preview.rendered_body,
        preview.actual_channel,
    )

    ctx = ContextWindowSchema.from_jsonb(session.context_window_json)
    ctx.active_customer_id = str(customer.id)
    ctx.last_action = "tell_customer_running_late"
    ctx.timestamp = datetime.now(UTC).isoformat()
    ctx_dict = ctx.to_jsonb()
    ctx_dict["pending_confirmation"] = pending
    session.context_window_json = ctx_dict
    db.add(session)
    db.commit()

    return {
        "action": "tell_customer_running_late",
        "success": True,
        "pending_confirmation": True,
        "message": pending["summary_prompt"],
        "preview_text": preview.rendered_body,
        "actual_channel": preview.actual_channel,
        "recipient": customer.display_name,
        "next_prompts": ["Yes, send it", "Cancel"],
    }


async def tell_customer_arrived_via_voice(
    entities: dict,
    current_user: "AuthenticatedUser | TestUserContext",
    db: Session,
    session: ConversationSession,
) -> dict[str, Any]:
    """
    A22: 'I just arrived', 'I'm here' → arrived template.
    Customer resolved from session context (active job customer) or name in entities.
    """
    from services.customer_comms_service import render_communication_preview

    result = _resolve_customer_for_voice(entities, current_user, db, session)
    if isinstance(result, dict):
        return result
    customer = result

    try:
        preview = render_communication_preview(
            db=db,
            tenant_id=current_user.tenant_id,
            customer_id=customer.id,
            template_code="arrived",
            variables={},
            sender_name=getattr(current_user, "display_name", None),
        )
    except ValueError as e:
        return {
            "action": "tell_customer_arrived",
            "success": False,
            "message": str(e),
            "next_prompts": ["Update customer phone"],
        }

    pending = _build_comms_pending_confirmation(
        "tell_customer_arrived",
        customer,
        "arrived",
        {},
        preview.rendered_body,
        preview.actual_channel,
    )

    ctx = ContextWindowSchema.from_jsonb(session.context_window_json)
    ctx.active_customer_id = str(customer.id)
    ctx.last_action = "tell_customer_arrived"
    ctx.timestamp = datetime.now(UTC).isoformat()
    ctx_dict = ctx.to_jsonb()
    ctx_dict["pending_confirmation"] = pending
    session.context_window_json = ctx_dict
    db.add(session)
    db.commit()

    return {
        "action": "tell_customer_arrived",
        "success": True,
        "pending_confirmation": True,
        "message": pending["summary_prompt"],
        "preview_text": preview.rendered_body,
        "actual_channel": preview.actual_channel,
        "recipient": customer.display_name,
        "next_prompts": ["Yes, send it", "Cancel"],
    }


async def tell_customer_completed_via_voice(
    entities: dict,
    current_user: "AuthenticatedUser | TestUserContext",
    db: Session,
    session: ConversationSession,
) -> dict[str, Any]:
    """
    A22: 'The job's done', 'All finished' → job_complete template.
    """
    from services.customer_comms_service import render_communication_preview

    result = _resolve_customer_for_voice(entities, current_user, db, session)
    if isinstance(result, dict):
        return result
    customer = result

    try:
        preview = render_communication_preview(
            db=db,
            tenant_id=current_user.tenant_id,
            customer_id=customer.id,
            template_code="job_complete",
            variables={},
            sender_name=getattr(current_user, "display_name", None),
        )
    except ValueError as e:
        return {
            "action": "tell_customer_completed",
            "success": False,
            "message": str(e),
            "next_prompts": ["Update customer phone"],
        }

    pending = _build_comms_pending_confirmation(
        "tell_customer_completed",
        customer,
        "job_complete",
        {},
        preview.rendered_body,
        preview.actual_channel,
    )

    ctx = ContextWindowSchema.from_jsonb(session.context_window_json)
    ctx.active_customer_id = str(customer.id)
    ctx.last_action = "tell_customer_completed"
    ctx.timestamp = datetime.now(UTC).isoformat()
    ctx_dict = ctx.to_jsonb()
    ctx_dict["pending_confirmation"] = pending
    session.context_window_json = ctx_dict
    db.add(session)
    db.commit()

    return {
        "action": "tell_customer_completed",
        "success": True,
        "pending_confirmation": True,
        "message": pending["summary_prompt"],
        "preview_text": preview.rendered_body,
        "actual_channel": preview.actual_channel,
        "recipient": customer.display_name,
        "next_prompts": ["Yes, send it", "Cancel"],
    }


# ==================== A36: CALENDAR CONFLICT RESOLUTION VOICE INTENTS ====================


async def list_pending_calendar_conflicts_via_voice(
    entities: dict,
    current_user: AuthenticatedUser | TestUserContext,
    db: Session,
    session: ConversationSession,
) -> dict:
    """
    A36: 'list_pending_calendar_conflicts' intent handler — read-only.

    AI announces count + urgency summary. No confirm-as-turn needed
    (read-only operation).

    Example response message:
      "You have 3 pending calendar conflicts. The most urgent is the Johnson
       panel upgrade on May 10th — both Pilot and Google Calendar changed it."
    """
    from sqlalchemy import desc as _sa_desc

    from app.models.scheduling import CalendarSyncConflict
    from services.calendar_conflict_service import CalendarConflictService

    # Count and fetch top pending conflict
    count = CalendarConflictService.get_pending_conflicts_count(
        db, current_user.tenant_id
    )

    if count == 0:
        return {
            "action": "list_pending_calendar_conflicts",
            "success": True,
            "message": "You have no pending calendar conflicts.",
            "data": {"pending_count": 0},
        }

    # Fetch most urgent (lowest urgency_score, else most recent)
    top_conflict = db.exec(
        select(CalendarSyncConflict)
        .where(
            CalendarSyncConflict.tenant_id == current_user.tenant_id,
            CalendarSyncConflict.resolution.is_(None),  # type: ignore[union-attr]
        )
        .order_by(
            CalendarSyncConflict.urgency_score.asc().nullslast(),  # type: ignore[union-attr]
            _sa_desc(CalendarSyncConflict.created_at),
        )
        .limit(1)
    ).first()

    # Build spoken summary from top conflict
    job_title = "unknown job"
    if top_conflict:
        snapshot = top_conflict.local_snapshot or {}
        job_title = (
            snapshot.get("title")
            or snapshot.get("summary")
            or f"job {str(top_conflict.job_id)[:8]}"
        )

    if count == 1:
        message = (
            f"You have 1 pending calendar conflict. "
            f"It involves {job_title}. "
            f"Open the conflicts list to review it."
        )
    else:
        message = (
            f"You have {count} pending calendar conflicts. "
            f"The most urgent involves {job_title}. "
            f"Open the conflicts list to review them."
        )

    return {
        "action": "list_pending_calendar_conflicts",
        "success": True,
        "message": message,
        "data": {
            "pending_count": count,
            "top_conflict_id": str(top_conflict.id) if top_conflict else None,
        },
    }


async def resolve_calendar_conflict_via_voice(
    entities: dict,
    current_user: AuthenticatedUser | TestUserContext,
    db: Session,
    session: ConversationSession,
) -> dict:
    """
    A36: 'resolve_calendar_conflict' intent handler.

    Implements confirm-as-turn pattern (§16.3) matching delete_session_via_voice().

    Turn 1: identifier match → write pending_confirmation → return spoken summary
            with requires_confirmation=True.
    Turn 2: affirmative detected → call resolve logic with staleness check (A33)
            → 409 branch: announce change + push deep link → clear pending_confirmation.

    Refusal-with-redirect for:
      - Deletion conflicts (conflict_type in {'deleted_modified','modified_deleted'})
      - Multi-resolve attempts ("resolve all")
      - Field-level edits ("change the time to 3pm")
    """
    from app.models.scheduling import CalendarSyncConflict
    from services.calendar_conflict_service import CalendarConflictService

    ctx_dict = session.context_window_json or {}
    if not isinstance(ctx_dict, dict):
        ctx_dict = {}

    # ---- Turn 2: Confirmation turn ----
    pending = ctx_dict.get("pending_confirmation", {})
    if (
        pending.get("action") == "resolve_calendar_conflict"
        and pending.get("conflict_id")
        and pending.get("resolution")
    ):
        conflict_id_str = pending["conflict_id"]
        resolution = pending["resolution"]
        expected_pilot_at_str = pending.get("expected_pilot_modified_at")
        expected_external_at_str = pending.get("expected_external_modified_at")

        # Clear pending confirmation
        ctx_dict.pop("pending_confirmation", None)
        session.context_window_json = ctx_dict
        db.add(session)
        db.flush()

        conflict = db.exec(
            select(CalendarSyncConflict).where(
                CalendarSyncConflict.id == conflict_id_str,
                CalendarSyncConflict.tenant_id == current_user.tenant_id,
            )
        ).first()

        if not conflict:
            db.commit()
            return {
                "action": "resolve_calendar_conflict",
                "success": False,
                "message": "I couldn't find that conflict. It may have already been resolved.",
            }

        # A33 staleness check
        if expected_pilot_at_str and expected_external_at_str:
            from datetime import UTC as _UTC
            from datetime import datetime

            expected_pilot = datetime.fromisoformat(expected_pilot_at_str)
            expected_external = datetime.fromisoformat(expected_external_at_str)

            if CalendarConflictService.check_staleness(
                conflict, expected_pilot, expected_external
            ):
                db.commit()
                return {
                    "action": "resolve_calendar_conflict",
                    "success": False,
                    "message": (
                        "The conflict has changed since you last looked at it. "
                        "Please review the updated conflict on web before resolving."
                    ),
                    "requires_web_review": True,
                    "conflict_id": conflict_id_str,
                }

        # Apply resolution
        from datetime import UTC as _UTC
        from datetime import datetime

        from core.db import set_audit_context_sync

        set_audit_context_sync(db, current_user.id)
        conflict.resolution = resolution
        conflict.resolved_by_user_id = current_user.id
        conflict.resolved_at = datetime.now(_UTC)
        conflict.updated_by = current_user.id
        db.add(conflict)
        db.commit()

        side_label = (
            "Pilot"
            if resolution in ("accept_local", "recreate_calendar_event")
            else "Google Calendar"
        )
        return {
            "action": "resolve_calendar_conflict",
            "success": True,
            "message": f"Done. I've kept the {side_label} version of that event.",
            "data": {
                "conflict_id": conflict_id_str,
                "resolution": resolution,
            },
        }

    # ---- Turn 1: Identify conflict and resolution side ----
    resolution_side = entities.get("resolution_side", "").lower()
    conflict_id_raw = entities.get("conflict_id") or entities.get("job_title")

    # Validate intent can be voice-resolved
    conflict = None
    if conflict_id_raw:
        try:
            import uuid as _uuid

            cid = _uuid.UUID(str(conflict_id_raw))
            conflict = db.exec(
                select(CalendarSyncConflict).where(
                    CalendarSyncConflict.id == cid,
                    CalendarSyncConflict.tenant_id == current_user.tenant_id,
                    CalendarSyncConflict.resolution.is_(None),  # type: ignore[union-attr]
                )
            ).first()
        except (ValueError, AttributeError):
            pass

    # Refusal: deletion-type conflicts require web UI
    if conflict and conflict.conflict_type in ("deleted_modified", "modified_deleted"):
        return {
            "action": "resolve_calendar_conflict",
            "success": False,
            "message": (
                "That conflict involves a deleted event — I need you to handle "
                "deletion decisions on the web. I'll open the conflict for you."
            ),
            "requires_web_review": True,
            "conflict_id": str(conflict.id) if conflict else None,
        }

    # Refusal: "resolve all" not supported via voice
    if entities.get("resolve_all"):
        return {
            "action": "resolve_calendar_conflict",
            "success": False,
            "message": (
                "I can only resolve conflicts one at a time. "
                "Please specify which job's conflict you want to resolve."
            ),
        }

    # Map spoken side to resolution value
    resolution_map = {
        "pilot": "accept_local",
        "pilot version": "accept_local",
        "keep pilot": "accept_local",
        "mine": "accept_local",
        "google": "accept_remote",
        "google calendar": "accept_remote",
        "calendar": "accept_remote",
        "external": "accept_remote",
        "their version": "accept_remote",
    }
    resolution_value = resolution_map.get(resolution_side)

    if not resolution_value or not conflict:
        pending_count = CalendarConflictService.get_pending_conflicts_count(
            db, current_user.tenant_id
        )
        return {
            "action": "resolve_calendar_conflict",
            "success": False,
            "message": (
                f"To resolve a conflict, say 'Keep the Pilot version of [job name]' "
                f"or 'Keep the Google Calendar version of [job name]'. "
                f"You have {pending_count} pending conflict"
                f"{'s' if pending_count != 1 else ''}."
            ),
            "needs_clarification": True,
            "pending_count": pending_count,
        }

    # Build spoken confirmation prompt
    from datetime import UTC as _UTC
    from datetime import datetime

    field_diffs = CalendarConflictService.compute_field_diffs(
        conflict.local_snapshot or {},
        conflict.remote_snapshot or {},
        conflict.base_snapshot,
    )
    chosen_side = "pilot" if resolution_value == "accept_local" else "external"
    summary_prompt = CalendarConflictService.build_voice_readback_summary(
        conflict, field_diffs, chosen_side
    )

    # Write pending confirmation (confirm-as-turn pattern §16.3)
    ctx_dict["pending_confirmation"] = {
        "action": "resolve_calendar_conflict",
        "conflict_id": str(conflict.id),
        "resolution": resolution_value,
        "expected_pilot_modified_at": conflict.pilot_modified_at.isoformat(),
        "expected_external_modified_at": conflict.external_modified_at.isoformat(),
        "summary_prompt": summary_prompt,
    }
    session.context_window_json = ctx_dict
    db.add(session)
    db.commit()

    return {
        "action": "resolve_calendar_conflict",
        "success": True,
        "requires_confirmation": True,
        "message": summary_prompt,
        "data": {
            "conflict_id": str(conflict.id),
            "resolution": resolution_value,
        },
    }


async def list_pending_qb_conflicts_via_voice(
    entities: dict,
    current_user: "AuthenticatedUser | TestUserContext",
    db: "Session",
    session: "ConversationSession",
) -> dict:
    """
    B8/A50: 'list_pending_qb_conflicts' intent handler — read-only status query.

    Per §F.5 design decision: AI explicitly refuses resolve attempts with redirect copy.
    Returns pending count + oldest conflict date; never attempts resolution.

    Example response:
      "You have 5 pending QuickBooks conflicts. The oldest is 12 days old.
       QuickBooks conflicts require manual review on the web."
    """
    from sqlalchemy import func as _func

    from app.models.system import AppService, IntegrationSyncConflict

    # Check if user is trying to resolve — explicitly refuse
    action_hint = (entities or {}).get("action", "").lower()
    if "resolve" in action_hint or "fix" in action_hint or "accept" in action_hint:
        return {
            "action": "list_pending_qb_conflicts",
            "success": True,
            "message": (
                "QuickBooks conflicts require manual review on the web. "
                "You can view and resolve them in the QuickBooks Conflicts section. "
                "I can only tell you how many pending conflicts you have."
            ),
            "data": {"redirected": True},
        }

    # Count pending QB conflicts
    count_stmt = (
        select(_func.count())
        .select_from(IntegrationSyncConflict)
        .join(AppService, IntegrationSyncConflict.app_service_id == AppService.id)
        .where(
            IntegrationSyncConflict.tenant_id == current_user.tenant_id,
            AppService.provider_code == "quickbooks",
            IntegrationSyncConflict.status == "pending",
        )
    )
    count = db.exec(count_stmt).one()

    if count == 0:
        return {
            "action": "list_pending_qb_conflicts",
            "success": True,
            "message": "You have no pending QuickBooks conflicts.",
            "data": {"pending_count": 0},
        }

    # Find oldest conflict date
    oldest_stmt = (
        select(IntegrationSyncConflict.created_at)
        .join(AppService, IntegrationSyncConflict.app_service_id == AppService.id)
        .where(
            IntegrationSyncConflict.tenant_id == current_user.tenant_id,
            AppService.provider_code == "quickbooks",
            IntegrationSyncConflict.status == "pending",
        )
        .order_by(IntegrationSyncConflict.created_at.asc())
        .limit(1)
    )
    oldest_row = db.exec(oldest_stmt).first()

    oldest_days = None
    if oldest_row:
        from datetime import UTC, datetime

        delta = (
            datetime.now(UTC) - oldest_row.replace(tzinfo=UTC)
            if oldest_row.tzinfo is None
            else datetime.now(UTC) - oldest_row
        )
        oldest_days = delta.days

    if count == 1:
        oldest_msg = (
            f" It is {oldest_days} days old." if oldest_days is not None else ""
        )
        message = (
            f"You have 1 pending QuickBooks conflict.{oldest_msg} "
            "QuickBooks conflicts require manual review on the web."
        )
    else:
        oldest_msg = (
            f" The oldest is {oldest_days} days old." if oldest_days is not None else ""
        )
        message = (
            f"You have {count} pending QuickBooks conflicts.{oldest_msg} "
            "QuickBooks conflicts require manual review on the web."
        )

    return {
        "action": "list_pending_qb_conflicts",
        "success": True,
        "message": message,
        "data": {
            "pending_count": count,
            "oldest_conflict_days": oldest_days,
        },
    }


# ==================== B11/A63: VOICE-TO-TEXT SMS REPLY ====================


async def reply_to_customer_sms_via_voice(
    params: dict,
    context,
    db,
    current_user,
) -> dict:
    """
    B11/A63: Voice-to-text SMS reply intent handler.
    Pattern: §6.6 Confirm-as-Turn — one-way-door action (SMS cannot be recalled).

    Turn 1: preview → store pending_confirmation, return requires_confirmation=True
    Turn 2: execute on confirmed "yes" → call A62 reply service
    """
    ctx_dict = (
        context if isinstance(context, dict) else getattr(context, "__dict__", {})
    )

    # Turn 2: execute confirmed send
    pending = ctx_dict.get("pending_confirmation", {})
    if pending and pending.get("action") == "reply_to_customer_sms":
        thread_id = pending.get("thread_id")
        body = pending.get("body")
        if not thread_id or not body:
            return {
                "action": "reply_to_customer_sms",
                "success": False,
                "message": "Missing thread or message body for SMS reply.",
            }
        try:
            import uuid as _uuid

            from api.routes.communications_threads import ReplyRequest, _send_reply_impl

            reply_req = ReplyRequest(body=body, composition_method="free_form_voice")
            result = _send_reply_impl(
                thread_id=_uuid.UUID(str(thread_id)),
                payload=reply_req,
                db=db,
                user_context=current_user,
            )
            ctx_dict.pop("pending_confirmation", None)
            return {
                "action": "reply_to_customer_sms",
                "success": True,
                "message": f"Message sent! Segments used: {result.segment_count}.",
                "message_id": str(result.message_id),
                "status": result.status,
            }
        except Exception as exc:
            return {
                "action": "reply_to_customer_sms",
                "success": False,
                "message": f"Failed to send SMS: {exc}",
            }

    # Turn 1: preview
    thread_id = params.get("thread_id")
    body = params.get("body", "").strip()
    customer_name = params.get("customer_name", "the customer")

    if not body:
        return {
            "action": "reply_to_customer_sms",
            "success": False,
            "message": "What would you like to say? Please provide the message body.",
            "requires_confirmation": False,
        }

    segment_count = max(1, (len(body) + 159) // 160)
    preview_text = (
        f"I'll send to {customer_name}: '{body}'. "
        f"That's {segment_count} segment(s). Confirm?"
    )
    ctx_dict["pending_confirmation"] = {
        "action": "reply_to_customer_sms",
        "thread_id": str(thread_id) if thread_id else None,
        "body": body,
        "customer_name": customer_name,
    }
    return {
        "action": "reply_to_customer_sms",
        "success": True,
        "requires_confirmation": True,
        "preview": preview_text,
        "message": preview_text,
        "pending": {
            "thread_id": str(thread_id) if thread_id else None,
            "body": body,
            "segment_count": segment_count,
        },
    }


# ==================== B20/FIND-111: Help System Voice Intents ====================


async def open_help_via_voice(
    entities: dict,
    current_user: AuthenticatedUser | TestUserContext,
    db: Session,
    session: ConversationSession,
) -> dict:
    """
    Handle: "Open help" or "I need help"

    Creates a new HelpChatSession and stores its ID in the conversation context.

    Returns:
        Success response with greeting message
    """
    now_utc = datetime.now(UTC)

    # Create a new help chat session
    help_session = HelpChatSession(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        started_at=now_utc,
        last_activity_at=now_utc,
        message_count=0,
        created_at=now_utc,
        updated_at=now_utc,
    )
    db.add(help_session)
    db.flush()

    # Update conversation context with active help session ID
    ctx_dict = session.context_window_json or {}
    ctx_dict["active_help_session_id"] = str(help_session.id)
    ctx_dict["timestamp"] = datetime.now(UTC).isoformat()
    session.context_window_json = ctx_dict
    db.add(session)
    db.commit()

    # Write voice command entity link (FIND-168 convention)
    if hasattr(session, "voice_command_log_id") and session.voice_command_log_id:
        from app.models.voice_helpers import _link_voice_to_entity

        link = _link_voice_to_entity(
            db=db,
            tenant_id=current_user.tenant_id,
            voice_command_log_id=session.voice_command_log_id,
            entity_type="help_chat_session",
            entity_id=help_session.id,
            action="opened_via_voice",
            created_by=current_user.id,
        )
        db.add(link)
        db.commit()

    return {
        "action": "open_help",
        "success": True,
        "message": "Help is open. What do you need help with?",
        "data": {
            "help_session_id": str(help_session.id),
        },
        "next_prompts": [
            "How do I wire a 3-way switch?",
            "What's the NEC requirement for grounding?",
        ],
    }


async def ask_help_question_via_voice(
    entities: dict,
    current_user: AuthenticatedUser | TestUserContext,
    db: Session,
    session: ConversationSession,
) -> dict:
    """
    Handle: "How do I wire a 3-way switch?" or "What's the NEC requirement for grounding?"

    Routes the question to the existing help chat endpoint via _chat_impl.
    Gracefully creates a help session if none is open.

    Returns:
        RAG response with retrieved article chunks
    """
    from api.routes.help import _chat_impl
    from api.schemas.help import HelpChatRequest
    from app.models.voice_helpers import _link_voice_to_entity

    question = entities.get("question") or ""

    if not question:
        return {
            "action": "ask_help_question",
            "success": False,
            "error": "Missing question",
            "message": "Please ask a question. What do you need help with?",
            "next_prompts": ["Try rephrasing"],
        }

    # Resolve active help session from context, or create one
    ctx_dict = session.context_window_json or {}
    active_help_session_id = ctx_dict.get("active_help_session_id")

    help_session = None
    if active_help_session_id:
        try:
            help_session = db.exec(
                select(HelpChatSession)
                .where(HelpChatSession.id == UUID(active_help_session_id))
                .where(HelpChatSession.tenant_id == current_user.tenant_id)
                .where(HelpChatSession.user_id == current_user.id)
                .where(HelpChatSession.anonymized_at == None)
            ).first()
        except (ValueError, TypeError):
            help_session = None

    # Graceful degradation: auto-create session if needed
    if not help_session:
        now_utc = datetime.now(UTC)
        help_session = HelpChatSession(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            started_at=now_utc,
            last_activity_at=now_utc,
            message_count=0,
            created_at=now_utc,
            updated_at=now_utc,
        )
        db.add(help_session)
        db.flush()

        # Update context with new session
        ctx_dict["active_help_session_id"] = str(help_session.id)
        ctx_dict["timestamp"] = datetime.now(UTC).isoformat()
        session.context_window_json = ctx_dict
        db.add(session)
        db.commit()

    # Resolve user role (tech or owner)
    user_role = current_user.role if hasattr(current_user, "role") else "technician"

    # Route to existing _chat_impl
    help_request = HelpChatRequest(
        session_id=help_session.id,
        message=question,
    )

    try:
        response = _chat_impl(
            data=help_request,
            db=db,
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            user_role=user_role,
        )

        # Write voice command entity link for the question
        if hasattr(session, "voice_command_log_id") and session.voice_command_log_id:
            # Get the most recent message (assistant response)
            message = db.exec(
                select(HelpChatMessage)
                .where(HelpChatMessage.session_id == help_session.id)
                .where(HelpChatMessage.role == "assistant")
                .order_by(HelpChatMessage.created_at.desc())
            ).first()

            if message:
                link = _link_voice_to_entity(
                    db=db,
                    tenant_id=current_user.tenant_id,
                    voice_command_log_id=session.voice_command_log_id,
                    entity_type="help_chat_message",
                    entity_id=message.message_id,
                    action="asked_via_voice",
                    created_by=current_user.id,
                )
                db.add(link)
                db.commit()

        return {
            "action": "ask_help_question",
            "success": True,
            "message": response.content,
            "data": {
                "help_session_id": str(help_session.id),
                "retrieved_article_ids": response.retrieved_article_ids,
            },
            "next_prompts": [
                "Tell me more",
                "How else can I use this?",
            ],
        }
    except Exception as e:
        logger.error(f"Error in ask_help_question_via_voice: {e!s}")
        return {
            "action": "ask_help_question",
            "success": False,
            "error": "Help system error",
            "message": "I couldn't retrieve help information. Try rephrasing?",
            "data": {
                "help_session_id": str(help_session.id) if help_session else None,
            },
            "next_prompts": ["Try another question"],
        }


# ==================== HANDLER 16: UPDATE JOB STATUS ====================


async def update_job_status_via_voice(
    entities: dict,
    current_user: AuthenticatedUser | TestUserContext,
    db: Session,
    session: ConversationSession,
) -> dict:
    """
    Handle: "Mark this job as in progress" / "Complete the Johnson job"

    Entities:
        - job_status: "in_progress", "completed", etc.

    Behavior:
        1. Read active_job_id from context window
        2. Fetch job, verify tenant scope
        3. Call job_service.transition_job_status()
        4. Write VoiceCommandEntityLink row with entity_type='job', action='status_updated'
        5. Return success response
    """
    context = session.context_window_json or {}
    active_job_id = context.get("active_job_id")

    if not active_job_id:
        return {
            "action": "update_job_status",
            "success": False,
            "error": "No active job",
            "message": "Which job status do you want to update? Please set an active job first.",
        }

    target_status = entities.get("job_status", "").lower()
    if not target_status:
        return {
            "action": "update_job_status",
            "success": False,
            "error": "Missing status",
            "message": "What status do you want to set? Say 'in progress' or 'completed'.",
        }

    # Fetch job (tenant-scoped)
    job = db.exec(
        select(Job)
        .where(Job.id == UUID(active_job_id))
        .where(Job.tenant_id == current_user.tenant_id)
    ).first()

    if not job:
        return {
            "action": "update_job_status",
            "success": False,
            "error": "Job not found",
            "message": "I couldn't find the active job. Please check your job selection.",
        }

    # Map spoken status to valid codes
    status_map = {
        "scheduled": "scheduled",
        "in progress": "in_progress",
        "in_progress": "in_progress",
        "completed": "completed",
        "complete": "completed",
        "done": "completed",
        "cancelled": "cancelled",
        "cancel": "cancelled",
    }

    new_status = status_map.get(target_status)
    if not new_status:
        return {
            "action": "update_job_status",
            "success": False,
            "error": "Invalid status",
            "message": f"I don't recognize '{target_status}'. Try 'scheduled', 'in progress', 'completed', or 'cancelled'.",
        }

    # Update job status
    from core.db import set_audit_context_sync

    set_audit_context_sync(db, current_user.id)
    job.status = new_status
    job.updated_by = current_user.id
    db.add(job)
    db.commit()

    # Write VoiceCommandEntityLink
    if hasattr(session, "voice_command_log_id") and session.voice_command_log_id:
        from app.models.voice_helpers import _link_voice_to_entity

        link = _link_voice_to_entity(
            db=db,
            tenant_id=current_user.tenant_id,
            voice_command_log_id=session.voice_command_log_id,
            entity_type="job",
            entity_id=job.id,
            action="status_updated",
            created_by=current_user.id,
        )
        db.add(link)
        db.commit()

    return {
        "action": "update_job_status",
        "success": True,
        "message": f"Updated job status to {new_status}.",
        "data": {
            "job_id": str(job.id),
            "new_status": new_status,
        },
        "next_prompts": ["Show job details", "Clock out"],
    }


# ==================== HANDLER 17: QUERY JOB ETC STATUS ====================


async def query_job_etc_status_via_voice(
    entities: dict,
    current_user: AuthenticatedUser | TestUserContext,
    db: Session,
    session: ConversationSession,
) -> dict:
    """
    Handle: "How much time do we have left?" / "What's the ETC status?"

    Entities: (none required — job_id read from context window)

    Behavior:
        1. Read active_job_id from context window
        2. Fetch job; return hours_estimated
        3. Sum job_time_entry.hours for this job
        4. Compute hours_remaining = hours_estimated - hours_logged
        5. Return read-only response; no link row
    """
    context = session.context_window_json or {}
    active_job_id = context.get("active_job_id")

    if not active_job_id:
        return {
            "action": "query_job_etc_status",
            "success": False,
            "error": "No active job",
            "message": "Which job's ETC status do you want to know? Please set an active job first.",
        }

    # Fetch job (tenant-scoped)
    job = db.exec(
        select(Job)
        .where(Job.id == UUID(active_job_id))
        .where(Job.tenant_id == current_user.tenant_id)
    ).first()

    if not job:
        return {
            "action": "query_job_etc_status",
            "success": False,
            "error": "Job not found",
            "message": "I couldn't find the active job.",
        }

    # Sum hours logged
    from sqlalchemy import func as sql_func

    from app.models.fulfillment import JobTimeEntry

    hours_logged_result = db.exec(
        select(sql_func.sum(JobTimeEntry.hours))
        .where(JobTimeEntry.job_id == job.id)
        .where(JobTimeEntry.tenant_id == current_user.tenant_id)
    ).first()

    hours_logged = float(hours_logged_result or 0)
    hours_estimated = float(job.hours_estimated or 0)
    hours_remaining = max(0, hours_estimated - hours_logged)

    status_msg = ""
    if hours_remaining <= 0:
        status_msg = "You've completed the estimated time."
    elif hours_remaining <= 1:
        status_msg = f"About {hours_remaining:.1f} hour remaining."
    else:
        status_msg = f"About {hours_remaining:.1f} hours remaining."

    return {
        "action": "query_job_etc_status",
        "success": True,
        "message": status_msg,
        "data": {
            "job_id": str(job.id),
            "hours_estimated": round(hours_estimated, 2),
            "hours_logged": round(hours_logged, 2),
            "hours_remaining": round(hours_remaining, 2),
        },
        "next_prompts": ["Log more time", "Clock out", "Show job details"],
    }


# ==================== HANDLER 18: SWITCH SESSION ====================


async def switch_session_via_voice(
    entities: dict,
    current_user: AuthenticatedUser | TestUserContext,
    db: Session,
    session: ConversationSession,
) -> dict:
    """
    Handle: "Switch to session 2" / "Go back to my previous session"

    Entities:
        - session_number: int (position in numbered list, 1-indexed)
        - session_name: Optional[str] (session label)

    Behavior:
        1. Query all ConversationSession rows for current user (ordered by created_at)
        2. Resolve session by number (1-indexed) or name match
        3. Update context_window_json["active_session_id"] = target_session.id
        4. Return success response; no link row (read-only context change)
    """
    context = session.context_window_json or {}
    session_number = entities.get("session_number")
    session_name = entities.get("session_name")

    if not session_number and not session_name:
        return {
            "action": "switch_session",
            "success": False,
            "error": "Missing target",
            "message": "Which session do you want to switch to? Say 'session 1' or 'session 2'.",
        }

    # Query all sessions for this user (ordered by creation)
    sessions = db.exec(
        select(ConversationSession)
        .where(ConversationSession.tenant_id == current_user.tenant_id)
        .where(ConversationSession.user_id == current_user.id)
        .order_by(ConversationSession.created_at.asc())
    ).all()

    if not sessions:
        return {
            "action": "switch_session",
            "success": False,
            "error": "No sessions found",
            "message": "You have no conversation sessions to switch to.",
        }

    target_session = None

    # Match by session number (1-indexed)
    if session_number:
        try:
            idx = int(session_number) - 1
            if 0 <= idx < len(sessions):
                target_session = sessions[idx]
        except (ValueError, TypeError):
            pass

    # Match by session name
    if not target_session and session_name:
        session_name_lower = session_name.lower()
        for s in sessions:
            if s.session_name and session_name_lower in s.session_name.lower():
                target_session = s
                break

    if not target_session:
        return {
            "action": "switch_session",
            "success": False,
            "error": "Session not found",
            "message": f"I couldn't find session {session_number or session_name}. You have {len(sessions)} active session{'s' if len(sessions) != 1 else ''}.",
        }

    # Update active_session_id in context
    ctx = ContextWindowSchema.from_jsonb(session.context_window_json)
    ctx.active_session_id = str(target_session.id)
    session.context_window_json = ctx.to_jsonb()
    db.add(session)
    db.commit()

    return {
        "action": "switch_session",
        "success": True,
        "message": f"Switched to {target_session.session_name or 'session'}.",
        "data": {
            "active_session_id": str(target_session.id),
            "session_name": target_session.session_name,
        },
        "next_prompts": ["Create quote", "List pending quotes"],
    }


# ==================== HANDLER 19: LIST PENDING FIELD ISSUES ====================


async def list_pending_field_issues_via_voice(
    entities: dict,
    current_user: AuthenticatedUser | TestUserContext,
    db: Session,
    session: ConversationSession,
) -> dict:
    """
    Handle: "What field issues are pending?" / "Any escalations I need to review?"

    Behavior:
        1. Query MobileSyncOwnerEscalation WHERE status='pending' AND tenant_id=current_tenant
        2. RBAC: field_issue.view (owner only) — enforced by permission check upstream
        3. Return count + brief summary of each pending escalation
        4. Read-only; no link row
    """
    from app.models.system import MobileSyncOwnerEscalation

    # Query pending escalations
    escalations = db.exec(
        select(MobileSyncOwnerEscalation)
        .where(MobileSyncOwnerEscalation.tenant_id == current_user.tenant_id)
        .where(MobileSyncOwnerEscalation.status == "pending")
        .order_by(MobileSyncOwnerEscalation.escalated_at.asc())
    ).all()

    if not escalations:
        return {
            "action": "list_pending_field_issues",
            "success": True,
            "message": "You have no pending field issues.",
            "data": {
                "pending_count": 0,
                "escalations": [],
            },
            "next_prompts": ["Create quote", "Show jobs"],
        }

    # Build brief summaries
    summaries = []
    for i, esc in enumerate(escalations, 1):
        summary = {
            "escalation_number": i,
            "escalation_id": str(esc.id),
            "reason": esc.escalation_reason or "Sync conflict",
        }
        summaries.append(summary)

    msg = f"You have {len(escalations)} pending field issue"
    msg += "s" if len(escalations) != 1 else ""
    msg += ". "
    msg += " ".join(f"Issue {i}: {s['reason']}." for i, s in enumerate(summaries, 1))

    return {
        "action": "list_pending_field_issues",
        "success": True,
        "message": msg,
        "data": {
            "pending_count": len(escalations),
            "escalations": summaries,
        },
        "next_prompts": ["Resolve escalation 1", "Resolve escalation 2"],
    }


# ==================== HANDLER 20: RESOLVE FIELD ISSUE ====================


async def resolve_field_issue_via_voice(
    entities: dict,
    current_user: AuthenticatedUser | TestUserContext,
    db: Session,
    session: ConversationSession,
) -> dict:
    """
    Handle: "Resolve escalation 3 — use the local version" / "Accept the tech's version on escalation 2"

    Entities:
        - escalation_number: int (1-indexed position in pending list)
        - resolution_action: str (use_local, use_server, etc.)

    Behavior:
        1. Confirm-as-turn pattern (§16.3):
           - Turn 1: identify escalation + resolution → write pending_confirmation → return spoken summary
           - Turn 2: affirmative → call _resolve_escalation_impl → clear pending_confirmation
        2. Write VoiceCommandEntityLink row with entity_type='mobile_sync_owner_escalation'
    """
    from api.routes.owner_escalations import (
        EscalationResolveRequest,
        _resolve_escalation_impl,
    )
    from app.models.system import MobileSyncOwnerEscalation

    ctx_dict = session.context_window_json or {}
    if not isinstance(ctx_dict, dict):
        ctx_dict = {}

    # ---- Turn 2: Confirmation turn ----
    pending = ctx_dict.get("pending_confirmation", {})
    if (
        pending.get("action") == "resolve_field_issue"
        and pending.get("escalation_id")
        and pending.get("resolution")
    ):
        escalation_id_str = pending["escalation_id"]
        resolution = pending["resolution"]

        # Clear pending confirmation
        ctx_dict.pop("pending_confirmation", None)
        session.context_window_json = ctx_dict
        db.add(session)
        db.flush()

        # Call _resolve_escalation_impl
        try:
            request = EscalationResolveRequest(resolution_action=resolution)
            _resolve_escalation_impl(
                UUID(escalation_id_str),
                request,
                db,
                current_user,
                resolution_channel="voice",
            )
        except Exception as e:
            db.commit()
            return {
                "action": "resolve_field_issue",
                "success": False,
                "message": f"Could not resolve escalation: {e!s}",
                "error": str(e),
            }

        db.commit()

        # Write VoiceCommandEntityLink
        if hasattr(session, "voice_command_log_id") and session.voice_command_log_id:
            from app.models.voice_helpers import _link_voice_to_entity

            link = _link_voice_to_entity(
                db=db,
                tenant_id=current_user.tenant_id,
                voice_command_log_id=session.voice_command_log_id,
                entity_type="mobile_sync_owner_escalation",
                entity_id=UUID(escalation_id_str),
                action="resolved_via_voice",
                created_by=current_user.id,
            )
            db.add(link)
            db.commit()

        return {
            "action": "resolve_field_issue",
            "success": True,
            "message": f"Escalation resolved with {resolution}.",
            "data": {
                "escalation_id": escalation_id_str,
                "resolution": resolution,
            },
        }

    # ---- Turn 1: Identify escalation and resolution side ----
    escalation_number = entities.get("escalation_number")
    resolution_side = entities.get("resolution_action", "").lower()

    if not escalation_number or not resolution_side:
        return {
            "action": "resolve_field_issue",
            "success": False,
            "error": "Missing parameters",
            "message": "Say 'Resolve escalation 1 — use the local version' or 'Accept the server version on escalation 2'.",
        }

    # Query pending escalations (same ordering as list_pending_field_issues)
    escalations = db.exec(
        select(MobileSyncOwnerEscalation)
        .where(MobileSyncOwnerEscalation.tenant_id == current_user.tenant_id)
        .where(MobileSyncOwnerEscalation.status == "pending")
        .order_by(MobileSyncOwnerEscalation.escalated_at.asc())
    ).all()

    if not escalations:
        return {
            "action": "resolve_field_issue",
            "success": False,
            "error": "No pending escalations",
            "message": "You have no pending field issues to resolve.",
        }

    # Resolve escalation by number (1-indexed)
    try:
        idx = int(escalation_number) - 1
        if idx < 0 or idx >= len(escalations):
            return {
                "action": "resolve_field_issue",
                "success": False,
                "error": "Invalid escalation number",
                "message": f"Escalation {escalation_number} not found. You have {len(escalations)} pending escalation{'s' if len(escalations) != 1 else ''}.",
            }
        escalation = escalations[idx]
    except (ValueError, TypeError):
        return {
            "action": "resolve_field_issue",
            "success": False,
            "error": "Invalid escalation number",
            "message": f"I didn't understand escalation number {escalation_number}.",
        }

    # Map spoken side to resolution value
    resolution_map = {
        "local": "use_local",
        "local version": "use_local",
        "tech": "use_local",
        "tech version": "use_local",
        "server": "use_server",
        "server version": "use_server",
        "pilot": "use_local",
        "pilot version": "use_local",
    }
    resolution_value = resolution_map.get(resolution_side)

    if not resolution_value:
        return {
            "action": "resolve_field_issue",
            "success": False,
            "error": "Invalid resolution",
            "message": "Say 'use the local version' or 'use the server version'.",
        }

    # Write pending confirmation (confirm-as-turn pattern)
    ctx_dict["pending_confirmation"] = {
        "action": "resolve_field_issue",
        "escalation_id": str(escalation.id),
        "resolution": resolution_value,
    }
    session.context_window_json = ctx_dict
    db.add(session)
    db.commit()

    return {
        "action": "resolve_field_issue",
        "success": True,
        "requires_confirmation": True,
        "message": f"Confirm: resolve escalation {escalation_number} with {resolution_value}?",
        "data": {
            "escalation_id": str(escalation.id),
            "escalation_reason": escalation.escalation_reason,
            "resolution": resolution_value,
        },
    }


INTENT_HANDLERS = {
    "create_quote": create_quote_via_voice,
    "add_quote_line": add_line_via_voice,
    "query_job_profit": get_job_profitability,
    "calculate_voltage_drop": calculate_nec_voltage_drop,
    "calculate_conduit_fill": calculate_conduit_fill,
    "navigate": return_navigation_command,
    "create_customer": create_customer_via_voice,
    "create_job": create_job_via_voice,
    "log_time_entry": log_time_entry_via_voice,
    "add_expense": add_expense_via_voice,
    "send_quote": send_quote_via_voice,
    "schedule_job": schedule_job_via_voice,  # Task 1-D-3
    "reassign_job": reassign_job_via_voice,  # Task 1-D-3
    # A31: Approval workflow voice intents
    "approve_quote": approve_quote_via_voice,
    "reject_quote": reject_quote_via_voice,
    "kickback_quote": kickback_quote_via_voice,
    "list_pending_quotes": list_pending_quotes_via_voice,
    # A10: Voice session management intents (B2)
    "rename_session": rename_session_via_voice,
    "delete_session": delete_session_via_voice,
    "open_session": open_session_via_voice,
    "query_session_summary": query_session_summary_via_voice,
    # A22: Customer Communications voice intents (B4)
    "tell_customer": tell_customer_via_voice,
    "tell_customer_running_late": tell_customer_running_late_via_voice,
    "tell_customer_arrived": tell_customer_arrived_via_voice,
    "tell_customer_completed": tell_customer_completed_via_voice,
    # A36: Calendar Conflict Resolution voice intents (B6)
    "list_pending_calendar_conflicts": list_pending_calendar_conflicts_via_voice,
    "resolve_calendar_conflict": resolve_calendar_conflict_via_voice,
    # B8/A50: QB Conflict status query (read-only; explicit resolve redirect copy per §F.5)
    "list_pending_qb_conflicts": list_pending_qb_conflicts_via_voice,
    # B11/A63: Voice-to-text SMS reply (confirm-as-turn per §6.6)
    "reply_to_customer_sms": reply_to_customer_sms_via_voice,
    # B20/A90: Time tracking voice intents (clock in/out)
    "clock_in": clock_in_via_voice,
    "clock_out": clock_out_via_voice,
    # B20/A89: LOTO confirmation voice intent
    "confirm_loto": confirm_loto_via_voice,
    # B20/FIND-110: Scheduling intents (reschedule + check next)
    "reschedule_job": reschedule_job_via_voice,
    "check_next_job": check_next_job_via_voice,
    # B20/FIND-111: Help system voice intents
    "open_help": open_help_via_voice,
    "ask_help_question": ask_help_question_via_voice,
    # B20/FIND-129: Job status + ETC + session + escalation intents
    "update_job_status": update_job_status_via_voice,
    "query_job_etc_status": query_job_etc_status_via_voice,
    "switch_session": switch_session_via_voice,
    "list_pending_field_issues": list_pending_field_issues_via_voice,
    "resolve_field_issue": resolve_field_issue_via_voice,
}


# ==================== ERROR HANDLING HELPERS ====================


def _handle_unknown_intent(intent_type: str) -> dict:
    """Return error response for unknown intent."""
    return {
        "action": intent_type or "unknown",
        "success": False,
        "error": "Unknown intent",
        "message": "I didn't understand that command. Try rephrasing?",
        "next_prompts": [
            "Create quote",
            "Show jobs",
            "Show customers",
        ],
    }


def _handle_execution_error(intent_type: str, error_message: str) -> dict:
    """Return error response for execution failure."""
    return {
        "action": intent_type,
        "success": False,
        "error": "Execution failed",
        "message": f"Something went wrong: {error_message}",
        "next_prompts": [
            "Try again",
            "Show help",
        ],
    }
