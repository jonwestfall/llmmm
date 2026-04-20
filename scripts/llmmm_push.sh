#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "Usage: $0 <base_url> <api_key> <title> [body_file] [tags_csv] [source_model]" >&2
  exit 1
fi

BASE_URL="$1"
API_KEY="$2"
TITLE="$3"
BODY_FILE="${4:-}"
TAGS="${5:-}"
SOURCE_MODEL="${6:-cli}"

if [[ -n "${BODY_FILE}" ]]; then
  if [[ ! -f "${BODY_FILE}" ]]; then
    echo "Body file not found: ${BODY_FILE}" >&2
    exit 1
  fi
  BODY_CONTENT="$(cat "${BODY_FILE}")"
else
  BODY_CONTENT="${TITLE}"
fi

JSON_PAYLOAD=$(jq -n \
  --arg title "${TITLE}" \
  --arg body "${BODY_CONTENT}" \
  --arg source_model "${SOURCE_MODEL}" \
  --arg tags_csv "${TAGS}" \
  '{title:$title, body:$body, source_model:$source_model, tags:($tags_csv|split(",")|map(gsub("^\\s+|\\s+$";""))|map(select(length>0))), importance:3, pinned:false, metadata:{source:"script"}}')

curl -sS "${BASE_URL%/}/api/v1/memories" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d "${JSON_PAYLOAD}"
