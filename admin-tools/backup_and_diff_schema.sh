#!/usr/bin/env bash
#
# backup_and_diff_schema.sh
#
# Automates the schema backup + diff workflow:
#   1. pg_dump (schema-only) into archive/db-backups/schema-only/
#   2. Copy the new dump over the master file in dev-docs/db-design/
#   3. Activate the backend venv and run schema_diff.py
#
# Usage:
#   chmod +x backup_and_diff_schema.sh    # one-time
#   ./backup_and_diff_schema.sh
#
# Password handling:
#   The script uses the PGPASSWORD env var. The default below matches your
#   current workflow. For better security, use ~/.pgpass instead:
#
#     echo "localhost:5432:pilot_dev:pilot_user:YOUR_PASSWORD" >> ~/.pgpass
#     chmod 600 ~/.pgpass
#
#   ...then delete the `export PGPASSWORD=...` line below. pg_dump will pick
#   up the credentials from .pgpass automatically.

set -euo pipefail

# ── Configuration ─────────────────────────────────────────────────────────────
PROJECT_ROOT="$HOME/Projects/roo-code/pilot"
BACKUP_DIR="$PROJECT_ROOT/archive/db-backups/schema-only"
DB_DESIGN_DIR="$PROJECT_ROOT/dev-docs/db-design"
VENV_PATH="$PROJECT_ROOT/backend/.venv"
MASTER_DUMP="$DB_DESIGN_DIR/pilot-db-schema-dump-master.sql"

DB_HOST="localhost"
DB_USER="pilot_user"
DB_NAME="pilot_dev"

export PGPASSWORD="${PGPASSWORD:-CHANGE_ME_LOCAL_DB_PW}"

# ── Sanity checks ─────────────────────────────────────────────────────────────
command -v pg_dump >/dev/null || { echo "✗ pg_dump not found in PATH"; exit 1; }
[[ -d "$BACKUP_DIR"     ]] || { echo "✗ Backup dir not found: $BACKUP_DIR"; exit 1; }
[[ -d "$DB_DESIGN_DIR"  ]] || { echo "✗ DB design dir not found: $DB_DESIGN_DIR"; exit 1; }
[[ -f "$VENV_PATH/bin/activate" ]] || { echo "✗ venv not found: $VENV_PATH"; exit 1; }
[[ -f "$DB_DESIGN_DIR/schema_diff.py" ]] || { echo "✗ schema_diff.py not found in $DB_DESIGN_DIR"; exit 1; }

# ── Run ───────────────────────────────────────────────────────────────────────
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DUMP_FILE="schema_dump_${TIMESTAMP}.sql"
DUMP_PATH="$BACKUP_DIR/$DUMP_FILE"

echo "→ Dumping schema to $DUMP_FILE"
pg_dump -h "$DB_HOST" -U "$DB_USER" -s -x -O "$DB_NAME" > "$DUMP_PATH"

echo "→ Copying to master: $MASTER_DUMP"
cp "$DUMP_PATH" "$MASTER_DUMP"

echo "→ Activating venv"
# shellcheck source=/dev/null
source "$VENV_PATH/bin/activate"

echo "→ Running schema_diff.py"
cd "$DB_DESIGN_DIR"
python schema_diff.py

unset PGPASSWORD

echo ""
echo "✓ Done. Open $DB_DESIGN_DIR/schema_diff_report.html to view the report."
