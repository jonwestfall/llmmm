#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="${ROOT_DIR}/data"
BACKUP_DIR="${DATA_DIR}/backups"
TS="$(date +"%Y%m%d_%H%M%S")"
ARCHIVE="${BACKUP_DIR}/llmmm_backup_${TS}.tar.gz"

mkdir -p "${BACKUP_DIR}"

if [[ ! -d "${DATA_DIR}" ]]; then
  echo "Data directory not found: ${DATA_DIR}" >&2
  exit 1
fi

tar -czf "${ARCHIVE}" -C "${ROOT_DIR}" data

echo "Backup created: ${ARCHIVE}"
