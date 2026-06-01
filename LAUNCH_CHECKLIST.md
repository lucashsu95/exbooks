# Exbooks 上線前檢查清單

> 最後更新：2026-05-26
> 狀態：✅ 業務功能完整，但營運面需補強

---

## CRITICAL（上線前必須處理）

- [x] **Production LOGGING** — 在 `exbook/prod_settings.py` 加入 Django logging 設定，輸出到 stdout 或檔案
- [x] **自訂錯誤頁面** — 建立 `templates/404.html`、`templates/500.html`、`templates/403.html`
- [x] **錯誤監控** — 整合 `sentry-sdk`，即時掌握 production 錯誤
- [x] **Health check 端點** — 新增 `GET /health/` 回傳 200 + DB 連線狀態
- [x] **API Rate Limiting** — 在 `REST_FRAMEWORK` 設定中加入 `DEFAULT_THROTTLE_CLASSES`
- [x] **資料庫連線池** — 在 `prod_settings.py` 的 `DATABASES["default"]["OPTIONS"]` 中加入 `CONN_MAX_AGE=600`

## HIGH（上線前建議完成）

- [ ] **SSL 終止確認** — 確認上線環境有外層 reverse proxy 處理 HTTPS（Cloudflare / Traefik / nginx SSL）
- [ ] **Media 備份** — 加上使用者上傳照片的備份機制（rsync 到外部儲存 / S3）
- [ ] **Deploy health verification** — 在 `scripts/deploy.sh` 加入 `/health/` 端點輪詢，確認 app 真正正常
- [ ] **Container 資源限制** — 在 `docker-compose.yml` 加入 web/celery 的 CPU 與記憶體上限
- [ ] **Redis 備份** — 定期備份 `redis_data` volume（AOF snapshot 抄寫到外部儲存）

## MEDIUM（上線後儘快補）

- [ ] **壓力測試** — 用 `locust` 或 `k6` 跑一次基本場景測試，確認瓶頸
- [ ] **非同步 Email 測試** — production 啟用 SMTP 前先用 mailtrap.io 驗證流程
- [ ] **正式域名 SSL 憑證** — 若自管 nginx 需加 certbot/LetsEncrypt 自動續約
