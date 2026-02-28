#!/usr/bin/env bash
set -euo pipefail

# Smoke test script for apps/web/pages/03_Train.py button flows.
#
# Usage:
#   bash scripts/test_train_page_buttons.sh
#   bash scripts/test_train_page_buttons.sh --live
#
# Optional env overrides:
#   REACHY_API_BASE=http://10.0.4.130:8083
#   REACHY_GATEWAY_BASE=http://10.0.4.130:8000
#   RUN_ID=run_1234
#   SEED=42
#   PREPARE_DRY_RUN=true

MEDIA_BASE="${REACHY_API_BASE:-http://localhost:8083}"
GATEWAY_BASE="${REACHY_GATEWAY_BASE:-http://localhost:8000}"
RUN_ID="${RUN_ID:-run_$(printf '%04d' $((RANDOM % 10000)))}"
SEED="${SEED:-42}"
PREPARE_DRY_RUN="${PREPARE_DRY_RUN:-true}"
INCLUDE_LIVE=0

if [[ "${1:-}" == "--live" ]]; then
  INCLUDE_LIVE=1
fi

if ! [[ "$RUN_ID" =~ ^run_[0-9]{4}$ ]]; then
  echo "ERROR: RUN_ID must match run_xxxx (received: $RUN_ID)" >&2
  exit 1
fi

request() {
  local method="$1"
  local url="$2"
  local body="${3:-}"

  local tmp
  tmp="$(mktemp)"
  local code

  if [[ -n "$body" ]]; then
    code="$(curl -sS -o "$tmp" -w "%{http_code}" -X "$method" "$url" \
      -H "Content-Type: application/json" \
      -d "$body")"
  else
    code="$(curl -sS -o "$tmp" -w "%{http_code}" -X "$method" "$url")"
  fi

  echo
  echo "[$method] $url -> HTTP $code"
  cat "$tmp"
  echo
  rm -f "$tmp"

  if [[ "$code" -ge 400 ]]; then
    return 1
  fi
}

echo "== Train Page Button Smoke Test =="
echo "MEDIA_BASE=$MEDIA_BASE"
echo "GATEWAY_BASE=$GATEWAY_BASE"
echo "RUN_ID=$RUN_ID"
echo "SEED=$SEED"
echo "PREPARE_DRY_RUN=$PREPARE_DRY_RUN"
echo "INCLUDE_LIVE=$INCLUDE_LIVE"

echo
echo "1) Health checks (backend availability)"
request GET "$MEDIA_BASE/api/v1/health"
request GET "$GATEWAY_BASE/api/v1/health"

echo
echo "2) Rebuild Manifests button"
request POST "$MEDIA_BASE/api/v1/ingest/manifest/rebuild" \
  "{\"splits\":[\"train\",\"test\"],\"correlation_id\":\"cli-smoke-$RUN_ID\"}"

echo
echo "3) Prepare 10-Frame Run button (inherits Dry run toggle)"
request POST "$MEDIA_BASE/api/v1/ingest/prepare-run-frames" \
  "{\"run_id\":\"$RUN_ID\",\"train_fraction\":0.8,\"seed\":$SEED,\"dry_run\":$PREPARE_DRY_RUN,\"face_crop\":false,\"face_target_size\":224,\"face_confidence\":0.6,\"split_run\":false,\"split_train_ratio\":0.9,\"strip_valid_labels\":true,\"persist_valid_metadata\":false,\"correlation_id\":\"cli-prepare-$RUN_ID\"}"

echo
echo "4) Manual Validate Plan button (forced dry_run=true)"
request POST "$MEDIA_BASE/api/v1/ingest/prepare-run-frames" \
  "{\"run_id\":\"$RUN_ID\",\"train_fraction\":0.8,\"seed\":$SEED,\"dry_run\":true,\"face_crop\":false,\"face_target_size\":224,\"face_confidence\":0.6,\"split_run\":false,\"split_train_ratio\":0.9,\"strip_valid_labels\":true,\"persist_valid_metadata\":false,\"correlation_id\":\"cli-validate-$RUN_ID\"}"

if [[ "$INCLUDE_LIVE" -eq 1 ]]; then
  echo
  echo "5) Manual Execute Live button (forced dry_run=false, split_run=true)"
  request POST "$MEDIA_BASE/api/v1/ingest/prepare-run-frames" \
    "{\"run_id\":\"$RUN_ID\",\"train_fraction\":0.8,\"seed\":$SEED,\"dry_run\":false,\"face_crop\":false,\"face_target_size\":224,\"face_confidence\":0.6,\"split_run\":true,\"split_train_ratio\":0.9,\"strip_valid_labels\":true,\"persist_valid_metadata\":true,\"correlation_id\":\"cli-live-$RUN_ID\"}"
else
  echo
  echo "5) Manual Execute Live button skipped (pass --live to enable writes)"
fi

echo
echo "6) Generate New Run ID button equivalent"
echo "Generated shell run id example: run_$(printf '%04d' $((RANDOM % 10000)))"

echo
echo "7) Refresh Training Status button"
# Seed a status snapshot so GET for RUN_ID is meaningful in a fresh environment.
request POST "$GATEWAY_BASE/api/training/status/$RUN_ID" \
  "{\"status\":\"training\",\"metrics\":{\"source\":\"cli-smoke\",\"progress\":0.1}}"
request GET "$GATEWAY_BASE/api/training/status/$RUN_ID"
request GET "$GATEWAY_BASE/api/training/status/latest"

echo
echo "Smoke test completed."
