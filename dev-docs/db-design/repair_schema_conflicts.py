#!/usr/bin/env python3
"""
Repair git conflict markers in pilot-db-schema-v2.6h.json.

Resolution rules (DB-verified):
  Category 1 — upstream is blank, stash has real content → keep stash
  Category 2 — both sides have content (two tables interleaved) → keep upstream only,
               inject stash tables as separate clean entries after help_training_corpus.
"""

import json
import shutil
import sys
from pathlib import Path

INPUT = Path("dev-docs/db-design/pilot-db-schema-v2.6h.json")
BACKUP = Path("dev-docs/db-design/pilot-db-schema-v2.6h.json.bak")

# ---------------------------------------------------------------------------
# Step 1 — backup
# ---------------------------------------------------------------------------
shutil.copy2(INPUT, BACKUP)
print(f"Backup written → {BACKUP}")

# ---------------------------------------------------------------------------
# Step 2 — resolve conflict markers
# ---------------------------------------------------------------------------
raw = INPUT.read_text(encoding="utf-8")
lines = raw.splitlines(keepends=True)

resolved_lines = []
state = "NORMAL"
upstream_buf = []
stash_buf = []
conflicts_resolved = 0

for line in lines:
    stripped = line.rstrip("\n").rstrip("\r")

    if stripped.startswith("<<<<<<< "):
        state = "IN_UPSTREAM"
        upstream_buf = []
        stash_buf = []
        continue

    if stripped == "=======" and state == "IN_UPSTREAM":
        state = "IN_STASH"
        continue

    if stripped.startswith(">>>>>>> ") and state == "IN_STASH":
        state = "NORMAL"
        conflicts_resolved += 1

        upstream_content = "".join(upstream_buf)
        stash_content = "".join(stash_buf)

        upstream_blank = not upstream_content.strip()

        if upstream_blank:
            # Category 1: keep stash content
            resolved_lines.append(stash_content)
        else:
            # Category 2: keep upstream content, stash tables injected later
            resolved_lines.append(upstream_content)

        upstream_buf = []
        stash_buf = []
        continue

    if state == "IN_UPSTREAM":
        upstream_buf.append(line)
    elif state == "IN_STASH":
        stash_buf.append(line)
    else:
        resolved_lines.append(line)

resolved_text = "".join(resolved_lines)
print(f"Conflict blocks resolved: {conflicts_resolved}")

# ---------------------------------------------------------------------------
# Step 3 — inject the 5 stash table definitions AFTER help_training_corpus
#           (only if they are not already present in the resolved text)
# ---------------------------------------------------------------------------

STASH_TABLES = {
    "user_session_history": {
        "comment": "B13/A72: One row per (tenant_id, user_id). Upserted on every successful login to track first-login date and total session count.",
        "columns": {
            "tenant_id": {"type": "uuid", "nullable": False},
            "user_id": {"type": "uuid", "nullable": False},
            "first_login_at": {"type": "timestamp with time zone", "nullable": False},
            "total_session_count": {
                "type": "integer",
                "nullable": False,
                "default": "0",
            },
            "last_login_at": {"type": "timestamp with time zone", "nullable": False},
            "created_at": {"type": "timestamp with time zone", "nullable": False},
            "updated_at": {"type": "timestamp with time zone", "nullable": False},
            "created_by": {"type": "uuid", "nullable": True},
            "updated_by": {"type": "uuid", "nullable": True},
        },
        "primary_key": ["tenant_id", "user_id"],
        "unique": [],
        "check_constraints": [],
        "foreign_keys": [
            {
                "name": "user_session_history_tenant_id_fkey",
                "columns": ["tenant_id"],
                "ref_table": "tenant",
                "ref_columns": ["id"],
                "on_delete": "NO ACTION",
            },
            {
                "name": "user_session_history_user_id_fkey",
                "columns": ["user_id"],
                "ref_table": "user",
                "ref_columns": ["id"],
                "on_delete": "NO ACTION",
            },
        ],
        "indexes": [
            {
                "name": "ix_user_session_history_tenant_id",
                "definition": "CREATE INDEX ix_user_session_history_tenant_id ON public.user_session_history USING btree (tenant_id)",
            },
            {
                "name": "ix_user_session_history_user_id",
                "definition": "CREATE INDEX ix_user_session_history_user_id ON public.user_session_history USING btree (user_id)",
            },
        ],
        "triggers": [
            {
                "name": "audit_user_session_history_changes",
                "definition": "CREATE TRIGGER audit_user_session_history_changes AFTER INSERT OR DELETE OR UPDATE ON public.user_session_history FOR EACH ROW EXECUTE FUNCTION audit.log_changes()",
            },
            {
                "name": "trg_user_session_history_guard_created_immutable",
                "definition": "CREATE TRIGGER trg_user_session_history_guard_created_immutable BEFORE UPDATE ON public.user_session_history FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()",
            },
            {
                "name": "trg_user_session_history_set_updated_at",
                "definition": "CREATE TRIGGER trg_user_session_history_set_updated_at BEFORE UPDATE ON public.user_session_history FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()",
            },
        ],
    },
    "mfa_grace_period_tracking": {
        "comment": "B13/A68: Per-user MFA grace period tracking. Created when tenant MFA policy activates. Updated when user enrolls or logs in mid-grace.",
        "columns": {
            "tenant_id": {"type": "uuid", "nullable": False},
            "user_id": {"type": "uuid", "nullable": False},
            "grace_started_at": {"type": "timestamp with time zone", "nullable": False},
            "enrolled_at": {"type": "timestamp with time zone", "nullable": True},
            "enforcement_activated_at": {
                "type": "timestamp with time zone",
                "nullable": True,
            },
        },
        "primary_key": ["tenant_id", "user_id"],
        "unique": [],
        "check_constraints": [],
        "foreign_keys": [
            {
                "name": "mfa_grace_period_tracking_tenant_id_fkey",
                "columns": ["tenant_id"],
                "ref_table": "tenant",
                "ref_columns": ["id"],
                "on_delete": "NO ACTION",
            },
            {
                "name": "mfa_grace_period_tracking_user_id_fkey",
                "columns": ["user_id"],
                "ref_table": "user",
                "ref_columns": ["id"],
                "on_delete": "NO ACTION",
            },
        ],
        "indexes": [
            {
                "name": "ix_mfa_grace_period_tracking_tenant_id",
                "definition": "CREATE INDEX ix_mfa_grace_period_tracking_tenant_id ON public.mfa_grace_period_tracking USING btree (tenant_id)",
            },
            {
                "name": "ix_mfa_grace_period_tracking_user_id",
                "definition": "CREATE INDEX ix_mfa_grace_period_tracking_user_id ON public.mfa_grace_period_tracking USING btree (user_id)",
            },
        ],
        "triggers": [
            {
                "name": "audit_mfa_grace_period_tracking_changes",
                "definition": "CREATE TRIGGER audit_mfa_grace_period_tracking_changes AFTER INSERT OR DELETE OR UPDATE ON public.mfa_grace_period_tracking FOR EACH ROW EXECUTE FUNCTION audit.log_changes()",
            },
            {
                "name": "trg_mfa_grace_period_tracking_guard_created_immutable",
                "definition": "CREATE TRIGGER trg_mfa_grace_period_tracking_guard_created_immutable BEFORE UPDATE ON public.mfa_grace_period_tracking FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()",
            },
            {
                "name": "trg_mfa_grace_period_tracking_set_updated_at",
                "definition": "CREATE TRIGGER trg_mfa_grace_period_tracking_set_updated_at BEFORE UPDATE ON public.mfa_grace_period_tracking FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()",
            },
        ],
    },
    "user_mfa_method": {
        "comment": "B13/A69: Persistent MFA enrollment record per (tenant_id, user_id, method_type). One row per method type per user.",
        "columns": {
            "mfa_method_id": {
                "type": "uuid",
                "nullable": False,
                "default": "gen_random_uuid()",
            },
            "tenant_id": {"type": "uuid", "nullable": False},
            "user_id": {"type": "uuid", "nullable": False},
            "method_type": {"type": "text", "nullable": False},
            "enrolled_at": {"type": "timestamp with time zone", "nullable": False},
            "last_used_at": {"type": "timestamp with time zone", "nullable": True},
            "cognito_method_id": {"type": "text", "nullable": False},
            "verification_status": {
                "type": "text",
                "nullable": False,
                "default": "'verified'",
            },
            "metadata": {"type": "jsonb", "nullable": True},
        },
        "primary_key": ["mfa_method_id"],
        "unique": [["tenant_id", "user_id", "method_type"]],
        "check_constraints": [],
        "foreign_keys": [
            {
                "name": "user_mfa_method_tenant_id_fkey",
                "columns": ["tenant_id"],
                "ref_table": "tenant",
                "ref_columns": ["id"],
                "on_delete": "NO ACTION",
            },
            {
                "name": "user_mfa_method_user_id_fkey",
                "columns": ["user_id"],
                "ref_table": "user",
                "ref_columns": ["id"],
                "on_delete": "NO ACTION",
            },
        ],
        "indexes": [
            {
                "name": "ix_user_mfa_method_tenant_id",
                "definition": "CREATE INDEX ix_user_mfa_method_tenant_id ON public.user_mfa_method USING btree (tenant_id)",
            },
            {
                "name": "ix_user_mfa_method_user_id",
                "definition": "CREATE INDEX ix_user_mfa_method_user_id ON public.user_mfa_method USING btree (user_id)",
            },
        ],
        "triggers": [
            {
                "name": "audit_user_mfa_method_changes",
                "definition": "CREATE TRIGGER audit_user_mfa_method_changes AFTER INSERT OR DELETE OR UPDATE ON public.user_mfa_method FOR EACH ROW EXECUTE FUNCTION audit.log_changes()",
            },
            {
                "name": "trg_user_mfa_method_guard_created_immutable",
                "definition": "CREATE TRIGGER trg_user_mfa_method_guard_created_immutable BEFORE UPDATE ON public.user_mfa_method FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()",
            },
            {
                "name": "trg_user_mfa_method_set_updated_at",
                "definition": "CREATE TRIGGER trg_user_mfa_method_set_updated_at BEFORE UPDATE ON public.user_mfa_method FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()",
            },
        ],
    },
    "user_session_metadata": {
        "comment": "B13/A70: One row per active browser/device session. Linked to auth_refresh_token via session_id FK (Migration 7).",
        "columns": {
            "session_id": {
                "type": "uuid",
                "nullable": False,
                "default": "gen_random_uuid()",
            },
            "tenant_id": {"type": "uuid", "nullable": False},
            "user_id": {"type": "uuid", "nullable": False},
            "device_fingerprint": {"type": "text", "nullable": False},
            "display_label": {"type": "text", "nullable": False},
            "ip_address": {"type": "inet", "nullable": False},
            "geolocation": {"type": "text", "nullable": True},
            "created_at": {
                "type": "timestamp with time zone",
                "nullable": False,
                "default": "now()",
            },
            "last_active_at": {"type": "timestamp with time zone", "nullable": False},
            "revoked_at": {"type": "timestamp with time zone", "nullable": True},
        },
        "primary_key": ["session_id"],
        "unique": [],
        "check_constraints": [],
        "foreign_keys": [
            {
                "name": "user_session_metadata_tenant_id_fkey",
                "columns": ["tenant_id"],
                "ref_table": "tenant",
                "ref_columns": ["id"],
                "on_delete": "NO ACTION",
            },
            {
                "name": "user_session_metadata_user_id_fkey",
                "columns": ["user_id"],
                "ref_table": "user",
                "ref_columns": ["id"],
                "on_delete": "NO ACTION",
            },
        ],
        "indexes": [
            {
                "name": "ix_user_session_metadata_tenant_id",
                "definition": "CREATE INDEX ix_user_session_metadata_tenant_id ON public.user_session_metadata USING btree (tenant_id)",
            },
            {
                "name": "ix_user_session_metadata_user_id",
                "definition": "CREATE INDEX ix_user_session_metadata_user_id ON public.user_session_metadata USING btree (user_id)",
            },
            {
                "name": "ix_user_session_metadata_user_id_revoked_at",
                "definition": "CREATE INDEX ix_user_session_metadata_user_id_revoked_at ON public.user_session_metadata USING btree (user_id, revoked_at)",
            },
        ],
        "triggers": [
            {
                "name": "audit_user_session_metadata_changes",
                "definition": "CREATE TRIGGER audit_user_session_metadata_changes AFTER INSERT OR DELETE OR UPDATE ON public.user_session_metadata FOR EACH ROW EXECUTE FUNCTION audit.log_changes()",
            },
            {
                "name": "trg_user_session_metadata_guard_created_immutable",
                "definition": "CREATE TRIGGER trg_user_session_metadata_guard_created_immutable BEFORE UPDATE ON public.user_session_metadata FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()",
            },
            {
                "name": "trg_user_session_metadata_set_updated_at",
                "definition": "CREATE TRIGGER trg_user_session_metadata_set_updated_at BEFORE UPDATE ON public.user_session_metadata FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()",
            },
        ],
    },
    "data_export_request": {
        "comment": "B13/A71: Async data export request tracking. Status: pending -> processing -> ready | expired | failed. ZIP streamed to S3.",
        "columns": {
            "export_id": {
                "type": "uuid",
                "nullable": False,
                "default": "gen_random_uuid()",
            },
            "tenant_id": {"type": "uuid", "nullable": False},
            "user_id": {"type": "uuid", "nullable": False},
            "requested_at": {
                "type": "timestamp with time zone",
                "nullable": False,
                "default": "now()",
            },
            "status": {"type": "text", "nullable": False, "default": "'pending'"},
            "s3_path": {"type": "text", "nullable": True},
            "signed_url": {"type": "text", "nullable": True},
            "expires_at": {"type": "timestamp with time zone", "nullable": True},
            "data_scope": {"type": "text", "nullable": False},
            "failure_reason": {"type": "text", "nullable": True},
        },
        "primary_key": ["export_id"],
        "unique": [],
        "check_constraints": [],
        "foreign_keys": [
            {
                "name": "data_export_request_tenant_id_fkey",
                "columns": ["tenant_id"],
                "ref_table": "tenant",
                "ref_columns": ["id"],
                "on_delete": "NO ACTION",
            },
            {
                "name": "data_export_request_user_id_fkey",
                "columns": ["user_id"],
                "ref_table": "user",
                "ref_columns": ["id"],
                "on_delete": "NO ACTION",
            },
        ],
        "indexes": [
            {
                "name": "ix_data_export_request_tenant_id",
                "definition": "CREATE INDEX ix_data_export_request_tenant_id ON public.data_export_request USING btree (tenant_id)",
            },
            {
                "name": "ix_data_export_request_user_id",
                "definition": "CREATE INDEX ix_data_export_request_user_id ON public.data_export_request USING btree (user_id)",
            },
            {
                "name": "ix_data_export_request_status",
                "definition": "CREATE INDEX ix_data_export_request_status ON public.data_export_request USING btree (status)",
            },
        ],
        "triggers": [
            {
                "name": "audit_data_export_request_changes",
                "definition": "CREATE TRIGGER audit_data_export_request_changes AFTER INSERT OR DELETE OR UPDATE ON public.data_export_request FOR EACH ROW EXECUTE FUNCTION audit.log_changes()",
            },
            {
                "name": "trg_data_export_request_guard_created_immutable",
                "definition": "CREATE TRIGGER trg_data_export_request_guard_created_immutable BEFORE UPDATE ON public.data_export_request FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()",
            },
            {
                "name": "trg_data_export_request_set_updated_at",
                "definition": "CREATE TRIGGER trg_data_export_request_set_updated_at BEFORE UPDATE ON public.data_export_request FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()",
            },
        ],
    },
}

tables_injected = []

# Find tables that are already present in the resolved text
for table_name, table_def in STASH_TABLES.items():
    # Check using the key pattern in the JSON text
    key_pattern = f'"{table_name}"'
    if key_pattern in resolved_text:
        print(f"  ⏭  {table_name} already present — skipping injection")
        continue

    # Find injection point: after the closing of help_training_corpus table entry.
    # The closing pattern is the triggers array closing for help_training_corpus,
    # followed by `}` that closes the table, followed by `,` or `\n    }` for next.
    # We search for the "help_training_corpus" key and then find its closing `}`.
    #
    # Strategy: locate `"help_training_corpus":` and then find the matching
    # closing `}` at depth 0 relative to that object.
    corpus_key = '"help_training_corpus"'
    corpus_start = resolved_text.find(corpus_key)
    if corpus_start == -1:
        print(f"  ⚠  Cannot find help_training_corpus injection point for {table_name}")
        continue

    # Walk forward from the `{` that opens help_training_corpus value
    brace_start = resolved_text.index("{", corpus_start)
    depth = 0
    i = brace_start
    while i < len(resolved_text):
        ch = resolved_text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                # i is the closing `}` of help_training_corpus
                corpus_end = i
                break
        i += 1
    else:
        print(
            f"  ⚠  Could not find closing brace of help_training_corpus for {table_name}"
        )
        continue

    # Build injection snippet
    table_json = json.dumps({table_name: table_def}, indent=4, ensure_ascii=False)
    # table_json will be {"table_name": {...}} — we want just the inner entry
    # Strip outer { } to get `"table_name": { ... }`
    inner = table_json.strip()[1:-1].strip()  # remove outer { and }

    # Insert after corpus_end: add comma after existing `}`, then newline + entry
    resolved_text = (
        resolved_text[: corpus_end + 1]
        + ",\n    "
        + inner
        + resolved_text[corpus_end + 1 :]
    )
    tables_injected.append(table_name)
    print(f"  ✅ Injected {table_name}")

# ---------------------------------------------------------------------------
# Step 4 — validate JSON
# ---------------------------------------------------------------------------
try:
    parsed = json.loads(resolved_text)
    json_valid = True
    error_msg = None
except json.JSONDecodeError as e:
    json_valid = False
    error_msg = str(e)
    # Print context around the error line
    err_lines = resolved_text.splitlines()
    start = max(0, e.lineno - 5)
    end = min(len(err_lines), e.lineno + 5)
    print(f"\n❌ JSON parse error at line {e.lineno}, col {e.colno}: {e.msg}")
    print("Context:")
    for ln, txt in enumerate(err_lines[start:end], start=start + 1):
        marker = ">>>" if ln == e.lineno else "   "
        print(f"  {marker} {ln:5d}: {txt}")

# ---------------------------------------------------------------------------
# Step 5 — write output (even if invalid, so you can inspect it)
# ---------------------------------------------------------------------------
INPUT.write_text(resolved_text, encoding="utf-8")

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print(f"Conflict blocks resolved : {conflicts_resolved}")
print(f"Tables injected          : {tables_injected}")
if json_valid:
    table_count = len(parsed.get("tables", {}))
    print(f"Top-level tables in JSON : {table_count}")
    print("✅ JSON valid")
else:
    print(f"❌ JSON invalid: {error_msg}")
    sys.exit(1)
