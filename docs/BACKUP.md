# 資料備份（MariaDB／媒體／Redis）

## MariaDB 邏輯備份

使用 Compose profile `backup`，會啟動與 `db` 相同映像的短期容器，執行 `scripts/backup_mysql.sh`，將 `mysqldump` 結果 gzip 寫入 volume `backup_data`。

```bash
docker compose --profile backup run --rm backup
```

備份檔路徑形如：`/backup/exbook_YYYYMMDD_HHMMSS.sql.gz`（容器內）；資料會落在 Docker volume `exbook_backup_data`（專案前綴依資料夾名稱而定）。

還原範例（將備份檔複製到本機後）：

```bash
gunzip -c exbook_YYYYMMDD_HHMMSS.sql.gz | docker compose exec -T db mariadb -uroot -p"$DB_PASSWORD" "$DB_NAME"
```

`.env` 需提供與 `docker-compose.yml` 中 `db` 服務一致的 `DB_PASSWORD`、`DB_NAME`（選填，預設 `exbook`）。

## 媒體檔（media）

使用 Compose profile `backup` 的 `media_backup` 服務，會將 `media_data` volume 打包成 `tar.gz`，寫入 `backup_data`。

```bash
docker compose --profile backup run --rm media_backup
```

如果你要把備份推到外部儲存，請在容器外再把 `backup_data` 中的檔案同步到 S3、NAS，或其他備份主機。

## Redis

使用 Compose profile `backup` 的 `redis_backup` 服務，會透過 `redis-cli --rdb` 產生 RDB 快照，寫入 `backup_data`。

```bash
docker compose --profile backup run --rm redis_backup
```

Redis 目前啟用 AOF，若只作快取／短期佇列可接受重建；若有業務不可失資料，建議再把 `backup_data` 同步到外部儲存，或改用托管服務。
