#!/usr/bin/env bash
# check_image_hygiene.sh [IMAGE ...] — runbook §19.7: built images must NOT contain /app/.env
#
# Default: pilot-api:latest pilot-web:latest. Exit 0 = all clean; exit 1 = violation found.
#
# Usage:
#   ./admin-tools/check_image_hygiene.sh                          # check default images
#   ./admin-tools/check_image_hygiene.sh pilot-api:latest         # check specific image
#   ./admin-tools/check_image_hygiene.sh pilot-api:latest pilot-web:latest pilot-celery_worker:latest
#
# Context: 2026-08-10 incident — backend Dockerfile COPY . . shipped backend/.env into prod
# images at /app/.env because no .dockerignore existed. This script mechanizes the manual
# check documented in aws-ops-runbook.md §19.7.
set -euo pipefail

# Default images (from §8.1/§8.3 build commands)
DEFAULT_IMAGES="pilot-api:latest pilot-web:latest"

# Use provided args or fall back to defaults
if [ "$#" -gt 0 ]; then
    images=("$@")
else
    # shellcheck disable=SC2206  # intentional word-splitting of the default list
    images=($DEFAULT_IMAGES)
fi

fail=0

for img in "${images[@]}"; do
    # Check if the image exists locally
    if ! docker image inspect "$img" >/dev/null 2>&1; then
        echo "  ⚠️  SKIP $img — image not found locally"
        continue
    fi

    out=$(docker run --rm --entrypoint sh "$img" -c 'ls /app/.env 2>&1' || true)

    if echo "$out" | grep -q "No such file"; then
        echo "  ✅ PASS $img — no /app/.env"
    else
        echo "  ❌ FAIL $img — /app/.env FOUND in image ($out)"
        fail=1
    fi
done

if [ "$fail" -eq 1 ]; then
    echo ""
    echo "  Image hygiene check FAILED — rebuild with .dockerignore in place."
    echo "  See aws-ops-runbook.md §19.7 for remediation steps."
fi

exit "$fail"
