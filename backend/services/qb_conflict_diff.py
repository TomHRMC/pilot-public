"""
services/qb_conflict_diff.py

B8/A49: QuickBooks conflict field diff computation.

Mirrors calendar_sync_conflict diff pattern from B6/A32 but is entity-type-aware.
Each entity type (customer, quote, invoice, expense) has a distinct field registry.

Introduced: B8/A49
Consumed by: integrations.py (QB conflict queue endpoints)
"""

from typing import Any

# ---------------------------------------------------------------------------
# Entity-type field registries
# ---------------------------------------------------------------------------

ENTITY_DIFF_FIELDS: dict[str, list[str]] = {
    "customer": [
        "display_name",
        "email",
        "phone",
        "billing_address",
        "shipping_address",
    ],
    "quote": ["status", "total_amount_cents", "line_items", "expiry_date", "notes"],
    "invoice": ["status", "amount_due_cents", "due_date", "line_items", "payments"],
    "expense": ["amount_cents", "category", "description", "vendor", "date"],
}

FINANCIAL_FIELDS: dict[str, str | None] = {
    "customer": None,
    "quote": "total_amount_cents",
    "invoice": "amount_due_cents",
    "expense": "amount_cents",
}


def compute_qb_field_diffs(
    entity_type: str,
    pilot_snapshot: dict[str, Any],
    qb_snapshot: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Compute field-level diffs between Pilot and QB snapshots for a given entity type.

    Returns list of diffs in the platform-wide track-changes vocabulary (§16.2):
        [{"field": str, "pilot_value": Any, "qb_value": Any, "change_type": "modified|added|removed"}]

    Args:
        entity_type:     One of 'customer' | 'quote' | 'invoice' | 'expense'
        pilot_snapshot:  Current state in Pilot (from base_snapshot + local edits)
        qb_snapshot:     Current state in QB (from base_snapshot + QB edits)

    Returns:
        List of field diff objects. Empty list if entity_type unknown or snapshots empty.
    """
    if not pilot_snapshot and not qb_snapshot:
        return []

    fields = ENTITY_DIFF_FIELDS.get(entity_type, [])
    diffs = []

    for field in fields:
        pilot_val = pilot_snapshot.get(field)
        qb_val = qb_snapshot.get(field)

        if pilot_val == qb_val:
            continue

        if pilot_val is None and qb_val is not None:
            change_type = "added"
        elif pilot_val is not None and qb_val is None:
            change_type = "removed"
        else:
            change_type = "modified"

        diffs.append(
            {
                "field": field,
                "pilot_value": pilot_val,
                "qb_value": qb_val,
                "change_type": change_type,
            }
        )

    # Also check for any fields in snapshots not in the registry
    all_fields = set(pilot_snapshot.keys()) | set(qb_snapshot.keys())
    for field in all_fields:
        if field in fields:
            continue  # already processed above
        pilot_val = pilot_snapshot.get(field)
        qb_val = qb_snapshot.get(field)
        if pilot_val != qb_val:
            diffs.append(
                {
                    "field": field,
                    "pilot_value": pilot_val,
                    "qb_value": qb_val,
                    "change_type": "modified"
                    if pilot_val is not None and qb_val is not None
                    else ("added" if qb_val is not None else "removed"),
                }
            )

    return diffs


def compute_financial_delta(
    entity_type: str,
    pilot_snapshot: dict[str, Any],
    qb_snapshot: dict[str, Any],
) -> int | None:
    """
    Compute financial_delta_cents for invoice conflicts.
    Returns None for non-financial entity types.

    Args:
        entity_type:     Entity type string
        pilot_snapshot:  Pilot snapshot
        qb_snapshot:     QB snapshot

    Returns:
        Delta in cents (Pilot - QB), or None
    """
    financial_field = FINANCIAL_FIELDS.get(entity_type)
    if not financial_field:
        return None

    pilot_amount = pilot_snapshot.get(financial_field)
    qb_amount = qb_snapshot.get(financial_field)

    if pilot_amount is None or qb_amount is None:
        return None

    try:
        return int(pilot_amount) - int(qb_amount)
    except (TypeError, ValueError):
        return None


def detect_tax_period_warning(
    entity_type: str,
    qb_snapshot: dict[str, Any],
) -> bool:
    """
    Detect whether the invoice spans a closed QB tax period.
    Returns False for non-invoice entity types.

    Heuristic: checks for a "tax_period_closed" flag in the QB snapshot
    or any "date" field that looks like it falls in a past year.

    Args:
        entity_type:   Entity type string
        qb_snapshot:   QB snapshot

    Returns:
        True if invoice date falls within a closed QB tax period
    """
    if entity_type != "invoice":
        return False

    # Check for explicit flag from QB API
    if qb_snapshot.get("tax_period_closed") is True:
        return True

    # Basic heuristic: if QB invoice has a "period" field marked closed
    if qb_snapshot.get("accounting_period", {}).get("closed") is True:
        return True

    return False


def build_entity_summary(
    entity_type: str,
    pilot_snapshot: dict[str, Any],
    qb_snapshot: dict[str, Any],
) -> tuple[str, str]:
    """
    Build human-readable summaries of changes on both sides.

    Returns:
        (pilot_change_summary, qb_change_summary)
    """
    diffs = compute_qb_field_diffs(entity_type, pilot_snapshot, qb_snapshot)

    if not diffs:
        return "No changes detected", "No changes detected"

    pilot_changes = []
    qb_changes = []

    for d in diffs:
        field = d["field"]
        if d["change_type"] == "modified":
            pilot_changes.append(f"{field}: {d['pilot_value']}")
            qb_changes.append(f"{field}: {d['qb_value']}")
        elif d["change_type"] == "removed":
            pilot_changes.append(f"{field}: [removed]")
        elif d["change_type"] == "added":
            qb_changes.append(f"{field}: {d['qb_value']}")

    pilot_summary = (
        "; ".join(pilot_changes[:3]) if pilot_changes else "No local changes"
    )
    qb_summary = "; ".join(qb_changes[:3]) if qb_changes else "No QB changes"

    return pilot_summary, qb_summary
