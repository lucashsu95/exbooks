# ADR: 2026-10-24 架構檢視後的延期項目（Follow-ups）

**Date**: 2026-10-24

**Status**: Accepted（延期決定；各項為獨立 follow-up，可分別啟動）

## Context

2026-10-24 的架構檢視（deepen shallow modules）完成六個 candidate：
死模組清理、publish_book、Deal 轉換收進 service、LLM provider seam、
chat orchestration、due-deals 查詢合併。以下項目在檢視中發現、
但經決策**本次不做**，記錄原因與建議修法，避免未來反覆重新調查。

## Follow-ups（依建議優先序）

### F-1 · `Deal.cancel()` 的 FSM 旁路是活炸彈（建議 P1）

**現象**：`deals/models/deal.py` 的 `cancel()` transition 內
（source REQUESTED/RESPONDED 時）對 `shared_book.status` 做**直接賦值**
+ save。`status` 是 `FSMField(protected=True)`，直接賦值會拋
`AttributeError: Direct status modification is not allowed`——
**任何真的呼叫 `cancel()` 的路徑都會崩**。

**現況**：生產無任何 caller（web 層用 `cancel_request`，
其還書寫用 queryset.update 可繞過 protected；DRF 層無 cancel 路由），
所以休眠中。C3 期間新增的 sibling 自動取消已改走 `auto_cancel()`，
不觸碰此路徑。

**建議修法**（擇一）：
- 若 `cancel()` 的還書語意還要保留：改成與 `cancel_request()` 相同的
  queryset.update 寫法（並加註 intentional bypass），或
- 直接刪除該還書區塊（`cancel_request` 已負責 BR-14 還書），
  讓 `cancel()` 只剩純狀態轉換。

**啟動觸發**：任何新功能要呼叫 `cancel()` 之前，先修這個。

### F-2 · `deal_service.create_deal` 沒有 `@transaction.atomic`

**現象**：`create_deal` 依序寫 Deal、DealMessage（備註）、
`notify_deal_requested`、`record_exchange_event`，中途失敗會留下半成品。
（已刪除的 `deal_creation_service.py` 有 atomic，live 版本沒有。）

**建議修法**：加 `@transaction.atomic`，並補一個 rollback 測試
（C2 搬遷時因此標記為不搬，見 `tests/deals/test_deal_service.py`）。

### F-3 · `AIConfig.from_env` 的隱藏副作用

**現象**：`sdk/python/src/ai_client/config.py` 的 `load_project_env()`
從 cwd/套件位置往上爬找 `.env` 並 mutate `os.environ`，在
`create_client()` 組裝時執行。

**決定**：C4 只在 `ChatService` 層隔離 seam（client 可注入），
SDK 本體未動。

**建議修法**：`from_env()` 不 mutate 環境，改回傳 config；
`.env` 載入移到應用啟動點（`exbook/settings.py` 已載 dotenv，
SDK 不需要自己再做一次）。

### F-4 · 分頁三種風格未統一

**現象**：`Paginator(..., 12)`（books 兩個 list view）、
`Paginator(..., 20)`（deals）、手刻 slicing（已隨 deal_query_service
刪除）、DRF `PAGE_SIZE: 20`。

**決定**：C6 只收查詢骨架（`_meeted_deals`），分頁統一超出範圍。

**建議修法**：定一個 `core/pagination.py`（或收回 `core/constants.py`
的 `PAGE_SIZE_DEFAULT`），各 list view 改用同一個 factory。

### F-5 · DRF `DealSerializer` 缺欄位

**現象**：`deals/api_views.py::create` 會傳 `loan_duration_days` /
`note`，但 `DealSerializer` 沒有這兩個欄位，永遠是 `None`。

**建議修法**：二擇一——serializer 補欄位（API 完整可用），
或從 view 的 call 拿掉這兩個 kwarg（API 不支援就別裝）。

### F-6 · 404 頁面測試與文案不同步（既有）— ✅ 已解決（2026-10-25）

**現象**：`tests/core/test_launch_critical.py::test_custom_404_page_renders`
斷言「找不到你要的頁面」，但 404 頁面已改成貓咪主題
（「這本書…似乎被某隻貓咪借走了」）。**本輪之前就一直失敗**，
與 2026-10-24 改動無關。

**建議修法**：把斷言改成抓頁面標題「找不到頁面｜Exbooks」。

**解決**：依建議修法更新斷言，測試全綠。

### F-7 · DRF `DealViewSet.create` 缺每類型 applicant 身份驗證（建議 P2）

**現象**：`deals/api_views.py::create` 的 `deal_type` 直接透傳 `create_deal`，
未做每類型的申請者身份驗證（與 master 相同）。本輪審查已在 `create_deal`
補上「EX 必須由持有者發起」（蓋住所有入口），但 RG（應由 Owner 發起）等
其他類型在 API 路徑上仍無身份驗證，任何登入者可經 API 發起。

**建議修法**：`DealViewSet.create` 對 API 支援的 `deal_type` 設白名單，
或為每類型在 `rules.py` 補 applicant predicate 並在 viewset 檢查。

## Consequences

- 這些項目的調查成本（定位、確認影響面）已完成，未來啟動時可直接看本檔。
- F-1 是唯一有「休眠炸彈」性質的：在修好之前，**不要**新增任何
  呼叫 `Deal.cancel()` 的路徑。

## References

- 架構檢視報告（HTML，temp 目錄，2026-10-24）
- `docs/adr/django-fsm-migration.md`（FSM 遷移背景）
- `GLOSSARY.md`（service 錯誤契約、domain 詞彙）
