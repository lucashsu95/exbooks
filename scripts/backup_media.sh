#!/bin/sh
set -eu

# MinIO Media Backup Script
# This script syncs local media to MinIO and cleans up old backups.

# Configuration from environment variables
MINIO_ENDPOINT="${MINIO_ENDPOINT}"
MINIO_ROOT_USER="${MINIO_ROOT_USER}"
MINIO_ROOT_PASSWORD="${MINIO_ROOT_PASSWORD}"
MEDIA_DIR="${MEDIA_DIR:-/media}"
BUCKET_NAME="exbook-media"
BACKUP_PATH="backups"

# Setup MinIO Client alias
mc alias set myminio "$MINIO_ENDPOINT" "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"

# Ensure target bucket exists
mc mb --ignore-existing myminio/"$BUCKET_NAME"

# Mirror local media to MinIO backups
# Using a timestamped folder to preserve versions as the previous script did
STAMP="$(date +%Y%m%d_%H%M%S)"
mc mirror "$MEDIA_DIR" "myminio/$BUCKET_NAME/$BACKUP_PATH/$STAMP"

# Remove backups older than 7 days
mc rm --recursive --older-than 7d "myminio/$BUCKET_NAME/$BACKUP_PATH/"

echo "Media backup completed to $BUCKET_NAME/$BACKUP_PATH/$STAMP"
