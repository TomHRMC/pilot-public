# Schema Backup & Diff Automation

This document describes `backup_and_diff_schema.sh`, a bash script that automates the schema-only Postgres backup and diff-report workflow for the Pilot project.

## What it does

The script runs the following steps in order:

1. Runs `pg_dump` against `pilot_dev` to produce a schema-only dump (no data, no privileges, no ownership) into `archive/db-backups/schema-only/`, with a timestamped filename like `schema_dump_20260501_064921.sql`.
2. Copies that new dump over the master file at `dev-docs/db-design/pilot-db-schema-dump-master.sql`.
3. Activates the backend Python virtual environment at `backend/.venv`.
4. Runs `schema_diff.py` from `dev-docs/db-design/`, which produces `schema_diff_report.html` in that same folder.

Before running any of those steps, the script verifies that `pg_dump` is installed, all required directories exist, the venv is present, and `schema_diff.py` is in place — so a missing dependency fails fast with a clear message rather than halfway through the run.

## Prerequisites

- PostgreSQL client tools installed (`pg_dump` on `PATH`)
- The Pilot project at `<repo>/`
- Backend venv created at `<repo>/backend/.venv/`
- `schema_diff.py` in `<repo>/dev-docs/db-design/`

## One-time setup

### 1. Make the script executable

```bash
chmod +x backup_and_diff_schema.sh
```

### 2. Set up `~/.pgpass` (recommended)

Rather than keeping your DB password inside the script, store it in a `~/.pgpass` file. Any tool built on the standard Postgres client library (`pg_dump`, `psql`, `pg_restore`, etc.) will pick it up automatically when no password is supplied another way.

Create the file:

```bash
echo "localhost:5432:pilot_dev:pilot_user:CHANGE_ME_LOCAL_DB_PW" >> ~/.pgpass
chmod 600 ~/.pgpass
```

The format is `hostname:port:database:username:password`, one line per credential.

**Important:** the `chmod 600` step is required. libpq will silently ignore the file if it's readable by group or other — this is a safety check against leaving credentials world-readable.

A few useful notes:

- You can use `*` as a wildcard in any of the first four fields. For example, `localhost:*:*:pilot_user:CHANGE_ME_LOCAL_DB_PW` matches `pilot_user` on localhost across any port and any database.
- Lookups are first-match-wins, top to bottom — put more specific entries above wildcard ones.
- If a password contains `:` or `\`, escape them with a backslash.

Once `~/.pgpass` is in place, open the script and delete the `export PGPASSWORD=...` line. `pg_dump` will pick the password up from the file automatically.

## Usage

Run the script from anywhere — all paths inside are absolute:

```bash
./backup_and_diff_schema.sh
```

Expected output:

```
→ Dumping schema to schema_dump_20260501_064921.sql
→ Copying to master: /Users/you/Projects/roo-code/pilot/dev-docs/db-design/pilot-db-schema-dump-master.sql
→ Activating venv
→ Running schema_diff.py
→ ...
✓ Done. Open /Users/you/Projects/roo-code/pilot/dev-docs/db-design/schema_diff_report.html to view the report.
```

Open `schema_diff_report.html` in your browser to view the diff.

## Configuration

All configurable values live near the top of the script:

```bash
PROJECT_ROOT="$HOME/Projects/roo-code/pilot"
BACKUP_DIR="$PROJECT_ROOT/archive/db-backups/schema-only"
DB_DESIGN_DIR="$PROJECT_ROOT/dev-docs/db-design"
VENV_PATH="$PROJECT_ROOT/backend/.venv"
MASTER_DUMP="$DB_DESIGN_DIR/pilot-db-schema-dump-master.sql"

DB_HOST="localhost"
DB_USER="pilot_user"
DB_NAME="pilot_dev"
```

Edit these if any of the paths or DB connection details change.

## `pg_dump` flags reference

The script uses these flags:

- `-h localhost` — host
- `-U pilot_user` — connecting user
- `-s` — schema only (no data)
- `-x` — skip privileges (no `GRANT`/`REVOKE` statements)
- `-O` — skip ownership (no `ALTER ... OWNER TO` statements)

Together, `-s -x -O` produce a clean schema-only dump suitable for diffing against a master reference without noise from environment-specific permissions or ownership.

## Troubleshooting

**`pg_dump: command not found`** — install PostgreSQL client tools (e.g. `brew install postgresql@16`) and ensure they're on `PATH`.

**`fe_sendauth: no password supplied`** — neither `PGPASSWORD` nor `~/.pgpass` is providing a password. Either restore the `export PGPASSWORD=...` line in the script or fix your `.pgpass` setup (most commonly, permissions aren't `600`).

**`✗ venv not found`** — the backend venv hasn't been created. From `<repo>/backend/`, run `python -m venv .venv` and install requirements.

**Script runs but report looks wrong** — confirm that the new dump actually overwrote `pilot-db-schema-dump-master.sql`. The "Copying to master" line in the output should show the right destination path.
