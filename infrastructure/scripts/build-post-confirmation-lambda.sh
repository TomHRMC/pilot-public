#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# build-post-confirmation-lambda.sh
#
# Builds the Cognito Post-Confirmation Lambda deployment package for
# pilot-production-post-confirmation (SIGNUP-GA-1, ADR-0011).
#
# Produces a flat build directory that the Terraform `data.archive_file`
# resource zips into post_confirmation.zip at plan/apply time.
#
# Dependencies packaged (Linux manylinux wheels, Lambda python3.12):
#   psycopg2-binary, sqlalchemy, sqlmodel, pydantic, pgvector (+ transitive)
#
# NOT packaged (pre-bundled in the AWS Lambda Python runtime):
#   boto3, botocore — imported lazily by handler._resolve_db_url() only when
#   DATABASE_URL is unset (i.e. in Lambda, not local dev/tests).
#
# The handler imports `from app.models.{auth,core} import ...`, and
# app/models/__init__.py eagerly imports ALL model modules (including ai.py
# and help.py which depend on pgvector). Therefore the entire app/models/
# tree is bundled.
#
# Usage:
#   ./infrastructure/scripts/build-post-confirmation-lambda.sh
#
# Run from the repo root before `terraform plan`/`apply` on the security module.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKEND_DIR="${REPO_ROOT}/backend"
BUILD_DIR="${REPO_ROOT}/infrastructure/terraform/modules/security/build/post_confirmation"

PYTHON_VERSION="3.12"
PLATFORM="manylinux2014_x86_64"

# Pinned to backend/requirements.txt for parity with the app.
DEPS=(
  "psycopg2-binary==2.9.11"
  "SQLAlchemy==2.0.48"
  "sqlmodel==0.0.37"
  "pydantic==2.12.5"
  "pgvector==0.4.2"
)

echo "=== Building Post-Confirmation Lambda package ==="
echo "  Build dir: ${BUILD_DIR}"
echo "  Python:    ${PYTHON_VERSION} (${PLATFORM})"
echo ""

# ── 1. Clean + recreate build dir ────────────────────────────────────────────
rm -rf "${BUILD_DIR}"
mkdir -p "${BUILD_DIR}"

# ── 2. Install Linux-compatible wheels ───────────────────────────────────────
# --only-binary=:all:  forces wheel-only (no source builds); a mac-built
#                       psycopg2/pgvector C extension would fail at Lambda runtime.
# --platform / --implementation / --python-version: cross-install for Lambda.
# Use the venv Python if available (backend/.venv), else fall back to python3.
PYTHON_BIN="${BACKEND_DIR}/.venv/bin/python"
if [ ! -x "${PYTHON_BIN}" ]; then
  PYTHON_BIN="$(command -v python3)"
fi
echo ">> Using Python: ${PYTHON_BIN} ($(${PYTHON_BIN} --version 2>&1))"

# Install all deps + their transitive deps (pydantic-core, annotated-types,
# typing-extensions, typing-inspection) as Linux cp312 wheels. Let pip resolve
# the correct transitive versions automatically (pinned to requirements.txt
# via the main package pins).
echo ">> Installing dependencies + transitive (Linux ${PLATFORM} wheels)..."
"${PYTHON_BIN}" -m pip install \
  --target "${BUILD_DIR}" \
  --platform "${PLATFORM}" \
  --implementation cp \
  --python-version "${PYTHON_VERSION}" \
  --only-binary=:all: \
  "${DEPS[@]}"

# ── 3. Copy handler source ───────────────────────────────────────────────────
# The Lambda handler is `handler.handler` (module=handler, func=handler), so
# handler.py MUST be at the ROOT of the zip (not nested under lambda/...).
echo ">> Copying handler source to build root..."
cp "${BACKEND_DIR}/lambda/post_confirmation/handler.py" \
   "${BUILD_DIR}/handler.py"

# ── 4. Copy app/models tree (handler imports from app.models.{auth,core}) ────
# app/models/__init__.py eagerly imports ALL model modules, so the entire
# tree must be present. app/__init__.py is empty (verified).
echo ">> Copying app/models tree..."
mkdir -p "${BUILD_DIR}/app/models"
cp "${BACKEND_DIR}/app/__init__.py" "${BUILD_DIR}/app/__init__.py"
cp -r "${BACKEND_DIR}/app/models/." "${BUILD_DIR}/app/models/"

# ── 5. Verify the import chain resolves ──────────────────────────────────────
echo ">> Verifying package structure..."
if [ ! -f "${BUILD_DIR}/handler.py" ]; then
  echo "ERROR: handler.py missing from build dir root" >&2
  exit 1
fi
if [ ! -f "${BUILD_DIR}/app/models/auth.py" ]; then
  echo "ERROR: app/models/auth.py missing from build dir" >&2
  exit 1
fi
if [ ! -f "${BUILD_DIR}/app/models/core.py" ]; then
  echo "ERROR: app/models/core.py missing from build dir" >&2
  exit 1
fi

# Count installed packages
PKG_COUNT=$(find "${BUILD_DIR}" -maxdepth 1 -type d | tail -n +2 | wc -l | tr -d ' ')
echo "  Installed ${PKG_COUNT} top-level packages"

echo ""
echo "=== Build complete ==="
echo "  The Terraform data.archive_file.post_confirmation resource will zip"
echo "  this directory at plan/apply time."
echo ""
echo "  Next: cd infrastructure/terraform/environments/production && terraform plan"
