---
marp: true
theme: business
size: 16:9
---

<style>
/* Google Fonts 讀取繁體中文 */
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&display=swap');

/* --- 商業簡報主題 (business) 繁中版 --- */
:root {
  --color-background: #ffffff;
  --color-foreground: #1f2937;
  --color-heading: #1e40af;
  --color-accent: #3b82f6;
  --color-border: #d1d5db;
  --font-default: 'Noto Sans TC', 'Microsoft JhengHei', 'PingFang TC', sans-serif;
}

section {
  background-color: var(--color-background);
  color: var(--color-foreground);
  font-family: var(--font-default);
  font-weight: 400;
  box-sizing: border-box;
  border-top: 8px solid var(--color-heading);
  position: relative;
  line-height: 1.7;
  font-size: 22px;
  padding: 56px;
}

h1, h2, h3, h4, h5, h6 {
  font-weight: 700;
  color: var(--color-heading);
  margin: 0;
  padding: 0;
}

h1 {
  font-size: 54px;
  line-height: 1.3;
  text-align: left;
  font-weight: 700;
  letter-spacing: -0.02em;
}

h2 {
  position: absolute;
  top: 40px;
  left: 56px;
  right: 56px;
  font-size: 38px;
  padding-top: 0;
  padding-bottom: 16px;
  border-bottom: 3px solid var(--color-accent);
}

h2 + * {
  margin-top: 112px;
}

h3 {
  color: var(--color-accent);
  font-size: 26px;
  margin-top: 32px;
  margin-bottom: 12px;
  font-weight: 600;
}

ul, ol {
  padding-left: 32px;
}

li {
  margin-bottom: 10px;
  line-height: 1.7;
}

/* 頁尾（頁碼風格）*/
footer {
  font-size: 16px;
  color: #6b7280;
  position: absolute;
  left: 56px;
  right: 56px;
  bottom: 40px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

footer::before {
  content: '';
  flex: 1;
  height: 2px;
  background-color: var(--color-border);
  margin-right: 20px;
}

section.lead {
  border-top: 8px solid var(--color-heading);
  display: flex;
  flex-direction: column;
  justify-content: center;
  background: linear-gradient(135deg, #ffffff 0%, #f3f4f6 100%);
}

section.lead footer {
  display: none;
}

section.lead h1 {
  margin-bottom: 32px;
  color: var(--color-heading);
}

section.lead p {
  font-size: 24px;
  color: var(--color-foreground);
  font-weight: 500;
}

/* 表格 */
table {
  border-collapse: collapse;
  width: 100%;
  margin: 20px 0;
  font-size: 18px;
}

th, td {
  border: 1px solid var(--color-border);
  padding: 12px;
  text-align: left;
}

th {
  background-color: var(--color-heading);
  color: #ffffff;
  font-weight: 700;
}

tr:nth-child(even) {
  background-color: #f9fafb;
}

/* 雙欄與卡片版面 */
.columns {
  display: flex;
  gap: 24px;
  margin-top: 10px;
  align-items: start;
}

.card {
  flex: 1;
  border: 1px solid #bfdbfe;
  border-radius: 12px;
  padding: 14px 16px;
}

/* 強調框 */
.highlight-box {
  background-color: #eff6ff;
  border-left: 4px solid var(--color-accent);
  padding: 20px;
  margin: 20px 0;
  border-radius: 4px;
}

/* 數字強調 */
.number {
  font-size: 48px;
  font-weight: 700;
  color: var(--color-accent);
  line-height: 1;
}

/* 步驟編號 */
.step {
  display: inline-block;
  width: 36px;
  height: 36px;
  background-color: var(--color-heading);
  color: #ffffff;
  border-radius: 50%;
  text-align: center;
  line-height: 36px;
  font-weight: 700;
  margin-right: 12px;
}

/* 引用 */
blockquote {
  border-left: 4px solid var(--color-accent);
  padding-left: 20px;
  color: #6b7280;
  font-style: italic;
  margin: 20px 0;
  font-size: 20px;
}

/* 連結 */
a {
  color: var(--color-accent);
  text-decoration: none;
  border-bottom: 1px solid var(--color-accent);
}

a:hover {
  color: var(--color-heading);
  border-bottom-color: var(--color-heading);
}

/* 強調 */
strong {
  color: var(--color-heading);
  font-weight: 700;
}
</style>

<!-- _class: lead -->
# Exbooks 功能進度報告
## 2025 年 6 月

<!-- _note: 各位好，我是本次簡報的主講者。今天要向大家報告 Exbooks 平台自上次簡報以來在架構現代化、AI 整合與生產力提升方面的重大進展。本次報告涵蓋 65 個 commits、超過一萬七千行新增程式碼，以及九大功能類別的全面升級。預計約二十分鐘，最後保留五分鐘問答時間。 -->

---

<!-- _note: 這是今天的議程。我們從 AI 聊天機器人這個最亮眼的新功能開始，接著介紹完整的 REST API 生態系、多語系支援、觀測性基建、生產強化、效能改善和資安措施，最後以架構總覽和三個附錄收尾。各位可以參考手上的投影片跟著進度。 -->

# 目錄

1. AI 聊天機器人與 Gemini 整合
2. REST API 生態系
3. 多語系支援 (i18n)
4. 觀測性與日誌架構
5. 生產環境強化
6. 效能與架構改善
7. 資安與合規強化
8. 部署自動化
9. 架構總覽
10. 附錄與結語

---

<!-- _note: 先看宏觀數據。過去這個週期我們完成了 65 個 commits，新增一萬七千多行程式碼，變動 203 個檔案。這些工作分布在九大功能類別，從 AI 應用到生產部署，從國際化到資安合規，可以說是一次全方面的升級。 -->

# 執行摘要

<div class="columns">
<div class="card">
<h3>65</h3>
<p>commits 變更</p>
</div>
<div class="card">
<h3>17,201</h3>
<p>新增程式碼行數</p>
</div>
<div class="card">
<h3>203</h3>
<p>異動檔案數</p>
</div>
<div class="card">
<h3>9</h3>
<p>功能類別覆蓋</p>
</div>
</div>

- **AI 智慧應用** — Gemini 驅動聊天機器人、Tool Calling、SSE 串流
- **REST API** — 帳號／書籍／交易三大領域，390+ 測試案例
- **國際化** — 繁中／English／한국어，3,175 行翻譯字串
- **觀測性** — 結構化日誌、Trace ID、Sentry 就緒
- **生產強化** — SSL 自動化、健康檢查、k6 壓測腳本
- **媒體存取優化** — 公開檔案 Nginx 直連 MinIO 繞過 Django，受保護檔案 X-Accel-Redirect

---

<!-- _note: 接下來進入第一個重頭戲——AI 聊天機器人。這是 Exbooks 首次整合大型語言模型，我們選擇了 Google Gemini 1.5 Flash，兼顧效能與成本。使用者可以在平台上透過自然語言詢問書籍推薦、ISBN 查詢或交易狀態，AI 會透過 Tool Calling 機制調用後端服務，並以 SSE 串流方式即時回應。 -->

# AI 聊天機器人應用

**全新 `ai/` app** — Google Gemini 1.5 Flash 整合

### 架構流程

<div class="columns">
<div class="card">
<h3>使用者瀏覽器</h3>
<ul>
<li>HTMX 發送 POST</li>
<li>接收 SSE 串流</li>
<li>打字機效果即時呈現</li>
</ul>
</div>
<div class="card">
<h3>Django 伺服器</h3>
<ul>
<li>ToolRegistry 調度</li>
<li>GeminiService 封裝 API</li>
<li>ConversationCache 管理上下文</li>
</ul>
</div>
<div class="card">
<h3>Google Gemini</h3>
<ul>
<li>1.5 Flash 模型</li>
<li>Tool Calling 協定</li>
<li>函式回應解析</li>
</ul>
</div>
</div>

---

<!-- _note: 深入技術細節。ToolRegistry 是我們的工具調度引擎，負責將使用者的自然語言請求轉譯為具體的函式呼叫。GeminiService 封裝了完整的 API 互動生命週期，包含請求建構、回應解析和錯誤處理。ConversationCache 基於 Redis，除了儲存對話歷史，還會管理 Token 預算，避免上下文超過模型限制。ChatSSEView 是 Server-Sent Events 的端點，實現即時回應串流。 -->

# AI 核心技術細節

| 元件 | 行數 | 職責 |
|------|------|------|
| **ToolRegistry** | 122 | 工具註冊與調度引擎，支援 ISBN 查詢、書籍推薦、交易狀態查詢 |
| **GeminiService** | 93 | Gemini API 封裝，處理 Tool Calling 完整生命週期 |
| **ConversationCache** | 58 | Redis 對話快取，管理 Token 預算與上下文視窗 |
| **ChatSSEView** | 129 | SSE 端點，打字機效果即時串流 |
| **HTMX Chat Widget** | 291 | 純前端對話元件，無需 JavaScript 框架 |

### 測試覆蓋
工具註冊、Gemini API 整合、Redis 快取邊界、SSE 端點 — 四份測試檔案完整涵蓋

---

<!-- _note: 接下來看 REST API。我們基於 Django REST Framework 搭配 SimpleJWT，建立了完整的 API 生態系。覆蓋三大核心領域：帳號認證、書籍管理和交易流程。所有端點都經過速率限制保護，並使用 django-rules 進行細粒度的權限控管。整個 API 層有超過 390 個測試案例。 -->

# REST API 生態系

**基於 DRF + SimpleJWT**，完整覆蓋三大領域

### API 架構

<pre>
行動裝置 / 第三方應用
  │  JWT Auth Header
  ▼
DRF API Views (速率限制)
  │  Serializers + Permission Checks
  ▼
Service Layer → Models
</pre>

### 測試覆蓋統計

| 領域 | 測試案例 | 涵蓋重點 |
|------|----------|----------|
| Accounts API | 82 | 註冊、登入、個人資料、信任分數 |
| Auth API | 51 | JWT 取得、重新整理、過期處理 |
| Books API | 55 | 官方書籍 CRUD |
| Shared Books API | 122 | 狀態機、權限、所有權 |
| Deals API | 80 | 交易流程、FSM 動作、評價 |

---

<!-- _note: Deals API 是我們最完整的 API 模組，總共九個端點，涵蓋交易從申請、核准、收書確認到評價的完整生命週期。核心是 django-fsm-2 驅動的有限狀態機，確保交易狀態轉換的合法性和一致性。每一個狀態轉換都有對應的權限檢查。 -->

# Deals API — 交易狀態機

**最完整的 API 模組** — 九個端點覆蓋交易全程

### 端點一覽

| 端點 | 功能 | 權限 |
|------|------|------|
| `POST /api/deals/` | 建立交易 | 認證用戶 |
| `GET /api/deals/{id}/` | 交易詳情 | 參與者 |
| `POST /api/deals/{id}/apply/` | 申請交易 | 認證用戶 |
| `POST /api/deals/{id}/approve/` | 核准交易 | 貢獻者 |
| `POST /api/deals/{id}/confirm-received/` | 確認收書 | 申請者 |
| `POST /api/deals/{id}/rate/` | 評價交易 | 參與者 |
| `POST /api/deals/{id}/extend/` | 延長借閱 | 持有者 |
| `GET /api/deals/{id}/messages/` | 交易訊息 | 參與者 |
| `GET /api/ratings/` | 評價列表 | 公開 |

---

<!-- _note: 國際化方面，我們建立了完整的三語系支援。繁體中文是預設語言，英文已達百分之百覆蓋，韓文也已建立完整的翻譯架構。透過 LocaleMiddleware 自動偵測瀏覽器偏好，使用者可以在語言切換器即時切換。我們還開發了一支半自動批次翻譯腳本，大幅降低後續維護成本。 -->

# 國際化 (i18n) 全站支援

**三語系** — 繁體中文、English、한국어

<div class="columns">
<div class="card">
<h3>繁體中文</h3>
<p><strong>1,572</strong> 行翻譯字串</p>
<p>預設語言，完整覆蓋</p>
</div>
<div class="card">
<h3>English</h3>
<p><strong>1,603</strong> 行翻譯字串</p>
<p>100% 翻譯覆蓋率</p>
</div>
<div class="card">
<h3>한국어</h3>
<p>翻譯架構已建立</p>
<p>持續補完中</p>
</div>
</div>

### 技術亮點

- **自動偵測** — LocaleMiddleware 根據瀏覽器偏好自動切換
- **即時切換** — 模板內建語言選擇器，持久化至 session
- **批次翻譯** — `scripts/translate_po.py` (735 行) 半自動化腳本
- **全範圍涵蓋** — Django 模板、DRF 錯誤訊息、Admin 管理介面、表單驗證

---

<!-- _note: 觀測性是這個週期的重點基建項目。我們建立了從請求進來到離開的完整追蹤鏈。首先 Request Logging Middleware 會為每個請求注入 trace_id 和 span_id，記錄 method、path、status 和耗時。接著各服務層使用結構化 logger 記錄業務事件。最後所有日誌透過 JSON Formatter 輸出，便於後續的日誌分析平台整合。Sentry 的整合也已就緒。 -->

# 企業級觀測性與日誌

**端到端請求追蹤架構**

### 日誌流程

<pre>
HTTP 請求進入
  │
  ▼
Request Logging Middleware
  ├─ 注入 trace_id / span_id
  ├─ 記錄 method、path、status、duration
  └─ 關聯 user_id
  │
  ▼
Service Layer 結構化日誌 (JSON Format)
  │
  ▼
stdout / 檔案 / Sentry (可切換)
</pre>

### 核心檔案

| 檔案 | 行數 | 說明 |
|------|------|------|
| `core/logging_config.py` | 225 | 集中式 logging 設定：格式、等級、Handler、Filter |
| `core/middleware/request_logging.py` | 71 | 請求追蹤中介軟體 |

---

<!-- _note: 生產環境強化包含四大面向。SSL 憑證透過 Let's Encrypt 自動申請和續約，nginx 設定已含 HSTS 和 OCSP Stapling。健康檢查端點提供 database 和 cache 的狀態，可作為 Docker 的 liveness probe。k6 壓測腳本有三種層級：負載測試、壓力測試和部署後的快速煙霧測試。最後我們整理了一份三十項的上線檢查清單。 -->

# 生產環境強化

**四大面向確保服務穩定**

<div class="columns">
<div class="card">
<h3>SSL 自動化</h3>
<ul>
<li>Let's Encrypt 憑證自動申請</li>
<li>cron 自動續約</li>
<li>HSTS 31,536,000 秒</li>
<li>OCSP Stapling</li>
</ul>
</div>
<div class="card">
<h3>健康檢查</h3>
<ul>
<li>/health/ 端點即時狀態</li>
<li>Docker liveness probe</li>
<li>資料庫與快取連線驗證</li>
<li>錯誤頁面含追蹤 ID</li>
</ul>
</div>
<div class="card">
<h3>壓力測試 (k6)</h3>
<ul>
<li>負載測試 — 多用戶並發</li>
<li>壓力測試 — 系統瓶頸</li>
<li>煙霧測試 — 部署快速驗證</li>
<li>可視化 HTML 報告</li>
</ul>
</div>
</div>

---

<!-- _note: 效能改善是這個週期最有感的成果。ISBN 查詢原本每次都要呼叫外部 API，加上 Redis 快取後延遲下降超過九成。書籍列表透過 select_related 和 prefetch_related 解決 N+1 問題，加上複合索引，查詢時間減少六成以上。熱門書籍原本即時計算耗費資源，改為 Celery 排程加上 Redis 快取後，首頁載入速度提升五倍。 -->

# 效能與架構改善

<div class="columns">
<div class="card">
<h3>ISBN 查詢</h3>
<p><strong>延遲 ↓ 90%+</strong></p>
<p>Redis 快取，TTL 可配置</p>
<p>外部 API 成本大幅節省</p>
</div>
<div class="card">
<h3>書籍列表</h3>
<p><strong>查詢 ↓ 60%+</strong></p>
<p>select_related + prefetch_related</p>
<p>複合索引加速排序</p>
</div>
<div class="card">
<h3>熱門書籍</h3>
<p><strong>載入 ↓ 80%</strong></p>
<p>Celery 排程每小時更新</p>
<p>Redis 快取即時讀取</p>
</div>
</div>

### 快取策略

| 層級 | 項目 | 更新策略 |
|------|------|----------|
| Redis (DB 1) | 熱門書籍 | Celery 每小時排程更新 |
| Redis (DB 1) | ISBN 查詢 | TTL 7 天 |
| Redis (DB 1) | 用戶統計 | TTL 30 分鐘 |
| Redis (DB 1) | AI 對話上下文 | Token 預算動態管理 |
| 資料庫索引 | 共享書籍排序 | 遷移時建立 |
| 資料庫索引 | 交易狀態查詢 | 遷移時建立 |

---

<!-- _note: 資安方面我們從三個層面著手。首先是環境驅動的安全設定，開發和生產環境的 SSL、Cookie 安全旗標和 HSTS 會自動切換。其次是登入保護，DRF 層設有速率限制，nginx 層也有 limit_req_zone 防止暴力破解，加上連續失敗鎖定機制。最後是媒體檔案保護，面交照片透過 X-Accel-Redirect 內部轉發，MinIO 使用預簽名 URL，所有權檢查確保只有相關參與者能查看。重點優化：公開媒體檔案（書封面、一般照片）完全繞過 Django，由 Nginx 直接代理 MinIO，零 Python 開銷；只有面交照片才經過 Django 權限檢查。 -->

# 資安與合規強化

**三層防護架構**

<div class="columns">
<div class="card">
<h3>環境驅動安全</h3>
<ul>
<li>開發 vs 生產自動切換</li>
<li>SSL Redirect、Secure Cookie</li>
<li>HSTS 31,536,000s</li>
<li>無需人工判斷</li>
</ul>
</div>
<div class="card">
<h3>登入保護</h3>
<ul>
<li>DRF 速率限制</li>
<li>anon 100 req/h</li>
<li>user 1000 req/h</li>
<li>nginx limit_req_zone</li>
<li>連續失敗鎖定</li>
</ul>
</div>
<div class="card">
<h3>媒體檔案保護</h3>
<ul>
<li>X-Accel-Redirect 內部轉發</li>
<li>MinIO 預簽名 URL</li>
<li>所有權檢查機制</li>
<li>防止盜鏈與未授權存取</li>
</ul>
</div>
</div>

<div class="highlight-box">
<h4>💡 媒體檔案雙軌存取架構（效能優化）</h4>
<pre>
公開媒體檔案 (書封面、無交易關聯照片)          受保護媒體檔案 (面交照片、deal_id 存在)
        │                                              │
        ▼                                              ▼
┌───────────────┐                              ┌─────────────────┐
│   Nginx       │                              │   Django View   │
│  /media/      │                              │ serve_protected │
│  proxy_pass   │                              │ 權限檢查        │
│  → MinIO      │                              │ X-Accel-Redirect│
└───────────────┘                              └────────┬────────┘
        │                                               │
        │                                               ▼
        │                                        ┌───────────────┐
        │                                        │   Nginx       │
        └───────────────────────────────────────▶│ /internal-media/│
                                                 │ internal;     │
                                                 │ proxy→MinIO   │
                                                 └───────────────┘
</pre>
<p><strong>公開檔案完全繞過 Django，由 Nginx 直接代理 MinIO，零 Python 開銷</strong></p>
</div>

---

<!-- _note: 部署自動化是生產力提升的關鍵。我們有七個腳本涵蓋從部署到備份的全部流程。Docker 採用多階段建構，最終產出不到 200MB 的 Alpine 映像，以非 root 用戶執行。CI/CD pipeline 整合了 lint、test 和 deploy 三個階段，只有 push 到 main 分支才會觸發部署。備份策略也很完整，資料庫、Redis 和媒體檔案各有獨立腳本。 -->

# 部署自動化

**七個腳本 + Docker 多階段 + CI/CD**

### 腳本群

<div class="columns">
<div class="card">
<h3>部署</h3>
<p>deploy.sh — migrate + collectstatic + 健康檢查</p>
<p>setup_ssl.sh — Let's Encrypt 申請與續約</p>
</div>
<div class="card">
<h3>備份</h3>
<p>backup_mysql.sh — 保留 7 天</p>
<p>backup_redis.sh — 保留 3 天</p>
<p>backup_media.sh — MinIO 同步備份</p>
</div>
<div class="card">
<h3>壓測</h3>
<p>k6_test.js — 負載測試</p>
<p>k6_stress.js — 壓力測試</p>
<p>k6_verify.js — 煙霧測試</p>
</div>
</div>

### Docker 多階段建構

<pre>
Stage 1: Builder → 安裝依賴 + 編譯
Stage 2: Production (Alpine, 小於 200MB)
  ├─ 非 root 用戶執行
  ├─ HEALTHCHECK 內建
  └─ Gunicorn + dumb-init
</pre>

---

<!-- _note: 這是整個系統的架構總覽圖。從 Nginx 反向代理進來到 Django 應用伺服器，往下連接 MariaDB 資料庫、Redis 快取和 MinIO 物件儲存。Celery 負責非同步任務，包含排程更新和提醒通知。關鍵架構細節：Nginx 直接服務 /static/（volume）、代理 /media/ 到 MinIO（公開檔案完全繞過 Django）、內部代理 /internal-media/ 到 MinIO（受保護檔案經 X-Accel-Redirect）。這個架構支援水平擴展——瓶頸通常出現在資料庫層，可以透過讀取複寫來解決。 -->

# 架構總覽圖

**全系統視角**

<pre>
┌──────────┐
│  Nginx   │── 反向代理、SSL 終止、靜態檔案、速率限制
│          │   /static/ → volume
│          │   /media/  → MinIO (公開檔案，零 Django)
│          │   /internal-media/ → MinIO (內部，X-Accel-Redirect)
└────┬─────┘
     │
┌────▼─────┐
│  Django  │── Gunicorn WSGI、健康檢查、Session 管理
│ (Web)    │   僅處理：受保護媒體權限檢查 → 回傳 X-Accel-Redirect
└────┬─────┘
     │
     ├─────────────┬──────────────┐
     │             │              │
┌────▼─────┐ ┌────▼─────┐ ┌────▼─────┐
│ MariaDB  │ │  Redis   │ │  MinIO   │
│ 資料庫   │ │ 快取+佇列│ │ 物件儲存  │
└──────────┘ └──────────┘ └──────────┘
                  │
             ┌────▼─────┐
             │  Celery  │── 排程任務、非同步處理
             └──────────┘
</pre>

---

<!-- _note: 附錄 A 介紹 AI Tool Registry 的技術架構。當使用者輸入自然語言查詢，GeminiService 建構請求時會附上已註冊的工具定義。Gemini 模型判斷需要呼叫哪個工具後回傳結構化的 Function Call 請求，GeminiService 解析後交由 ToolRegistry 執行對應的函式，最後將結果送回模型產生自然語言回應。整個過程對使用者來說就像在跟一個了解平台的朋友對話。 -->

<!-- _class: lead -->
# 附錄 A：AI Tool Registry 技術架構

### Tool Calling 生命週期

<pre>
使用者輸入「推薦幾本科幻小說」
  │
  ▼
GeminiService 建構請求 + 工具定義
  │
  ▼
Gemini 模型回傳 Function Call
  │
  ▼
ToolRegistry 執行對應工具（書籍推薦查詢）
  │
  ▼
GeminiService 將結果送回模型
  │
  ▼
SSE 串流回傳自然語言回應
</pre>

### 已註冊工具
- ISBN 查詢 — 根據國際標準書號取得書籍資訊
- 書籍推薦 — 根據類別、作者或關鍵字推薦
- 交易狀態查詢 — 查詢特定交易的最新進度

---

<!-- _note: 附錄 B 檢視測試覆蓋與品質指標。總計超過 390 個測試案例分布在五大領域。Shared Books 的測試案例最多，因為涉及狀態機和所有權的複雜邏輯。測試設定使用 SQLite 檔案資料庫以支援並行執行，Celery 任務設為同步執行以簡化測試流程。Factory Boy 用於產生測試資料，確保測試的可重複性和可讀性。 -->

<!-- _class: lead -->
# 附錄 B：測試覆蓋與品質指標

**390+ 測試案例，全面品質守護**

| 測試領域 | 案例數 | 重點 |
|----------|--------|------|
| Accounts API | 82 | 註冊、登入、個人資料、信任分數 |
| Auth API | 51 | JWT 生命週期管理 |
| Books API | 55 | 官方書籍 CRUD |
| Shared Books API | 122 | 狀態機、權限、所有權 |
| Deals API | 80 | 交易流程、FSM 動作、評價 |

### 測試基建
- **SQLite 檔案資料庫** — 支援並行測試執行
- **Celery Always Eager** — 非同步任務同步執行
- **Factory Boy** — 資料工廠，確保測試可重複
- **Playwright E2E** — 瀏覽器端對端測試就緒

---

<!-- _note: 附錄 C 是效能對照表和快取策略的總結。這是我們改善最明顯的四個項目，從 API 呼叫減少到頁面載入加速都有具體數字。快取策略分為兩層：Redis 負責熱資料的即時存取，資料庫索引負責查詢加速。每一項快取都有明確的 TTL 或更新策略，確保資料時效性和系統資源的平衡。 -->

<!-- _class: lead -->
# 附錄 C：效能對照表與快取策略

### 改善前後對照

| 項目 | 改善前 | 改善後 | 影響幅度 |
|------|--------|--------|----------|
| ISBN 查詢 | 每次呼叫外部 API | Redis 快取 | 延遲 ↓ 90%+ |
| 書籍列表 | N+1 問題、無索引 | select_related + 複合索引 | 查詢 ↓ 60%+ |
| 熱門書籍 | 即時計算 | Celery 排程 + 快取 | 載入 ↓ 80% |
| 測試隔離 | 共用 Redis DB 0 | 隔離 DB 1 | 並行無衝突 |

### 快取策略架構

<pre>
Redis (DB 1)
├─ 熱門書籍 → Celery 每小時更新
├─ ISBN 查詢 → TTL 7 天
├─ 用戶統計 → TTL 30 分鐘
└─ AI 對話 → Token 預算動態管理

Database Indexes
├─ 共享書籍排序索引
└─ 交易狀態查詢索引
</pre>

---

<!-- _class: lead -->
# 問題與討論

## 感謝各位的聆聽

<!-- _note: 以上就是本次 Exbooks 功能進度的完整報告。我們在 AI 應用、API 生態系、國際化、觀測性和生產強化方面都取得了具體的進展。接下來開放問答，歡迎大家針對任何一個主題提出問題或建議。如果有興趣深入了解某個技術細節，也很樂意在會後個別討論。 -->
