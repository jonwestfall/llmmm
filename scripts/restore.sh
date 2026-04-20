#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <backup-archive.tar.gz> --yes" >&2
  exit 1
fi

ARCHIVE="$1"
CONFIRM="$2"
if [[ "${CONFIRM}" != "--yes" ]]; then
  echo "Refusing to restore without --yes" >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="${ROOT_DIR}/data"

if [[ ! -f "${ARCHIVE}" ]]; then
  echo "Backup file not found: ${ARCHIVE}" >&2
  exit 1
fi

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

tar -xzf "${ARCHIVE}" -C "${TMP_DIR}"

if [[ ! -d "${TMP_DIR}/data" ]]; then
  echo "Archive does not contain a data directory" >&2
  exit 1
fi

rm -rf "${DATA_DIR}"
mv "${TMP_DIR}/data" "${DATA_DIR}"

echo "Restore completed from ${ARCHIVE}"
