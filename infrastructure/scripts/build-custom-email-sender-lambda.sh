#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# build-custom-email-sender-lambda.sh
#
# Builds the Cognito Custom Email Sender Lambda deployment package for
# pilot-production-custom-email-sender (COGNITO-EMAIL-1, design §C step 3).
#
# Produces a flat build directory that the Terraform `data.archive_file`
# resource zips into custom_email_sender.zip at plan/apply time.
#
# Mirrors build-post-authentication-lambda.sh / build-post-confirmation-lambda.sh
# with ONE key simplification: this handler is **self-contained** — no
# `app/models` bundle, no DB deps (design §B: the auth email path must not
# depend on RDS availability).
#
# Dependencies packaged (Linux manylinux wheels, Lambda python3.12):
#   sendgrid==6.11.0
#     (+ transitive: python-http-client, starkbank-ecdsa)
#   aws-encryption-sdk==4.0.6
#     (+ transitive: attrs, wrapt, cryptography)
#   aws-cryptographic-material-providers==1.11.3
#     (+ transitive: DafnyRuntimePython, pytz, aws-cryptography-internal-*)
#
#   Cognito encrypts the auth code using the AWS Encryption SDK envelope format
#   (NOT raw KMS Encrypt). The handler uses aws_encryption_sdk.EncryptionSDKClient
#   + a KMS keyring from aws_cryptographic_material_providers to decrypt it.
#   Raw kms.decrypt() fails with InvalidCiphertextException (discovered
#   2026-09-03 in the first prod smoke).
#
# NOT packaged (pre-bundled in the AWS Lambda Python runtime):
#   boto3, botocore — imported lazily by handler._get_kms_keyring() and
#   _resolve_sendgrid_key() only when SENDGRID_API_KEY / SENDGRID_SECRET_ARN
#   env-var overrides are unset (i.e. in Lambda, not local dev/tests).
#
# Usage:
#   ./infrastructure/scripts/build-custom-email-sender-lambda.sh
#
# Run from the repo root before `terraform plan`/`apply` on the security module.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKEND_DIR="${REPO_ROOT}/backend"
BUILD_DIR="${REPO_ROOT}/infrastructure/terraform/modules/security/build/custom_email_sender"

PYTHON_VERSION="3.12"
PLATFORM="manylinux2014_x86_64"

# Pinned to backend/requirements.txt:79 — the exact sendgrid pin.
# aws-encryption-sdk + aws-cryptographic-material-providers are required because
# Cognito encrypts the auth code using the AWS Encryption SDK envelope format
# (NOT raw KMS Encrypt). pip resolves transitive deps automatically.
DEPS=(
  "sendgrid==6.11.0"
  "aws-encryption-sdk==4.0.6"
  "aws-cryptographic-material-providers==1.11.3"
)

echo "=== Building Custom Email Sender Lambda package ==="
echo "  Build dir: ${BUILD_DIR}"
echo "  Python:    ${PYTHON_VERSION} (${PLATFORM})"
echo ""

# ── 1. Clean + recreate build dir ────────────────────────────────────────────
rm -rf "${BUILD_DIR}"
mkdir -p "${BUILD_DIR}"

# ── 2. Install Linux-compatible wheels ───────────────────────────────────────
# --only-binary=:all:  forces wheel-only (no source builds).
# --platform / --implementation / --python-version: cross-install for Lambda.
# Use the venv Python if available (backend/.venv), else fall back to python3.
PYTHON_BIN="${BACKEND_DIR}/.venv/bin/python"
if [ ! -x "${PYTHON_BIN}" ]; then
  PYTHON_BIN="$(command -v python3)"
fi
echo ">> Using Python: ${PYTHON_BIN} ($(${PYTHON_BIN} --version 2>&1))"

# Install sendgrid + aws-encryption-sdk + transitive deps as Linux cp312 wheels.
echo ">> Installing dependencies + transitive (Linux ${PLATFORM} wheels)..."
"${PYTHON_BIN}" -m pip install \
  --target "${BUILD_DIR}" \
  --platform "${PLATFORM}" \
  --implementation cp \
  --python-version "${PYTHON_VERSION}" \
  --only-binary=:all: \
  "${DEPS[@]}"

# ── 2b. Remove runtime-provided packages ─────────────────────────────────────
# aws-encryption-sdk and aws-cryptographic-material-providers both declare
# boto3 as a dependency, so pip installs boto3 + botocore + s3transfer +
# urllib3 + jmespath + python-dateutil + six. These are ALL pre-bundled in
# the AWS Lambda Python runtime — packaging them bloats the zip and can cause
# version conflicts. Remove them after install.
echo ">> Removing runtime-provided packages (boto3, botocore, etc.)..."
RUNTIME_PROVIDED=(
  "boto3"
  "botocore"
  "s3transfer"
  "urllib3"
  "jmespath"
  "python_dateutil"
  "dateutil"
  "six"
)
for pkg in "${RUNTIME_PROVIDED[@]}"; do
  rm -rf "${BUILD_DIR}/${pkg}" "${BUILD_DIR}/${pkg}-"*".dist-info" 2>/dev/null || true
done
# Also remove the .dist-info dirs for the removed packages (by name pattern)
rm -rf "${BUILD_DIR}/boto3-"*".dist-info" \
       "${BUILD_DIR}/botocore-"*".dist-info" \
       "${BUILD_DIR}/s3transfer-"*".dist-info" \
       "${BUILD_DIR}/urllib3-"*".dist-info" \
       "${BUILD_DIR}/jmespath-"*".dist-info" \
       "${BUILD_DIR}/python_dateutil-"*".dist-info" \
       "${BUILD_DIR}/six-"*".dist-info" 2>/dev/null || true

# ── 3. Copy handler source ───────────────────────────────────────────────────
# The Lambda handler is `handler.handler` (module=handler, func=handler), so
# handler.py MUST be at the ROOT of the zip (not nested under lambda/...).
# templates.py is imported by handler.py (flat layout at runtime) — also at root.
# __init__.py is empty but ships for package-context import parity (tests use
# `importlib.import_module("lambda.custom_email_sender.handler")`).
echo ">> Copying handler source to build root..."
cp "${BACKEND_DIR}/lambda/custom_email_sender/handler.py" \
   "${BUILD_DIR}/handler.py"
cp "${BACKEND_DIR}/lambda/custom_email_sender/templates.py" \
   "${BUILD_DIR}/templates.py"
cp "${BACKEND_DIR}/lambda/custom_email_sender/__init__.py" \
   "${BUILD_DIR}/__init__.py"

# ── 4. Verify the package structure ──────────────────────────────────────────
# Expected: handler.py, templates.py, sendgrid/, python_http_client/,
# starkbank_ecdsa/ — and NO boto3/, NO app/ (design §B self-contained).
echo ">> Verifying package structure..."
if [ ! -f "${BUILD_DIR}/handler.py" ]; then
  echo "ERROR: handler.py missing from build dir root" >&2
  exit 1
fi
if [ ! -f "${BUILD_DIR}/templates.py" ]; then
  echo "ERROR: templates.py missing from build dir root" >&2
  exit 1
fi
if [ ! -d "${BUILD_DIR}/sendgrid" ]; then
  echo "ERROR: sendgrid package missing from build dir" >&2
  exit 1
fi
if [ ! -d "${BUILD_DIR}/python_http_client" ]; then
  echo "ERROR: python_http_client package missing (sendgrid transitive dep)" >&2
  exit 1
fi
# starkbank-ecdsa installs its top-level import dir as `ellipticcurve/`
# (the dist-info is named starkbank_ecdsa, but the importable module is
# ellipticcurve). Verify the importable dir, not the dist-info name.
if [ ! -d "${BUILD_DIR}/ellipticcurve" ]; then
  echo "ERROR: ellipticcurve package missing (starkbank-ecdsa transitive dep)" >&2
  exit 1
fi

# AWS Encryption SDK — required for Cognito code decryption.
if [ ! -d "${BUILD_DIR}/aws_encryption_sdk" ]; then
  echo "ERROR: aws_encryption_sdk package missing" >&2
  exit 1
fi
# AWS Cryptographic Material Providers — provides the KMS keyring for the SDK.
if [ ! -d "${BUILD_DIR}/aws_cryptographic_material_providers" ]; then
  echo "ERROR: aws_cryptographic_material_providers package missing" >&2
  exit 1
fi
# cryptography — C-extension dep of aws-encryption-sdk (manylinux wheel).
if [ ! -d "${BUILD_DIR}/cryptography" ]; then
  echo "ERROR: cryptography package missing (aws-encryption-sdk dep)" >&2
  exit 1
fi

# Guard: boto3 must NOT be packaged (runtime-provided; packaging it bloats the
# zip and can cause version conflicts with the Lambda runtime's bundled copy).
if [ -d "${BUILD_DIR}/boto3" ]; then
  echo "ERROR: boto3 was packaged — it must NOT be (Lambda runtime provides it)." >&2
  echo "  Remove it from the build dir and re-run." >&2
  exit 1
fi

# Guard: app/ must NOT be present (design §B — self-contained, no DB deps).
if [ -d "${BUILD_DIR}/app" ]; then
  echo "ERROR: app/ directory present — this handler is self-contained (design §B)." >&2
  exit 1
fi

# Count installed packages
PKG_COUNT=$(find "${BUILD_DIR}" -maxdepth 1 -type d | tail -n +2 | wc -l | tr -d ' ')
echo "  Installed ${PKG_COUNT} top-level packages"

echo ""
echo "=== Build complete ==="
echo "  The Terraform data.archive_file.custom_email_sender resource will zip"
echo "  this directory at plan/apply time."
echo ""
echo "  Next: cd infrastructure/terraform/environments/production && terraform plan -target=module.security"
