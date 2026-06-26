# 進階可觀測性系統 (Observability System) 實作方案

## 1. 概述 (Overview)

本系統將傳統的「日誌記錄 (Logging)」提升至「可觀測性 (Observability)」層級。目標是解決分散式系統（Django $\rightarrow$ Celery $\rightarrow$ MariaDB）中常見的「追蹤斷層」問題，並透過日誌分流減少雜訊，提高業務分析與安全稽核的效率。

### 核心目標
- **全鏈路追蹤**：一個請求從進入系統到完成所有背景任務，擁有唯一的 `trace_id`。
- **維度分離**：將技術除錯、業務分析、安全稽核三者分流，滿足不同角色的需求。
- **主動防禦**：從被動看日誌轉向主動偵測業務異常。

---

## 2. 三層日誌架構 (Three-Tier Log Streams)

系統將日誌拆分為三個獨立通道，定義不同的儲存策略與對象：

| 層級 | 紀錄內容 | 主要對象 | 儲存特性 | 目的 |
| :--- | :--- | :--- | :--- | :--- |
| **System Log** | 錯誤堆棧、性能警告、Infra 資訊 | 工程師 (SRE) | 短期保存, 高詳細度 | 快速定位 Bug 與性能瓶頸 |
| **Business Log** | 結構化業務事件 (e.g. `deal.created`) | 產品經理 (PM) | 長期保存, 結構化 JSON | 用戶行為分析、業務轉化率統計 |
| **Audit Log** | 關鍵資產變更、權限變更 | 管理員 / 審計員 | 極長期保存, Append-only | 爭端處理、合規審查、安全性追蹤 |

---

## 3. 實作細節 (Implementation)

### 3.1 跨邊界追蹤 (Lv.2: Distributed Tracing)
為了在非同步環境中維持上下文，系統引入了基於 `contextvars` 的追蹤機制。

- **核心模組**：`core/observability/trace_context.py`
- **追蹤標識**：
    - `trace_id` (16位元): 代表整個請求鏈條的唯一 ID。
    - `span_id` (8位元): 代表鏈條中單次操作的唯一 ID。
- **傳遞路徑**：
    1. **HTTP 進入** $\rightarrow$ `RequestLoggingMiddleware` 生成 `trace_id` $\rightarrow$ 存入 `contextvars`。
    2. **觸發 Celery** $\rightarrow$ `before_task_publish` 信號將 `trace_id` 注入 Task Header。
    3. **Worker 執行** $\rightarrow$ `task_prerun` 信號從 Header 恢復 `trace_id` 到 Worker 的 `contextvars`。
    4. **資料庫持久化** $\rightarrow$ 關鍵模型 (`ExchangeEvent`, `TrustScoreLedger`) 新增 `trace_id` 欄位。

### 3.2 結構化事件發射 (Lv.3: Structured Events)
不再使用簡單的 `logger.info("User created deal")`，而採用標準化發射器。

- **核心模組**：`core/observability/business_events.py`
- **API 設計**：
    - `emit_business_event(event_type, payload)`: 發送至 `business` 流。
    - `emit_audit_event(event_type, payload)`: 發送至 `audit` 流。
- **自動富化**：所有事件在發送時會自動附加當前的 `trace_id`、`span_id` 與 `request_id`。

### 3.3 領域異常檢測 (Lv.4: Anomaly Detection)
實作主動監控機制，將日誌從「紀錄」變為「告警」。

- **核心模組**：`core/observability/anomaly_detectors.py`
- **偵測邏輯**：
    - **信用分驟降**：監控 `TrustScoreLedger`，若短時間內下降過快則觸發 `system.alerts`。
    - **逾期連鎖反應**：監控逾期率異常激增。
- **自動化執行**：透過 Celery Beat 每小時觸發一次掃描任務。

---

## 4. 驗證與演示 (Demo Guide)

### 演示路徑
`請求 (Request)` $\rightarrow$ `系統日誌 (System)` $\rightarrow$ `業務事件 (Business)` $\rightarrow$ `稽核紀錄 (Audit)`

### 驗證步驟
1. 執行一筆業務操作 (例如：建立書籍交換 Deal)。
2. 獲取該次操作的 `trace_id`。
3. 在三份日誌文件中搜尋該 `trace_id`：
   - 在 `exbook.log` 看到技術處理流程。
   - 在 `business.log` 看到 `deal.created` 業務事件。
   - 在 `audit.log` 看到資產權限變更紀錄。

---

## 5. 相關檔案索引

| 檔案路徑 | 角色 |
| :--- | :--- |
| `core/observability/trace_context.py` | 追蹤上下文核心 (ContextVars) |
| `core/observability/celery_signals.py` | 跨進程追蹤傳遞 (Signals) |
| `core/observability/business_events.py` | 結構化事件發射器 |
| `core/observability/anomaly_detectors.py` | 業務異常檢測邏輯 |
| `core/logging_config.py` | 三層流日誌配置 |
| `core/middleware/request_logging.py` | 請求進入點追蹤注入 |
| `core/tasks.py` | 異常檢測任務定義 |
