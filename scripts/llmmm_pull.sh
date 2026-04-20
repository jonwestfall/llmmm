#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <base_url> <api_key> [profile]" >&2
  exit 1
fi

BASE_URL="$1"
API_KEY="$2"
PROFILE="${3:-default}"

curl -sS "${BASE_URL%/}/api/v1/context/pull?profile=${PROFILE}" \
  -H "X-API-Key: ${API_KEY}"
