# Exbooks Domain Glossary

Exbooks 共享書籍平臺的 domain 詞彙。討論架構、命名 module、寫 ADR 時使用這些詞，
不要用代碼中的函式名（如 `book_add`）或類別名（如 `SharedBookHandler`）代替。

## 核心概念

- **發布（publish）**：將一冊實體書上架為 SharedBook 並進入 TRANSFERABLE 狀態的完整流程。
  含 OfficialBook 依 ISBN upsert、封面處理、書況照片、FSM 初始轉換（S → T）。
  實作：`books/services/book_service.py::publish_book`。
- **更新（update）**：owner 修改已上架書籍的 OfficialBook 基本資料與 SharedBook 欄位。
  Level 0 使用者無權限。實作：`update_book`。
- **上架 / 下架（list / suspend）**：SharedBook 在 TRANSFERABLE ↔ SUSPENDED 之間的切換。
  實作：`list_book` / `suspend_book`，對外入口 `toggle_listing`。
- **即將到期（due soon）**：借閱者視角，MEETED 狀態且到期日落在提醒窗口內的交易。
  實作：`deals/services/overdue_service.py::get_due_soon_deals`。
- **逾期（overdue）**：MEETED 狀態且已過到期日的交易。公開展示、信用扣分與通知
  皆以此為依據。實作：`overdue_service`。

- **AI 對話編排（chat orchestration）**：一輪 AI 對話的完整流程——tool 呼叫迴圈、
  consent 決策、follow-up 二次呼叫、history 寫入。實作：
  `ai/services/chat_orchestrator.py`。AI provider 經 `AIClient`/`Transport`
  seam 注入（生產：RequestsTransport；測試：ScriptedTransport）。

## 實體

- **OfficialBook（官方書目）**：依 ISBN 唯一的書目資訊（書名/作者/出版社/分類/封面）。
  多人的 SharedBook 可指向同一本。
- **SharedBook（分享書籍）**：某人實體的一本書，有 owner、keeper、狀態機
  （S/T/O/E/R…，django-fsm 管理）、流通性、最低信用等級。
- **BookPhoto（書況照片）**：附在 SharedBook 上的照片；面交照片（有 deal）
  存取受權限保護。
- **Deal（交易）**：两人之間對一冊 SharedBook 的互動，類型 LN/TF/RS/EX，
  狀態機 REQUESTED → RESPONDED → MEETED → DONE（可 CANCELLED），由
  django-fsm 管理。BR-3 ~ BR-12 為其業務規則編號。
- **LoanExtension（延長借閱）**：借閱者對 MEETED 交易的延期申請。
- **Rating（互評）**：交易完成後雙方互評。
- **Appeal（申訴）**：對交易糾紛的申訴流程。
- **TrustLevel（信用等級）**：由 trust_score 派生（0–3 級），影響可借冊數、
  借閱天數與編輯/切換書籍的權限。

## 慣例

- Service 層錯誤契約：失敗 raise `django.core.exceptions.ValidationError`
  （或 `PermissionDenied`），訊息為使用者可讀的中文；View 負責轉譯成
  messages / HTTP 回應。
- 狀態變更一律走 FSM transition（`protected=True`），禁止直接賦值 status。
