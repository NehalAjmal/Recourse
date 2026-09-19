#!/usr/bin/env bash
# Copy shared/ into each service before sam build.
# Keeps shared/ as the single source of truth.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

for svc in ingest evaluate narrate api; do
    rm -rf "${REPO_ROOT}/services/${svc}/shared"
    cp -r "${REPO_ROOT}/shared" "${REPO_ROOT}/services/${svc}/shared"
done

# Copy eval and holdout to api so /metrics can read them
rm -rf "${REPO_ROOT}/services/api/eval"
cp -r "${REPO_ROOT}/eval" "${REPO_ROOT}/services/api/eval"
cp "${REPO_ROOT}/data/seed/holdout.json" "${REPO_ROOT}/services/api/holdout.json"

echo "Shared code synced to all services."
