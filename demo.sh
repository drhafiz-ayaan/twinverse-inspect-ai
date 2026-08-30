#!/usr/bin/env bash
#
# Set up a complete inspection for a live demo, from nothing to a finished
# report, in one command.
#
#   ./demo.sh              8 images from the crack test set
#   ./demo.sh 12           a different number
#
# The dashboard has no upload control — it is a read-only view over the API —
# so this is how imagery gets in. Run it before you present, then again live if
# you want to show the pipeline actually working.
#
# Requires the stack to be up (infra/docker-compose.yml) and jq.

set -euo pipefail

API="${API:-http://localhost:8000/api/v1}"
DASHBOARD="${DASHBOARD:-http://localhost:3000}"
EMAIL="${ADMIN_EMAIL:-admin@twinverse-inspect.com}"
PASSWORD="${ADMIN_PASSWORD:-change-me-now-8chars}"
COUNT="${1:-8}"

IMAGE_DIR="ml/datasets/nitw-crack/test/images"

command -v jq >/dev/null || { echo "jq is required: sudo apt install -y jq"; exit 1; }
[ -d "$IMAGE_DIR" ] || { echo "no images at $IMAGE_DIR — fetch a dataset first"; exit 1; }

step() { printf '\n\033[36m▸ %s\033[0m\n' "$1"; }

step "Signing in as $EMAIL"
TOKEN=$(curl -fsS -X POST "$API/auth/login" \
  -H 'Content-Type: application/json' \
  -d "$(jq -n --arg e "$EMAIL" --arg p "$PASSWORD" '{email:$e,password:$p}')" \
  | jq -r .access_token)
AUTH=(-H "Authorization: Bearer $TOKEN")
echo "  token acquired"

step "Creating the asset"
ASSET=$(curl -fsS -X POST "$API/assets" "${AUTH[@]}" \
  -H 'Content-Type: application/json' \
  -d '{"name":"Riverside Viaduct","asset_type":"bridge",
       "location":"Sector 7, North Span",
       "description":"Demo asset created by demo.sh"}' | jq -r .id)
echo "  asset $ASSET"

step "Opening the inspection"
INSPECTION=$(curl -fsS -X POST "$API/inspections" "${AUTH[@]}" \
  -H 'Content-Type: application/json' \
  -d "$(jq -n --arg a "$ASSET" \
        '{asset_id:$a, title:"North span deck survey",
          notes:"Post-monsoon condition survey"}')" | jq -r .id)
echo "  inspection $INSPECTION"

step "Uploading $COUNT images"
# Build one multipart request; the API accepts up to 50 files and reports each
# file's outcome separately, so a single bad frame never sinks the batch.
FILES=()
while IFS= read -r f; do FILES+=(-F "files=@$f"); done \
  < <(find "$IMAGE_DIR" -name '*.jpg' | sort | head -n "$COUNT")
curl -fsS -X POST "$API/inspections/$INSPECTION/uploads" "${AUTH[@]}" "${FILES[@]}" \
  | jq -r '"  accepted \(.accepted_count), rejected \(.rejected_count)",
           (.results[] | select(.accepted | not) | "  ✗ \(.filename): \(.error)")'

step "Running detection"
curl -fsS -X POST "$API/inspections/$INSPECTION/detect" "${AUTH[@]}" >/dev/null

# Detection returns immediately and runs in the background, so poll the status
# rather than assuming it finished.
for _ in $(seq 1 60); do
  STATUS=$(curl -fsS "$API/inspections/$INSPECTION" "${AUTH[@]}" | jq -r .status)
  [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ] && break
  printf '  %s...\r' "$STATUS"
  sleep 2
done
echo "  status: $STATUS      "

step "Results"
curl -fsS "$API/inspections/$INSPECTION/detections/summary" "${AUTH[@]}" | jq -r '
  "  media analysed   \(.media_processed)/\(.media_total)",
  "  detections       \(.detection_total)",
  "  max severity     \(.max_severity_score // "—")",
  (.by_severity[] | "  \(.severity_band)\(" " * (17 - (.severity_band|length)))\(.count)")'

printf '\n\033[32m✓ Ready.\033[0m Open %s/inspections/%s\n\n' "$DASHBOARD" "$INSPECTION"
