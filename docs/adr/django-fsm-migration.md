# ADR: 採用 django-fsm 重構 Deal 狀態機

**Date**: 2026-03-29

**Status**: Accepted

## Context

Deal 模型有 5 個狀態（REQUESTED, RESPONDED, MEETED, DONE, CANCELLED），目前狀態轉換邏輯手刻在 `deal_service.py`。現有問題：

1. **狀態檢查散落各函式** — 6 處重複的 `deal.status != Deal.Status.REQUESTED` 檢查
2. **無編譯期保護非法狀態轉換** — 可直接 `deal.status = 'D'` 跳過中間狀態
3. **狀態轉換副作用分散** — 通知、書籍狀態變更散落各函式
4. **測試覆蓋困難** — 每個轉換需手動 setup 正確前置狀態
5. **無狀態轉換日誌** — 無法追蹤誰在何時觸發了哪個轉換

專案約束：

- Django 5.2 + MariaDB
- Service 層架構（不允許 View/Model 有業務邏輯）
- 需要追蹤交易糾紛審計

## Options Considered

### Option 1: 維持現狀（手刻）

**Pros:**
- 無需學習新套件
- 不需要遷移成本

**Cons:**
- 狀態檢查邏輯持續重複
- 無法防止非法狀態轉換
- 維護成本隨狀態數量指數增長

### Option 2: 採用 django-fsm

**Pros:**
- 宣告式狀態轉換定義
- `protected=True` 防止直接賦值
- Signal 處理副作用
- 內建狀態圖可視化
- 社群活躍（django-fsm-2 由 viewflow 維護）

**Cons:**
- 需要遷移現有程式碼
- 團隊學習曲線

### Option 3: 自行實作簡化版狀態機

**Pros:**
- 完全控制實作細節

**Cons:**
- 重複造輪子
- 缺乏社群支援
- 需要自行維護

## Trade-off Matrix

| Option | Performance | Maintainability | Cost | Complexity | Risk |
|--------|-------------|-----------------|------|------------|------|
| 維持現狀 | 高 | 低 | 低 | 高 | 高 |
| 採用 django-fsm | 高 | 高 | 中 | 中 | 低 |
| 自行實作 | 高 | 中 | 高 | 高 | 中 |

## Decision

**採用 django-fsm-2** 遷移 Deal 狀態機。

理由：

1. Deal + SharedBook 狀態耦合嚴重，手刻維護成本指數增長
2. 符合專案架構 — Service 層仍可保留，FSM 只處理狀態驗證
3. 社群活躍 — django-fsm-2 由 viewflow 維護，Django 5.x 相容
4. 降低技術債 — 統一狀態機架構，降低維護成本

## Consequences

### Positive

- 狀態檢查邏輯集中管理
- 非法狀態轉換有編譯期保護
- 副作用透過 Signal 統一處理
- 狀態轉換日誌可追蹤
- 測試覆蓋更容易

### Negative

- 需要遷移現有程式碼（約 84 小時）
- 團隊需要學習 django-fsm API

### Neutral

- Model 層會新增 @transition 方法
- Service 層改為調用 Model 的 FSM 方法
- 需要建立 Signal 處理模組

## Migration Scope

| Model | 狀態數 | 優先級 | 預估工時 |
|-------|--------|--------|----------|
| Deal | 5 | P0 | 20h |
| SharedBook | 8 | P0 | 16h |
| LoanExtension | 3 | P1 | 8h |
| Appeal | 5 | P1 | 8h |

**總工時：84 小時（約 3 週單人工作）**

## References

- [django-fsm-2 GitHub](https://github.com/django-commons/django-fsm-2)
- [Django FSM Documentation](https://django-fsm.readthedocs.io/)
