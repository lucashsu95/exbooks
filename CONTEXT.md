# CONTEXT.md — exbook domain 詞彙

exbook 是社區借書平台：成員把自己擁有的書共享出去（SharedBook），
透過 Deal 進行借用／返還／傳遞。系統核心是 Deal 狀態機與管束
成員行為的信任系統。

## 核心實體

- **SharedBook**（books）— 成員共享出借的書，狀態由 Deal 推進帶動。
- **Deal**（deals）— 交易記錄，五種類別：Loan 借用 (LN)、Restore 返還 (RS)、
  Transfer 傳遞 (TF)、Regress 回歸 (RG)、Except 例外處理 (EX)。
  狀態 REQUESTED → RESPONDED → MEETED → DONE / CANCELLED（django-fsm）。
- **LoanExtension**（deals）— 借用到期日的延期申請（Deal 的 sibling）。
- **ExchangeEvent**（deals）— Deal 狀態轉換的審計日誌。
- **Rating / DealMessage**（deals）— 面交後互評、雙方訊息。
- **OfficialBook / BookSet / Author / Publisher**（books）— 官方書目（參考用）。
- **WishListItem**（books）— 成員的想借清單。

## 成員與信任

- **UserProfile / TrustLevelConfig / TrustScoreLedger**（accounts）—
  信任分級與分數變更帳。
- **Violation / Appeal**（accounts）— 違規記錄與申訴（Appeal 是 FSM）。

## AI

- **ai app** — AI 聊天助理（SSE 串流、使用者同意在 consent_store service）；
  此 app 沒有 model。

## 模型位置

- `books/models/`、`deals/models/`（package）、`accounts/models.py`（單檔）
- 基底類別在 `core/models.py`：`BaseModel` → `UpdatableModel`；
  FSM 直接吃 `django_fsm`（`FSMField` protected、`transition`）。

## 架構約束（勿重翻案）

- Django 5.2 + MariaDB；service 層：業務邏輯只在 `services/`，
  View/Model 不帶業務邏輯。
- Deal 狀態機用 django-fsm，見 docs/adr/django-fsm-migration.md。
- 已知延期項目：docs/adr/2026-10-24-architecture-followups.md
  （F-1 `Deal.cancel()` 的 FSM 旁路炸彈、F-2 `create_deal` 缺
  `@transaction.atomic` 等）。
