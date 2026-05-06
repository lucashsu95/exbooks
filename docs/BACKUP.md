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

目前媒體掛載於命名 volume `media_data`。請另行以：

- 週期性將 volume 掛載到備份主機並 `rsync`／快照，或
- 物件儲存（S3 相容）同步策略

納入備援計畫；腳本未自動備份媒體。

## Redis

Redis 使用 `redis_data` volume，設定為 AOF（`appendonly yes`）。若僅作快取／短期佇列可接受重建；若有業務不可失資料，請評估 RDB／AOF 複製或托管服務。
