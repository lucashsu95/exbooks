# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Exbooks 是公益性質的社群共享書籍平臺（Django 5.2）：成員上架自有藏書（SharedBook），透過交易（Deal）面交借用／返還／傳遞，並以信用分數管束行為。

## 常用指令

全部用 uv 執行（Python 3.12，`uv sync` 會裝 dev 群組；測試依賴要另加 `--group test`）。

```bash
uv sync --group test              # 安裝正式 + dev + test 依賴
cp .env.example .env              # 本地預設值即可，AI/Email/Push/物件儲存未設定時自動停用或 fallback
uv run python manage.py migrate
uv run python manage.py seed      # 假資料 + 示範帳號 admin@example.com/admin12345、reader@example.com/reader12345
uv run python manage.py runserver

uv run ruff check .               # CI lint（scripts/ 已排除）
uv run djlint templates --check   # 模板格式（profile=django）
uv run pytest                     # CI test
uv run pytest tests/deals/test_x.py::TestY::test_z   # 單一測試
uv run pytest -m "not slow"
```

- Browser e2e（`tests/e2e/`）需 `uv run playwright install chromium`，未安裝時自動略過。
- CI（`.github/workflows/ci.yml`）：lint → test 跑在 GitHub-hosted；deploy 只在上游 repo push 到 `master` 時於 self-hosted runner 執行 `scripts/deploy.sh`。預設分支是 `master`。

## 設定檔（容易踩錯）

- `manage.py` 預設 `exbook.dev_settings`（SQLite）；`wsgi.py` / `celery.py` 預設 `exbook.settings`（MariaDB）；`prod_settings.py` 給部署。
- 測試用 `exbook.test_settings`（pytest 設定已指定）：每次執行在 /tmp 建獨立 SQLite 檔，不需 MariaDB。
- 本地 `CELERY_TASK_ALWAYS_EAGER=true`，任務同步執行，不需 Redis/worker。
- 生產環境見 `docker-compose.yml`（db / web / celery_worker / celery_beat / nginx / redis / minio / mailpit；備份服務在 `backup` profile）。

## 架構

Django apps：`accounts`（會員、信任分數、違規／申訴）、`books`（書目與分享書籍）、`deals`（交易、延期、評價、通知、Web Push）、`ai`（AI 聊天助理，無 model）、`core`（基底 model、middleware、observability、共用 view）。

**分層約束（勿重新翻案）**：業務邏輯只放在各 app 的 `services/`，View 與 Model 不帶業務邏輯。Web 端（`views.py`，Django templates + htmx + Alpine.js + Tailwind CDN）與 REST API 端（`api_views.py` + `serializers.py`，DRF + SimpleJWT，`/api/token/`）共用同一組 service。

- **Model 位置**：`books/models/`、`deals/models/` 是 package；`accounts/models.py` 是單檔。基底類別在 `core/models.py`（`BaseModel` → `UpdatableModel`）。
- **狀態機**：Deal 與 SharedBook 的狀態用 django-fsm（`FSMField(protected=True)` + `@transition`），不能直接賦值 `status`，要走 transition（見 `docs/adr/django-fsm-migration.md`）。
  - Deal 類別：LN 借用、RS 返還、TF 傳遞、RG 回歸、EX 例外。
  - Deal 狀態：REQUESTED → RESPONDED → MEETED → DONE，或任一階段 CANCELLED。
  - 每次轉換由 `exchange_event_service` 寫入 ExchangeEvent 審計紀錄。
- **權限**：物件層級權限用 `rules`（如 `deals/rules.py` 的 predicates）；信用等級（TrustLevel 0–3）影響可借冊數、借期與編輯權限。
- **AI**：`ai/services/chat_orchestrator.py` 負責一輪對話（tool 呼叫迴圈、consent 決策、follow-up 呼叫、history 寫入），tools 註冊在 `tool_registry.py`，以 SSE 串流回前端。LLM 經 `sdk/python` 的 `ai-client` 套件（本地 path 依賴）呼叫 vLLM 的 OpenAI 相容端點；provider 透過 `AIClient` / `Transport` seam 注入（生產 `RequestsTransport`，測試用 scripted transport）。未設定 `VLLM_API_KEY` 時走 mock 回應。
- **前端寵物**：全站像素寵物「米豆 MeDou」在 `static/js/pixel-pet.js` + `static/css/pixel-pet.css`，由 `templates/base.html` 載入；精靈圖讀 `static/img/medou/medou-sheet.png`（由 `scripts/medou/build_sprites.py` 從 `docs/assets/medou/` 參考圖產生）。

## 測試結構

測試分散兩處：根目錄 `tests/`（依 app 分資料夾，含 `api/`、`e2e/`、`observability/`；`conftest.py` 與 factory-boy 的 `factories.py` 在這裡），以及部分 app 內的 `<app>/tests/`（`accounts`、`books`、`ai`）。`sdk/python/tests/` 是 SDK 自己的測試。

## 領域詞彙與已知債務

- 討論與命名使用 `GLOSSARY.md` 的詞彙（例如「發布 publish」「逾期 overdue」「AI 對話編排」），不要用函式名或類別名代替。業務規則以 BR-x 編號。
- `docs/adr/2026-10-24-architecture-followups.md` 列出已知但延後處理的問題，動到相關程式前先看。例如：
  - F-1：`Deal.cancel()` 直接改 protected FSM 欄位，被呼叫就會崩。
  - F-8：`_attach_cover` 直接抓取使用者輸入的 `cover_url`，有 SSRF 風險。
  - 注意：這份 ADR 的狀態可能落後於程式碼。例如 F-2 已在 master 修好（`create_deal` 已加 `@transaction.atomic`），文件還沒更新，引用前要對照程式確認。
- 設計 token（顏色、元件樣式）記錄在 `DESIGN.md`；其他文件索引見 `docs/index.md`。
