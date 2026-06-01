#!/bin/sh
set -eu

# 媒體備份（tar.gz）。預設將 media volume 打包到 /backup。
# 環境變數：BACKUP_DIR（預設 /backup）、MEDIA_DIR（預設 /media）

BACKUP_DIR="${BACKUP_DIR:-/backup}"
MEDIA_DIR="${MEDIA_DIR:-/media}"

mkdir -p "$BACKUP_DIR"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT="$BACKUP_DIR/exbook_media_${STAMP}.tar.gz"

if [ ! -d "$MEDIA_DIR" ]; then
  echo "Missing media directory: $MEDIA_DIR" >&2
  exit 1
fi

tar -czf "$OUT" -C "$MEDIA_DIR" .

echo "Backup written: $OUT"
