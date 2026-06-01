#!/bin/sh
set -eu

# Redis 邏輯備份（RDB）。使用 redis-cli 對 compose 內的 redis 服務產生快照。
# 環境變數：REDIS_HOST（預設 redis）、REDIS_PORT（預設 6379）、BACKUP_DIR（預設 /backup）

BACKUP_DIR="${BACKUP_DIR:-/backup}"
REDIS_HOST="${REDIS_HOST:-redis}"
REDIS_PORT="${REDIS_PORT:-6379}"

mkdir -p "$BACKUP_DIR"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT="$BACKUP_DIR/exbook_redis_${STAMP}.rdb"

redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" --rdb "$OUT"

echo "Backup written: $OUT"
