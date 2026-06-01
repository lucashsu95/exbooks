#!/bin/sh
set -eu

# MariaDB 邏輯備份（gzip）。預設於 Compose 網路內對 host「db」連線。
# 環境變數：MARIADB_ROOT_PASSWORD（必填）、MARIADB_DATABASE（預設 exbook）、BACKUP_DIR（預設 /backup）

BACKUP_DIR="${BACKUP_DIR:-/backup}"
DB_NAME="${MARIADB_DATABASE:-exbook}"
DB_HOST="${MYSQL_HOST:-db}"

if [ -z "${MARIADB_ROOT_PASSWORD:-}" ]; then
  echo "Missing MARIADB_ROOT_PASSWORD" >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT="$BACKUP_DIR/exbook_${STAMP}.sql.gz"

export MYSQL_PWD="$MARIADB_ROOT_PASSWORD"
mysqldump \
  --single-transaction \
  --quick \
  --default-character-set=utf8mb4 \
  -h "$DB_HOST" \
  -uroot \
  "$DB_NAME" | gzip -c >"$OUT"

echo "Backup written: $OUT"
