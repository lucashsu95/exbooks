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

## 管理介面（MinIO / Mailpit）

`docker-compose.yml` 只把下列 port 綁在伺服器的 `127.0.0.1`，外部網路連不到；對外只開 nginx 的 `:80`（網站的媒體檔由 nginx 經 Docker 內部網路轉到 `minio:9000`，不需要對外開 MinIO）。

| 服務 | 伺服器本機位址 | 用途 |
|------|----------------|------|
| MinIO S3 API | `127.0.0.1:9002` | `mc` 等 S3 用戶端 |
| MinIO console | `127.0.0.1:9003` | 網頁管理介面（查看／下載備份） |
| Mailpit | `127.0.0.1:8025` | 檢視攔截的郵件 |

從自己的電腦管理時，用 SSH tunnel：

```bash
# MinIO console
ssh -L 9003:127.0.0.1:9003 <user>@<host>
# 然後在本機瀏覽器開 http://localhost:9003/

# 一次轉多個 port（S3 API、console、Mailpit），-N 表示只建 tunnel 不開 shell
ssh -N -L 9002:127.0.0.1:9002 -L 9003:127.0.0.1:9003 -L 8025:127.0.0.1:8025 <user>@<host>
```

建 tunnel 後，本機的 `mc` 可指向 `http://localhost:9002`：

```bash
mc alias set exbook-remote http://localhost:9002 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"
```
