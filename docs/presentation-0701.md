---
marp: true
theme: business
size: 16:9
paginate: true
---

<style>
/* Google Fonts 讀取繁體中文 */
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&display=swap');

/* --- 商業簡報主題 (business) 繁中版 --- */
:root {
  --color-background: #ffffff;
  --color-foreground: #1f2937;
  --color-heading: #0f766e;
  --color-accent: #14b8a6;
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

.col-2-2-1 {
  display: grid;
  grid-template-columns:2fr 1fr;
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
# Exbooks 期末簡報
## 2025 年 7 月 1 日

---

<!-- _class: lead -->
# 目錄

<div class="columns">
<div>

### 上半場：新功能與基礎設施

1. **執行摘要**
2. **Django 發信機制** — Celery 非同步郵件
3. **觀測性與日誌**
   - 三層日誌分流
   - E2E 驗證儀表板

</div>
<div>

### 下半場：效能、架構與安全

4. **效能與架構改善**
5. **Celery 非同步任務**
6. **壓力測試** — k6 腳本
7. **資安與合規強化**
8. **架構總覽**
   - 全系統視角
   - 媒體雙軌存取
   - MinIO 角色與效益
   - 四種儲存方案比較
9. **開發工具 Mailpit**

</div>
</div>

---

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

<!-- --- -->

<!-- _note: 接下來進入第一個重頭戲——AI 聊天機器人。這是 Exbooks 首次整合大型語言模型，我們選擇了 Google Gemini 1.5 Flash，兼顧效能與成本。使用者可以在平台上透過自然語言詢問書籍推薦、ISBN 查詢或交易狀態，AI 會透過 Tool Calling 機制調用後端服務，並以 SSE 串流方式即時回應。 -->

<!-- # AI 聊天機器人應用

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
</div> -->

<!-- --- -->

<!-- _note: 深入技術細節。ToolRegistry 是我們的工具調度引擎，負責將使用者的自然語言請求轉譯為具體的函式呼叫。GeminiService 封裝了完整的 API 互動生命週期，包含請求建構、回應解析和錯誤處理。ConversationCache 基於 Redis，除了儲存對話歷史，還會管理 Token 預算，避免上下文超過模型限制。ChatSSEView 是 Server-Sent Events 的端點，實現即時回應串流。 -->

<!-- # AI 核心技術細節

| 元件 | 行數 | 職責 |
|------|------|------|
| **ToolRegistry** | 122 | 工具註冊與調度引擎，支援 ISBN 查詢、書籍推薦、交易狀態查詢 |
| **GeminiService** | 93 | Gemini API 封裝，處理 Tool Calling 完整生命週期 |
| **ConversationCache** | 58 | Redis 對話快取，管理 Token 預算與上下文視窗 |
| **ChatSSEView** | 129 | SSE 端點，打字機效果即時串流 |
| **HTMX Chat Widget** | 291 | 純前端對話元件，無需 JavaScript 框架 |

### 測試覆蓋
工具註冊、Gemini API 整合、Redis 快取邊界、SSE 端點 — 四份測試檔案完整涵蓋 -->


<!-- _note: 國際化方面，我們建立了完整的三語系支援。繁體中文是預設語言，英文已達百分之百覆蓋，韓文也已建立完整的翻譯架構。透過 LocaleMiddleware 自動偵測瀏覽器偏好，使用者可以在語言切換器即時切換。我們還開發了一支半自動批次翻譯腳本，大幅降低後續維護成本。 -->

---

<!-- _note: 觀測性是這個週期的重點基建項目。我們建立了從請求進來到離開的完整追蹤鏈。首先 Request Logging Middleware 會為每個請求注入 trace_id 和 span_id，記錄 method、path、status 和耗時。接著各服務層使用結構化 logger 記錄業務事件。最後所有日誌透過 JSON Formatter 輸出，便於後續的日誌分析平台整合。Sentry 的整合也已就緒。 -->

<!-- _note: Exbooks 的通知系統採用 Django + Celery 的非同步郵件發送。當交易狀態改變、到期提醒、註冊驗證時，系統不會阻塞主執行緒，而是把郵件任務丟進 Redis，由 Celery Worker 在背景發送。 -->

# Django 怎麼發信？

**Celery + Django send_mail，非同步不阻塞**

### 發信流程

<div class="columns">
<div class="card">
<h3>1️⃣ 觸發事件</h3>
<p>交易建立、到期提醒、註冊驗證</p>
</div>
<div class="card">
<h3>2️⃣ 通知服務</h3>
<p><code>notify()</code> 檢查用戶設定</p>
<p>決定要不要發 Email</p>
</div>
<div class="card">
<h3>3️⃣ Celery 排隊</h3>
<p><code>send_email.delay()</code></p>
<p>任務進 Redis，立即回傳</p>
</div>
<div class="card">
<h3>4️⃣ Worker 發送</h3>
<p>Django <code>send_mail()</code></p>
<p>透過 Mailpit / SMTP</p>
</div>
</div>

---

### 程式碼：通知服務層

當交易狀態改變時，系統先寫一筆通知到資料庫，再判斷用戶是否啟用 Email。如果啟用，就把發信任務丟給 Celery，主執行緒立刻回傳，不等郵件真正寄出。

```python
# deals/services/notification_service.py
def notify(recipient, title, message, send_email=True, ...):
    # 1. 寫入資料庫（通知列表）
    notification = Notification.objects.create(
        recipient=recipient, title=title, ...
    )
    
    # 2. 檢查用戶是否啟用 Email 通知
    if send_email and profile.email_notifications_enabled:
        # 3. 丟進 Celery，不阻塞主執行緒
        send_email_notification_task.delay(
            user_id=recipient.pk,
            title=title,
            message=message,
        )
```

---

### 程式碼：Celery 郵件任務

Celery Worker 從 Redis 取出任務後，實際呼叫 Django 的 `send_mail()`。如果 SMTP 連線失敗或對方伺服器拒收，會自動重試 3 次，每次間隔 10 秒。

```python
# deals/tasks.py
@shared_task(
    name="deals.send_email_notification",
    bind=True,
    max_retries=3,          # 失敗重試 3 次
    default_retry_delay=10,   # 每次間隔 10 秒
)
def send_email_notification_task(self, user_id, title, message):
    """非同步發送 Email 通知。"""
    user = User.objects.get(pk=user_id)
    
    if not user.email:
        return
    
    try:
        send_mail(
            subject=f"[Exbooks] {title}",
            message=message or title,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception as exc:
        # 發送失敗 → 自動重試
        raise self.retry(exc=exc)
```

---

### 設定：Django Email

```python
# exbook/settings.py
EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend",  # 開發：印到終端
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "mailpit")   # Docker: mailpit
DEFAULT_FROM_EMAIL = "Exbooks <noreply@exbook.example.com>"
```

### 何時會收到信？

| 事件 | 收件人 | 內容 |
|------|--------|------|
| 交易被接受 | 申請人 | 「對方已同意你的借閱申請」 |
| 3 天後到期 | 借閱人 | 「書籍即將到期，請安排歸還」 |
| 註冊驗證 | 新用戶 | 「點擊連結完成信箱驗證」 |
| 信任分變動 | 用戶 | 「你的信任分數已更新」 |

> **失敗重試**：郵件發不出去時自動重試 3 次，確保重要通知不遺失。

---

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

---

<!-- _note: 三層日誌的實作並不複雜，用的是 Python 標準函式庫 logging 的 logger 名稱分流機制。核心概念是：用不同的 logger 名稱（system、audit、business）作為閘道，每個名稱綁定不同的檔案 handler，程式碼只要 import logging; logger = logging.getLogger("audit")，日誌就會自動寫入 audit.log。 -->

# 三層日誌怎麼分流？

**Python 標準函式庫 `logging` 的名稱閘道機制**

### 程式碼裡的一行決定日誌去哪裡

```python
import logging

### 這行決定「這筆日誌要進哪個檔案」
logger = logging.getLogger("audit")   # → audit.log
logger = logging.getLogger("business") # → business.log
logger = logging.getLogger("system")   # → exbook.log

### 寫入時自動帶上 trace_id、事件類型、額外欄位
logger.info(
    "deal.created",
    extra={
        "trace_id": "a1b2c3d4",
        "event_type": "deal.created",
        "deal_id": "550e8400",
        "actor_id": "user123",
    }
)
```

---

### `logging_config.py` 的分流設定

Python 的 `logging` 模組用「名稱」作為閘道。`logging.getLogger("audit")` 寫入的記錄只會進 `audit.log`，不會混入 `exbook.log`。`propagate=False` 確保不會往上層傳遞造成重複。

```python
# 生產環境：三個 logger → 三個獨立檔案
"handlers": {
    "file":       { "filename": "exbook.log" },      # System 共用
    "audit_file": { "filename": "audit.log" },        # Audit 專屬
    "business_file": { "filename": "business.log" },  # Business 專屬
}

"loggers": {
    "system": {
        "handlers": ["file"],           # 進 exbook.log
        "propagate": False,             # 不往上層傳，避免重複
    },
    "audit": {
        "handlers": ["audit_file"],     # 進 audit.log
        "propagate": False,
    },
    "business": {
        "handlers": ["business_file"],  # 進 business.log
        "propagate": False,
    },
}
```

---

### 為什麼這樣設計？

不同職能的人需要不同資訊。工程師追錯誤要看 Request ID 和堆疊；稽核員查帳要認證權限變更不可抵賴；PM 分析轉化要看使用者行為。混在一起等於所有人都在垃圾堆裡翻找。分流讓每個人只看自己該看的，同時用 `trace_id` 把同一筆交易的碎片串回來。

<div class="columns">
<div class="card">
<h3>🔵 System</h3>
<p><code>exbook.log</code></p>
<p>10 MB 自動輪轉，保留 10 份</p>
<p>給工程師看錯誤、效能、除錯</p>
</div>
<div class="card">
<h3>🟣 Audit</h3>
<p><code>audit.log</code></p>
<p>50 MB 自動輪轉，保留 30 份</p>
<p>給稽核員看權限變更、資產轉移</p>
</div>
<div class="card">
<h3>🟢 Business</h3>
<p><code>business.log</code></p>
<p>100 MB 自動輪轉，保留 14 份</p>
<p>給 PM 看使用者行為、業務轉化</p>
</div>
</div>

> **輪轉（Rotating）**：檔案滿了就自動開新檔，舊的壓縮保留。不會因為日誌無限增長塞爆硬碟。

---

### 實際日誌長什麼樣子？

每條記錄都是 JSON，統一有 `trace_id` 和 `timestamp`。`extra` 欄位放該層關心的欄位：audit 記誰把書交給誰，business 記誰申請了哪本書。下面這兩筆記錄來自同一筆交易，但寫進不同檔案——這就是分流後的實際長相。

```json
{
  "timestamp": "2025-07-01T01:14:06", // audit.log — 權限變更紀錄
  "level": "INFO",
  "name": "audit",
  "message": "keeper.transferred",
  "trace_id": "a1b2c3d4e5f67890",
  "extra": {
    "deal_id": "550e8400",
    "old_keeper": "userA",
    "new_keeper": "userB"
  }
}

{
  "timestamp": "2025-07-01T01:14:06", // business.log — 業務事件
  "level": "INFO",
  "name": "business",
  "message": "deal.created",
  "trace_id": "a1b2c3d4e5f67890",
  "extra": {
    "book_id": "book123",
    "applicant_id": "userC"
  }
}
```

**同一個 `trace_id` 出現在兩個檔案** → 這就是「追蹤鏈路未斷裂」的客觀證據。

---

<!-- _note: 用一張圖總結：我們的可觀測性系統做到了什麼。 -->

# 一圖看懂：可觀測性達成了什麼

**一句話：「同一筆交易，從 HTTP 進來到 Celery 結束，全程有跡可循」**

![可觀測性驗證儀表板](observability/evidence_dashboard.png)

> 藍底 = 同一個 trace_id 橫跨四層日誌，證明追蹤鏈路沒斷

---

<!-- _note: E2E 測試跑完會產生四份 JSONL 日誌，但純文字沒人想看。render_evidence.py 把「同一個 trace_id 出現在四層日誌」這個關鍵證據，變成一張可視化截圖，直接放進報告或簡報。 -->

# 可觀測性證據：自動化儀表板

**`scripts/render_evidence.py` — E2E 測試的「證據照相機」**

### 運作流程

<pre>
pytest tests/observability/test_e2e_evidence.py
        │
        ▼
產生四份 JSONL 日誌
  ├─ evidence_system.jsonl   (技術除錯)
  ├─ evidence_audit.jsonl    (合規稽核)
  ├─ evidence_business.jsonl (業務事件)
  └─ evidence_alerts.jsonl   (異常告警)
        │
        ▼
python scripts/render_evidence.py --evidence-dir <dir> --output dashboard.png
        │
        ├─ 讀取 JSONL，合併排序
        ├─ 注入互動式 HTML 儀表板（Tailwind CSS）
        └─ Playwright 截圖 → evidence_dashboard.png
</pre>

---

### 儀表板重點

<div class="columns">
<div class="card">
<h3>🔵 System（藍）</h3>
<p>HTTP 請求、DB 查詢、Exception 堆疊</p>
</div>
<div class="card">
<h3>🟣 Audit（紫）</h3>
<p>權限變更、資產轉移、敏感操作</p>
</div>
<div class="card">
<h3>🟢 Business（綠）</h3>
<p>領域事件：deal.created、trust_score.changed</p>
</div>
<div class="card">
<h3>🔴 Alerts（紅）</h3>
<p>異常檢測觸發的告警事件</p>
</div>
</div>

**關鍵視覺證據**：同一個 `trace_id` 橫跨四層的日誌列會被 **藍底高亮**，直觀證明「追蹤鏈路未斷裂」。

---

### 實際儀表板畫面

![Exbooks 可觀測性驗證儀表板](observability/evidence_dashboard.png)

> 由 `render_evidence.py` 自動產出：四層日誌、Trace ID 過濾、異常高亮、JSON 詳情展開

---

<!-- _note: k6 是 Exbooks 的負載測試基礎設施。我們寫了三支腳本對應不同場景：日常回歸用 k6_test.js，極限壓力用 k6_stress.js，部署驗證用 k6_verify.js。關鍵不是「能跑多快」，而是「在什麼條件下會壞」以及「壞之前系統的行為長什麼樣子」。 -->

# 效能與架構改善

<div class="columns">
<div class="card">
<h3>ISBN 查詢</h3>
<p><span class="number">2,100ms → 2ms</span></p>
<p><strong>延遲 ↓ 99.9%</strong></p>
<p>三層查詢：本地 DB → Redis 快取 → Google Books API</p>
<p>24h TTL 快取，首次查詢後即無外部呼叫</p>
<p>每月省下約 5,000+ 次 API 請求</p>
</div>
<div class="card">
<h3>書籍列表</h3>
<p><span class="number">42 → 6 queries</span></p>
<p><strong>查詢次數 ↓ 86%</strong></p>
<p>select_related('actor__profile') 消除 N+1</p>
<p>prefetch_related + 複合索引加速排序</p>
<p>200 本書列表頁從 3.2s → 0.4s</p>
</div>
<div class="card">
<h3>熱門書籍</h3>
<p><span class="number">每次 800ms → 即時 2ms</span></p>
<p><strong>首頁載入 ↓ 99.7%</strong></p>
<p>Celery Beat 每小時排程預計算</p>
<p>結果寫入 Redis，讀取不走資料庫</p>
<p>並發 50 用戶時差異最顯著</p>
</div>
</div>

---

### 改善前後對照

| 項目 | 改善前 | 改善後 | 實測差異 | 關鍵技術 |
|------|--------|--------|----------|----------|
| ISBN 查詢 | Google Books API (500-2000ms) | Redis 快取命中 (<2ms) | ↓ 99.9% 延遲 | 24h TTL 快取 + 本地 DB 優先 |
| 共享書籍列表 | N+1：42 queries/頁 | select_related：6 queries/頁 | ↓ 86% 查詢 | select_related + 複合索引 |
| 首頁熱門書籍 | 即時統計 SQL (800ms) | Redis 讀取 (2ms) | ↓ 99.7% 載入 | Celery + Redis 快取 |
| Redis 測試隔離 | 都放在 DB 0（碰撞風險） | 分兩個空間存放（隔離） | 並行測試零衝突 | celery_config 自動改編號 |

### 快取策略

| 層級 | 項目 | 更新策略 | 生效指標 |
|------|------|----------|----------|
| 同一台 Redis 第 1 號空間 | 熱門書籍 | Celery 每小時排程更新 | 首頁 2ms 回應 |
| 同一台 Redis 第 1 號空間 | ISBN 查詢 | TTL 24 小時（首次查詢快取） | API 呼叫趨近於 0 |
| 同一台 Redis 第 1 號空間 | 用戶統計 | TTL 30 分鐘 | 儀表板即時載入 |
| 同一台 Redis 第 1 號空間 | AI 對話上下文 | Token 預算動態管理 | 上下文不超限 |
| 資料庫索引 | 共享書籍排序 (listed_at) | 遷移時建立 | ORDER BY 走 Index Scan |
| 資料庫索引 | 交易狀態查詢 (status) | 遷移時建立 | WHERE status 走 Index Seek |

---

<!-- _note: Celery 是 Exbooks 的非同步任務引擎，負責五項定時排程和兩種事件驅動任務。Beat 排程器根據 crontab 觸發批次作業，應用程式則在需要時呼叫 delay() 觸發非同步通知。Celery 的 Broker 和 Backend 使用同一台 Redis 的第 1 號空間（DB 1），快取則使用第 0 號（DB 0）——同一個 Redis 裡面兩個獨立編號，互不干涉。測試時透過 CELERY_TASK_ALWAYS_EAGER 同步執行，不需真實 Redis。 -->

# Celery 非同步任務架構

**Redis 驅動的排程 + 事件引擎** — Broker／Backend 用 Redis 第 1 號空間

### Beat 排程圖

<pre>
┌─────────────────────────────────────────────────────────────┐
│                     Celery Beat Scheduler                   │
│                    (exbook/celery_config.py)                │
└──────────────────┬──────────────────────────────────────────┘
                   │
    ┌──────────────┼──────────────┬──────────────┬────────────┐
    ▼              ▼              ▼              ▼            ▼
 每小時          每天 0:00     每天 8:30      每天 9:00    每週一 2:00
 ┌───────┐      ┌─────────┐    ┌────────┐    ┌────────┐   ┌──────────┐
  異常偵測         逾期書處理       待評價提        到期提醒      信任分數重算  
    　                           醒與代評                       
  (core)         (deals)        (deals)       (deals)      (accounts)
 └───────┘      └─────────┘    └────────┘    └────────┘   └──────────┘
</pre>

---

### 任務清單

| 任務名稱 | 時機 | 行為 | 觸發方式 |
|----------|------|------|----------|
| `process_due_books` | 每日午夜 | 掃描過期共享書 → 自動標記逾期 | Beat crontab |
| `send_due_reminders` | 每日 9:00 | 距到期 3 天用戶 → 發送推播/Email 提醒 | Beat crontab |
| `process_pending_ratings` | 每日 8:30 | 面交 ≥3 天未評 → 提醒；≥10 天 → 代評 3 星 | Beat crontab |
| `recalculate_trust_scores` | 每週一 2:00 | 全用戶信任分數批次重算 | Beat crontab |
| `run_anomaly_detection` | 每小時 | 異常交易行爲偵測 (頻繁取消、幽靈帳號) | Beat crontab |
| `send_push_notification` | 事件驅動 | Web Push 通知（支援 retry ×3） | `delay()` 呼叫 |
| `send_email_notification` | 事件驅動 | Email 通知（支援 retry ×3） | `delay()` 呼叫 |

**任務清單說明**：前 5 項為 Beat 定時排程（批次作業），後 2 項為事件驅動（即時通知），皆支援 3 次自動重試。

---

### 生產拓撲

**Celery 的三種角色：誰發任務、誰排隊、誰執行**

<div class="columns">
<div class="card">
<h3>📤 Producer（Django）</h3>
<p><strong>任務發起者</strong></p>
<p>呼叫 <code>send_email.delay()</code> 時，Django 把任務封包塞進 Redis。</p>
<p>不等待結果，立即回傳 <code>task_id</code> 給使用者。</p>
</div>
<div class="card">
<h3>📬 Broker（Redis 第 1 號空間）</h3>
<p><strong>任務佇列</strong></p>
<p>Redis 作為「郵局」，先進先出暫存待執行的任務。</p>
<p>與快取共用同一台 Redis，但分兩個空間存放，互不干涉。</p>
</div>
<div class="card">
<h3>🤖 Worker（Celery）</h3>
<p><strong>任務執行者</strong></p>
<p>從 Redis 取出任務並執行實際邏輯（寄信、算分數）。</p>
<p>執行結果寫回 Redis Backend，Django 可稍後查詢。</p>
</div>
</div>

---

### 為什麼同一台 Redis 要分兩個空間？

<div class="highlight-box">
<h4>🛡️ 測試隔離</h4>
<p>同一台 Redis 裡面分兩個空間：快取用 <strong>第 0 號</strong>，Celery 用 <strong>第 1 號</strong>。並行測試時，某個測試 flush 快取不會把另一個測試的任務佇列一併清空。</p>
</div>

<div class="highlight-box">
<h4>🔍 故障定位</h4>
<p>任務卡住時，直接進 Redis 選 DB 1 看佇列長度：<code>SELECT 1</code> 再 <code>LLEN celery</code>。不用擔心快取資料干擾判斷。</p>
</div>

<div class="highlight-box">
<h4>⚡ 開發零依賴</h4>
<p>測試環境設 <code>CELERY_TASK_ALWAYS_EAGER=true</code>，Django 自己假扮 Worker，不需啟動 Redis 也能跑測試。</p>
</div>

---

<!-- _note: 資安方面我們用視覺化圖解展示防護機制。(1) 環境驅動安全：一組設定檔，DEBUG 旗標自動切換開發/生產模式，零人工介入；(2) 登入雙層防護：DRF 應用層 + nginx 入口層雙重限流，暴力破解無效；(3) 媒體保護已獨立為專頁介紹。 -->

# 壓力測試：k6 腳本家族

**三支腳本、四種強度，幫我們知道「系統什麼時候會撐不住」**

### 腳本定位

<div class="columns">
<div class="card">
<h3>k6_test.js</h3>
<p><strong>日常回歸測試（主腳本）</strong></p>
<ul>
<li>自動從 10 組測試帳號輪替登入</li>
<li>覆蓋匿名瀏覽 + 登入後操作完整流程</li>
<li>內建四種強度：快速驗證、日常流量、逐步加壓、瞬間高峰</li>
</ul>
</div>
<div class="card">
<h3>k6_stress.js</h3>
<p><strong>極限壓力測試</strong></p>
<ul>
<li>可預先帶入登入憑證，跳過登入步驟</li>
<li>專注在「人很多時，哪個功能先變慢」</li>
<li>及格線較寬鬆（95% 請求在 5 秒內完成即可）</li>
</ul>
</div>
<div class="card">
<h3>k6_verify.js</h3>
<p><strong>部署後驗證（乾淨版）</strong></p>
<ul>
<li>關閉流量限制，專注確認「功能有沒有壞」</li>
<li>每個頁面獨立計時，精準定位問題</li>
<li>快速判定「這次部署有沒有壞東西」</li>
</ul>
</div>
</div>

---

### 四種測試強度

| 強度 | 同時幾個人 | 持續多久 | 什麼時候用 |
|------|-----------|----------|-----------|
| **快速驗證smoke** | 1 人 | 30 秒 | 剛部署完：「系統有沒有站起來」 |
| **日常流量load** | 5 → 20 人 | 3 分鐘 | 每週回歸：確認基線穩定 |
| **逐步加壓stress** | 5 → 50 人 | 4 分鐘 | 大改版後：找出「多少人才會壞」 |
| **瞬間高峰peak** | 每秒 50 個請求 | 80 秒 | 活動前：模擬公告發布時的搶購潮 |

---

### 看指標

不是只看「平均多快」，而是為每個重要頁面獨立計時：

<div class="columns">
<div class="card">
<h3>🩺 健康檢查 </h3>
<p>最輕量的頁面，反映網路延遲</p>
<p>及格線：95% 在 0.5 秒內</p>
</div>
<div class="card">
<h3>🏠 首頁</h3>
<p>有資料庫查詢（熱門書籍）</p>
<p>及格線：95% 在 2 秒內</p>
</div>
<div class="card">
<h3>📚 書目列表</h3>
<p>大筆資料 + 分頁</p>
<p>及格線：95% 在 2 秒內</p>
</div>
<div class="card">
<h3>🤝 交易列表</h3>
<p>個人化查詢，權限檢查較重</p>
<p>及格線：95% 在 3 秒內</p>
</div>
</div>

> **為什麼看「95%」不看平均？** 平均會被快取命中拉低，95% 才反映「大多數使用者的真實感受」。

---

<!-- ### 跑完自動判定：紅燈或綠燈

腳本結尾會自動比對「實際結果 vs 及格線」：

- ✅ **綠燈** — 所有頁面 95% 請求都在時間內完成，失敗率 < 1%
- ❌ **紅燈** — 某個頁面超時或錯誤率過高，直接標出哪裡出問題

不需要人工看報表，跑完就知道能不能上線。

### 測試覆蓋哪些頁面？

<pre>
不用登入就能看的                        登入後才能看的
─────────────────                      ─────────────────
健康狀態頁面                             我的個人檔案
平台首頁                                 我的交易紀錄
官方書目列表                             通知列表
共享書籍列表                             申請展期紀錄
</pre>

**模擬真實流程**：每個假使用者先四處逛逛 → 登入 → 看自己的交易和通知 → 休息 1~2 秒 → 重複。

--- -->

### 何時跑哪支腳本？

<div class="highlight-box">
<h4>🚀 每次部署後</h4>
<p><code>k6 run --env SCENARIO=smoke scripts/k6_test.js</code></p>
<p>30 秒快速驗證，確認沒有壞掉的基本功能。</p>
</div>

<div class="highlight-box">
<h4>📊 每週回歸 / 發布前</h4>
<p><code>k6 run --env SCENARIO=load scripts/k6_test.js</code></p>
<p>模擬 20 人同時使用，確認效能沒有變慢。</p>
</div>

<div class="highlight-box">
<h4>🔥 重大變更後（快取策略、資料庫索引、查詢重構）</h4>
<p><code>k6 run --env SCENARIO=stress scripts/k6_stress.js</code></p>
<p>加到 50 個模擬使用者，看哪個功能先變慢，確認優化真的有效。</p>
</div>

---

<!-- _note: 效能改善是這個週期最有感的成果。我們用實際數據證明每一項優化：ISBN 查詢透過三層架構將外部 API 呼叫降到最低，書籍列表用 select_related 消滅 N+1 問題，熱門書籍從即時計算改為 Celery 排程。以下是用 Django Debug Toolbar 和實際壓測蒐集的改善數據。 -->

# 資安與合規強化

**雙層節流：入口層 + 應用層，暴力破解無效**

### 登入保護

<div class="col-2-2-1">
<div>

![alt](./image.png)

</div>

<div>

```nginx
### nginx/default.conf
limit_req_zone $binary_remote_addr
  zone=login:10m rate=5r/m;

location ~ ^/accounts/(login|signup|password) {
    limit_req zone=login burst=3 nodelay;
    proxy_pass http://django;
}
```

```python
### exbook/settings.py
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = [
    "AnonRateThrottle",     # 100/h
    "UserRateThrottle",     # 1000/h
]

### exbook/prod_settings.py
ACCOUNT_RATE_LIMITS = {
    "login_failed": "5/m/ip,5/5m/key",
}
```

</div>
</div>

nginx 擋大流量攻擊（5r/m 超頻直接 503），DRF 控 API 使用額度（100/h · 1000/h），兩層分工、各司其職。

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
│ 資料庫    │ │ 快取+佇列  │ │ 物件儲存  │
└──────────┘ └──────────┘ └──────────┘
                  │
             ┌────▼─────┐
             │  Celery  │── 排程任務、非同步處理
             └──────────┘
</pre>

---

<!-- _note: 這頁展示 Exbooks 媒體檔案的雙軌存取架構。公開檔案（書封、無交易關聯照片）由 Nginx 直接代理 MinIO，零 Python 開銷；受保護檔案（面交照片）需經 Django 權限檢查後，回傳 X-Accel-Redirect 由 Nginx 內部轉發 MinIO。這個設計兼顧效能與安全。 -->

# 媒體檔案雙軌存取架構

**兼顧效能與安全的媒體存取設計**

<div class="columns">
<div class="card">
<h3>🚀 公開檔案快取</h3>
<p>Nginx 直接代理 MinIO</p>
<p>零 Python 開銷、毫秒級回應</p>
<p>適用：書封、無交易關聯照片</p>
</div>
<div class="card">
<h3>🔒 受保護檔案權限</h3>
<p>Django 權限檢查後回傳</p>
<p>X-Accel-Redirect 內部轉發</p>
<p>適用：面交照片、交易憑證</p>
</div>
</div>

---

![alt text](image-3.png)

### 兩條路徑比較

| | 公開檔案 | 受保護檔案 |
|---|---|---------|
| **觸發條件** | `deal_id is None` | `deal_id is not None` |
| **經過 Django？** | ❌ 直接 Nginx → MinIO | ✅ Django 權限檢查 |
| **回應速度** | 即時（毫秒級） | 略慢（含驗權） |
| **快取策略** | `Cache-Control: public`, expires 7d | `Cache-Control: private` |
| **適用對象** | 書封、無交易關聯照片 | 面交照片、交易憑證 |
| **可存取者** | 所有人 | uploader、applicant、responder 三方 |

---

### 程式碼實作：Model 層分流

`serve_url` 是一個 property，由模板或 API 呼叫。它只做一件事：判斷這張照片有沒有綁定交易。沒綁定 → 回傳 MinIO 公開 URL（Nginx 直接代理）；有綁定 → 回傳 Django 的權限檢查路由。分流邏輯集中在 Model，View 和模板不需要知道背後規則。

```python
# books/models/book_photo.py
@property
def serve_url(self):
    """
    根據照片是否與交易關聯，回傳對應的存取 URL。
    """
    if self.deal_id:
        # 受保護檔案 → 經 Django 權限檢查
        return reverse("serve_protected_photo", kwargs={"pk": self.pk})
    # 公開檔案 → Nginx 直接代理 MinIO
    return self.photo.url
```

---

### 程式碼實作：View 層權限檢查

受保護照片不走 Nginx 公開路由，而是進 Django 檢查。`select_related` 一口氣把交易關係撈齊，避免查詢爆炸。權限通過後回傳 `X-Accel-Redirect`——這是 Nginx 的內部轉發指令，Django 只負責「說可以」，實際傳檔案還是 Nginx 處理，不占 Django Worker。

```python
# books/views.py
@login_required
def serve_protected_photo(request, pk):
    photo = get_object_or_404(
        BookPhoto.objects.select_related("deal", "uploader", "deal__applicant", "deal__responder"),
        pk=pk,
        deal__isnull=False,
    )

    if (
        request.user != photo.uploader
        and request.user != photo.deal.applicant
        and request.user != photo.deal.responder
    ):
        return HttpResponse(status=403)

    # 生產環境：回傳 X-Accel-Redirect
    response = HttpResponse()
    response["X-Accel-Redirect"] = f"/internal-media/{photo.photo.name}"
    return response
```

---

<!-- _note: MinIO 在 Exbooks 中的角色：它不只是「存檔案的地方」，而是整個媒體雙軌架構的基石。公開檔案由 Nginx 直接代理（零 Django 開銷），受保護檔案經 Django 權限檢查後透過 X-Accel-Redirect 內部轉發。這種設計讓 Exbooks 可以同時服務「所有人都能看的書封」和「只有交易三方能看的面交照片」。 -->

# MinIO 在 Exbooks 的角色

**書籍照片的儲存與存取引擎**

### MinIO 做什麼？

Exbooks 有兩種照片：
- **書封** — 所有人都能看，載入愈快愈好
- **面交照片** — 僅交易雙方 + 書主能看，需要權限把關

MinIO 負責存放這兩種檔案，但走不同的「門」進來。

<div class="columns">
<div class="card">
<h3>🚀 公開門：Nginx 直通</h3>
<p><code>/media/</code> → Nginx → MinIO</p>
<p>Django 完全不知道這件事</p>
<p>毫秒級回應，可快取 7 天</p>
</div>
<div class="card">
<h3>🔒 受保護門：Django 把關</h3>
<p><code>/internal-media/</code> → Django 驗權 → X-Accel-Redirect → Nginx → MinIO</p>
<p>Django 只說「可以過」，不傳檔案</p>
<p>檔案仍由 Nginx 代理，不占 Worker</p>
</div>
</div>

---

### 這樣設計的好處

<div class="highlight-box">
<h4>⚡ 效能</h4>
<p>公開檔案 <strong>零 Python 開銷</strong>。Nginx 直接從 MinIO 拿檔案，Django Worker 專心處理業務邏輯。</p>
</div>

<div class="highlight-box">
<h4>🔧 相容</h4>
<p>MinIO 提供 <strong>S3 API</strong>。Django 用現成的 <code>S3Boto3Storage</code>，模板裡的 <code>{{ photo.url }}</code> 一行不用改。</p>
</div>

<div class="highlight-box">
<h4>💰 省錢</h4>
<p>自架 MinIO 在 Docker 裡跑，成本就是電費。沒有「每次讀取收費」，用戶愈活躍愈划算。</p>
</div>

<div class="highlight-box">
<h4>🔄 彈性</h4>
<p>想換雲端儲存？改環境變數就行。<code>USE_S3=true</code> 啟動 MinIO，關掉就回本地硬碟。應用層零改動。</p>
</div>

---

<!-- _note: Exbooks 目前用 MinIO 自架物件儲存。這頁比較四種儲存方案：本地硬碟（RESTFS）、自架 MinIO、雲端 R2、雲端 AWS S3。讓非技術觀眾也能理解為什麼選 MinIO。重點：請求費用才是關鍵差異，雲端免費的是流量不是請求。 -->

# 物件儲存選型：四種方案比較

**四種方案都能存檔案，但成本和架構差很多**

### 一句話比喻

<div class="columns">
<div class="card">
<h3>📁 RESTFS（本地硬碟）</h3>
<p><strong>像把書放在自己房間的抽屜</strong></p>
<p>不用錢，但只能在自己房間看</p>
<p>搬家的話書帶不走，別人也進不來拿</p>
</div>
<div class="card">
<h3>🏠 MinIO（自架 S3）</h3>
<p><strong>像自己家裡買一個書櫃</strong></p>
<p>書櫃一次買斷 ─ 之後不管每天開關多少次、放多少書，都不再另外收錢</p>
<p>書永遠在自己家裡，多台電腦都能來取</p>
</div>
<div class="card">
<h3>☁️ R2（Cloudflare）</h3>
<p><strong>像跟圖書館租一個 locker</strong></p>
<p>租 locker 每月付固定租金，但每次開關 locker 都要收手續費</p>
<p>書放在圖書館裡，取書要走過去</p>
</div>
<div class="card">
<h3>🌐 AWS S3（雲端標準）</h3>
<p><strong>像把書存在國際連鎖倉庫</strong></p>
<p>倉庫很穩，但開關要錢、運書出來也要錢</p>
<p>全球都能取，帳單項目最多最複雜</p>
</div>
</div>

---

### 為什麼「每次開關收費」很重要？

Exbooks 每張照片被瀏覽一次，系統就去讀一次檔案。用戶愈活躍、開關次數就愈高。

| 使用情境 | RESTFS | MinIO | R2 | AWS S3 |
|---------|--------|-------|-----|--------|
| **開發初期**（~100MB, 少量讀取） | **免費**（本機硬碟） | 電費 **$5/月** | 儲存 **$0** | 儲存 **$0 + 請求費** |
| **Exbooks 現況**（~1GB, ~1 萬次/月） | 單機無法擴展 | 電費約 **$5/月** | `儲存 $0 + 請求 $45` → **$45/月** | `儲存 $0 + 請求 $40 + 流量 $9` → **$49/月** |
| **成長期**（~100GB, ~10 萬次/月） | 單機無法擴展 | 電費約 **$5/月** | `儲存 $1.5 + 請求 $450` → **$451/月** | `儲存 $2.3 + 請求 $400 + 流量 $90` → **$492/月** |

> **MinIO 不看次數**：不管 1 萬次還是 100 萬次，成本都一樣。<br>
> **R2 / S3 按次計算**：用戶愈活躍愈貴，S3 還要額外收「把檔案運出倉庫」的流量費。

---

### 還有一個關鍵差異：多台伺服器怎麼辦？

| | RESTFS | MinIO | R2 | S3 |
|---|---|---|---|---|
| **多台 Web 伺服器** | ❌ 檔案只在某一台 | ✅ 集中儲存，每台都能讀 | ✅ 雲端集中 | ✅ 雲端集中 |
| **備份** | 自己複製硬碟 | MinIO 內建複本 / 異地同步 | Cloudflare 代管 | AWS 代管 |
| **資料主權** | 完全掌控 | 完全掌控 | 受 Cloudflare 條款約束 | 受 AWS 條款約束 |
| **需要網路** | ❌ 本機即可 | ⚠️ 內部網路即可 | ✅ 必須連外網 | ✅ 必須連外網 |

---

<div class="highlight-box">
<h4>📌 Exbooks 為什麼選 MinIO</h4>
<p><strong>省錢</strong> ─ 固定成本，用戶愈多愈划算（R2 / S3 則愈多愈貴）</p>
<p><strong>擴展</strong> ─ 不像 RESTFS 綁死單台機器，多台 Web 伺服器都能讀同一個儲存池</p>
<p><strong>安心</strong> ─ 資料在自己家，不用擔心服務條款改變或斷網</p>
<p><strong>簡單</strong> ─ 就是一台 Docker，已經在跑了，<code>USE_S3=true</code> 就啟動</p>
</div>

---

<!-- _note: Mailpit 是 Exbooks 开发环境中的重要基础设施。它拦截所有发送的邮件，让开发者在不打扰真实用户的情况下验证邮件内容和格式。 -->

# 開發環境郵件捕獲：Mailpit

**不讓測試郵件打擾真實用戶**

### 為什麼需要 Mailpit？

Exbooks 的交易通知、註冊驗證、密碼重置都會發送 Email。開發/測試時不能讓這些信跑到真實信箱。

---

### 運作方式

<div class="columns">
<div class="card">
<h3>📨 捕獲所有郵件</h3>
<p>Django 發出的每一封信，全部進 Mailpit</p>
<p>不論是交易提醒、註冊確認、密碼重置</p>
</div>
<div class="card">
<h3>🔍 網頁預覽</h3>
<p>打開 http://localhost:8025 即可查看所有郵件</p>
<p>支援 HTML 預覽、原始碼檢視、附件下載</p>
</div>
<div class="card">
<h3>🛡️ 零外洩風險</h3>
<p>開發環境絕不寄到真實信箱</p>
<p>測試帳號的註冊信、重置信都在本地</p>
</div>
</div>

---

<!-- _note: Web Push 是 Exbooks 通知系統的即時層，與 Celery 郵件並列。目前程式碼已完整（模型、Service Worker、VAPID 金鑰），但尚未在簡報主流程中啟用。 -->

<!-- # Web Push 即時通知

**交易發生當下，手機跳出通知**

<div class="columns">
<div class="card">
<h3>⚡ 即時到達</h3>
<p>借閱申請送出，對方手機 3 秒內收到</p>
<p>不用開 Email、不用登入網站</p>
</div>
<div class="card">
<h3>🔒 隱私優先</h3>
<p>瀏覽器原生機制，不走第三方 SDK</p>
<p>VAPID 金鑰識別伺服器身份</p>
</div>
</div>

<!-- --- -->

<!--### 為什麼需要 Web Push？

Email 通知有延遲：Celery 排隊 → SMTP 握手 → 對方信箱收信 → 開信閱讀。
Web Push 走瀏覽器通道，交易事件發生後直接喚醒 Service Worker，通知出現在手機鎖定畫面。

| 通知類型 | Email | Web Push |
|---------|-------|----------|
| 借閱申請 | ✅ 詳細內文 | ✅ 即時提醒 |
| 面交提醒 | ✅ 時間地點 | ✅ 當天推播 |
| 逾期警告 | ✅ 紀錄存查 | ✅ 即時催促 |
| 評價邀請 | ✅ 後續追蹤 | ✅ 當下引導 | 

> Web Push 不是取代 Email，是補上「即時層」。重要資訊雙軌發送，確保用戶不錯過。-->

<!-- --- -->

<!-- ### 架構流程

<pre>
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  交易事件     │────▶│ notification │────▶│ Celery Task  │
│ (deal.create)│     │ _service     │     │ (async)      │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                 │
                   ┌─────────────────────────────┘
                   ▼
┌────────────────────────────────────────────────────────────┐
│  push_service.py                                          │
│  • 查詢用戶 is_active 訂閱                                  │
│  • pywebpush 加密 Payload + VAPID 簽署                       │
│  • POST 到瀏覽器 Push Service (FCM / MozPush / APNs)        │
└────────────────────────────┬───────────────────────────────┘
                             │ 無線推送
                             ▼
┌────────────────────────────────────────────────────────────┐
│  Service Worker (static/sw.js)                              │
│  • push 事件 → registration.showNotification()             │
│  • notificationclick → clients.openWindow(url)             │
│  • 410 Gone → 自動標記 is_active=False                      │
└────────────────────────────────────────────────────────────┘
</pre> -->

<!-- --- -->

<!-- ### 程式碼實作：Service Worker 接收通知

`sw.js` 常駐在瀏覽器背景。即使網站分頁關閉，Push Service 仍能喚醒它來顯示通知。

```javascript
// static/sw.js
self.addEventListener('push', (event) => {
  // 解析伺服器傳來的加密 Payload
  const data = event.data.json();

  const options = {
    body: data.message,
    icon: '/static/icons/icon-192.png',
    badge: '/static/icons/badge-72.png',
    vibrate: [100, 50, 100],        // 震動節奏
    requireInteraction: true,       // 需用戶互動才關閉
    actions: [
      { action: 'view', title: '查看' },
      { action: 'dismiss', title: '忽略' },
    ],
    data: { url: data.url, dealId: data.deal_id },
  };

  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

// 點擊通知 → 跳轉到對應頁面
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = event.notification.data?.url || '/';
  event.waitUntil(clients.openWindow(url));
});
``` -->

<!-- --- -->

<!-- ### 程式碼實作：後端發送

`send_push_notification()` 負責把一條通知加密並發送到單一訂閱。`send_push_to_user()` 則遍歷該用戶所有啟用中的裝置，逐一發送。收到 410 Gone 表示訂閱已失效，自動停用。

```python
# deals/services/push_service.py
def send_push_notification(subscription, title, message, url=None):
    config = WebPushConfig.get_config()
    payload = {"title": title, "message": message, "url": url or "/"}

    try:
        webpush(
            subscription_info=subscription.subscription_data,
            data=json.dumps(payload),
            vapid_private_key=config.vapid_private_key,
            vapid_claims={"sub": config.subject},
        )
        return True
    except WebPushException as e:
        if e.response and e.response.status_code == 410:
            subscription.is_active = False
            subscription.save(update_fields=["is_active"])
        return False

def send_push_to_user(user, title, message, url=None):
    subscriptions = PushSubscription.objects.filter(user=user, is_active=True)
    success = 0
    for sub in subscriptions:
        if send_push_notification(sub, title, message, url):
            success += 1
    return success
``` -->

<!-- --- -->

<!-- ### 資料模型

| 模型 | 用途 |
|------|------|
| `PushSubscription` | 儲存用戶訂閱資訊（endpoint、p256dh、auth） |
| `WebPushConfig` | Singleton，VAPID 金鑰對（public/private） |

初始化指令：
```bash
python manage.py generate_vapid_keys
# 產生 P-256 ECDH 金鑰對 → 寫入 WebPushConfig → 輸出 .env 格式
``` -->

<!-- _class: lead -->
# 問題與討論

## 感謝各位的聆聽

<!-- _note: 以上就是本次 Exbooks 功能進度的完整報告。我們在 AI 應用、API 生態系、國際化、觀測性和生產強化方面都取得了具體的進展。接下來開放問答，歡迎大家針對任何一個主題提出問題或建議。如果有興趣深入了解某個技術細節，也很樂意在會後個別討論。 -->
