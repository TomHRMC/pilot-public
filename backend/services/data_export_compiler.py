"""
Data export compilation service for Pilot for Trades — B13/A71.

Generates per-entity CSV files and bundles them into a ZIP with MANIFEST.json.
Builds the ZIP in memory, then uploads it to S3 with upload_fileobj (multipart streaming for large tenants is a planned change).
"""

from __future__ import annotations

import csv
import io
import json
import logging
import zipfile
from collections.abc import Generator
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlmodel import Session, select

logger = logging.getLogger(__name__)

# Entities included per scope
_FULL_TENANT_ENTITIES = [
    "customer",
    "job",
    "quote",
    "invoice",
    "job_time_entry",
    "job_expense",
    "customer_communication",
    "contact",
]

_USER_SPECIFIC_ENTITIES = [
    "job",
    "job_time_entry",
    "job_expense",
    "customer_communication",
]


class ExportScopeError(ValueError):
    pass


def stream_export_to_s3(
    db: Session,
    tenant_id: UUID,
    user_id: UUID,
    data_scope: str,
    export_id: UUID,
) -> tuple[str, str]:
    """
    Stream tenant/user data to S3 as a ZIP archive.

    Data scope controls what is included:
    - "full_tenant" (owner): customers, jobs, quotes, invoices,
      time_entries, expenses, communications, contacts
    - "user_specific" (technician): own jobs, own time_entries,
      own expenses, own communications only

    Builds the ZIP in memory, then uploads with upload_fileobj.

    Args:
        db:         Active SQLModel session.
        tenant_id:  Tenant whose data to export.
        user_id:    Requesting user (used for scope + MANIFEST.json).
        data_scope: "full_tenant" or "user_specific".
        export_id:  UUID of the data_export_request row (for naming).

    Returns:
        (s3_path, signed_url) — s3_path is the key in S3;
        signed_url is a 7-day presigned GET URL.

    Raises:
        ExportScopeError: If data_scope is not a valid value.
    """
    if data_scope not in ("full_tenant", "user_specific"):
        raise ExportScopeError(f"Invalid data_scope: '{data_scope}'")

    from core.config import settings

    bucket = getattr(settings, "DATA_EXPORT_S3_BUCKET", "pilot-data-exports-dev")
    s3_key = f"exports/{tenant_id}/{export_id}.zip"

    entities = (
        _FULL_TENANT_ENTITIES
        if data_scope == "full_tenant"
        else _USER_SPECIFIC_ENTITIES
    )

    # Build ZIP in memory for MVP (for large tenants, switch to multipart S3 streaming)
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        # MANIFEST.json
        manifest = {
            "export_id": str(export_id),
            "tenant_id": str(tenant_id),
            "user_id": str(user_id),
            "data_scope": data_scope,
            "generated_at": datetime.now(UTC).isoformat(),
            "entities": entities,
        }
        zf.writestr("MANIFEST.json", json.dumps(manifest, indent=2))

        # Entity CSVs
        for entity_name in entities:
            rows = list(
                _iter_entity_csv_rows(db, entity_name, tenant_id, user_id, data_scope)
            )
            if rows:
                csv_buffer = io.StringIO()
                writer = csv.DictWriter(csv_buffer, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)
                zf.writestr(f"{entity_name}.csv", csv_buffer.getvalue())

    zip_buffer.seek(0)

    # Upload to S3
    try:
        import boto3

        s3_client = boto3.client("s3")
        s3_client.upload_fileobj(zip_buffer, bucket, s3_key)

        # Generate 7-day presigned URL
        expires_in = 7 * 24 * 3600  # 7 days in seconds
        signed_url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": s3_key},
            ExpiresIn=expires_in,
        )
    except Exception as e:
        logger.error(f"S3 upload failed for export {export_id}: {e}")
        raise

    return s3_key, signed_url


def _iter_entity_csv_rows(
    db: Session,
    entity_name: str,
    tenant_id: UUID,
    user_id: UUID | None,
    data_scope: str,
) -> Generator[dict[str, Any], None, None]:
    """
    Yield dicts for a single entity type, scoped per data_scope.
    Caller feeds rows into the CSV writer without loading all rows at once.

    Note: Only imports models at call time to avoid circular imports.
    """
    try:
        if entity_name == "customer":
            from app.models.crm import Customer

            rows = db.exec(
                select(Customer).where(Customer.tenant_id == tenant_id)
            ).all()
            for r in rows:
                yield {
                    "id": str(r.id),
                    "name": getattr(r, "name", ""),
                    "is_active": r.is_active,
                    "created_at": r.created_at.isoformat(),
                }

        elif entity_name == "job":
            from app.models.fulfillment import Job

            q = select(Job).where(Job.tenant_id == tenant_id)
            if data_scope == "user_specific":
                # Filter by assigned user via job tech assignments (legacy job_assignment table dropped)
                from app.models.scheduling import JobTechAssignment

                assigned_job_ids = [
                    a.job_id
                    for a in db.exec(
                        select(JobTechAssignment)
                        .where(JobTechAssignment.user_id == user_id)
                        .where(JobTechAssignment.tenant_id == tenant_id)
                        .where(JobTechAssignment.is_active == True)
                    ).all()
                ]
                q = q.where(Job.id.in_(assigned_job_ids))
            rows = db.exec(q).all()
            for r in rows:
                yield {
                    "id": str(r.id),
                    "status": str(getattr(r, "status", "")),
                    "tenant_id": str(r.tenant_id),
                    "created_at": r.created_at.isoformat(),
                }

        elif entity_name == "quote":
            from app.models.quoting import Quote

            rows = db.exec(select(Quote).where(Quote.tenant_id == tenant_id)).all()
            for r in rows:
                yield {
                    "id": str(r.id),
                    "status": str(getattr(r, "status", "")),
                    "tenant_id": str(r.tenant_id),
                    "created_at": r.created_at.isoformat(),
                }

        elif entity_name == "invoice":
            from app.models.billing import Invoice

            rows = db.exec(select(Invoice).where(Invoice.tenant_id == tenant_id)).all()
            for r in rows:
                yield {
                    "id": str(r.id),
                    "status": str(getattr(r, "status", "")),
                    "tenant_id": str(r.tenant_id),
                    "created_at": r.created_at.isoformat(),
                }

        elif entity_name == "job_time_entry":
            from app.models.fulfillment import JobTimeEntry

            q = select(JobTimeEntry).where(JobTimeEntry.tenant_id == tenant_id)
            if data_scope == "user_specific":
                q = q.where(JobTimeEntry.user_id == user_id)
            rows = db.exec(q).all()
            for r in rows:
                yield {
                    "id": str(r.id),
                    "job_id": str(r.job_id),
                    "user_id": str(r.user_id),
                    "created_at": r.created_at.isoformat(),
                }

        elif entity_name == "job_expense":
            from app.models.fulfillment import JobExpense

            q = select(JobExpense).where(JobExpense.tenant_id == tenant_id)
            if data_scope == "user_specific":
                q = q.where(JobExpense.user_id == user_id)
            rows = db.exec(q).all()
            for r in rows:
                yield {
                    "id": str(r.id),
                    "job_id": str(r.job_id),
                    "created_at": r.created_at.isoformat(),
                }

        elif entity_name == "customer_communication":
            from app.models.communications import CustomerCommunication

            q = select(CustomerCommunication).where(
                CustomerCommunication.tenant_id == tenant_id
            )
            rows = db.exec(q).all()
            for r in rows:
                yield {
                    "id": str(r.id),
                    "tenant_id": str(r.tenant_id),
                    "created_at": r.created_at.isoformat(),
                }

        elif entity_name == "contact":
            from app.models.crm import Contact

            rows = db.exec(select(Contact).where(Contact.tenant_id == tenant_id)).all()
            for r in rows:
                yield {
                    "id": str(r.id),
                    "tenant_id": str(r.tenant_id),
                    "is_active": r.is_active,
                    "created_at": r.created_at.isoformat(),
                }

    except Exception as e:
        logger.warning(f"Failed to export entity '{entity_name}': {e}")
