#!/usr/bin/env bash
# Copy shared/ into each service before sam build.
# Keeps shared/ as the single source of truth.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

for svc in ingest evaluate narrate api; do
    rm -rf "${REPO_ROOT}/services/${svc}/shared"
    cp -r "${REPO_ROOT}/shared" "${REPO_ROOT}/services/${svc}/shared"
done

echo "Shared code synced to all services."
