# HTMX 導覽模式與優化指南

本文紀錄了 Exbooks 專案中導覽路由的 HTMX 整合模式，用於指導後續頁面開發以確保導覽的「優雅度」與效能。

## 1. 核心模式：View-Level HTMX 檢測

專案採用「主模板 + 局部包裝器」的模式，確保同一個 URL 既能處理全頁載入（SEO/初次訪問），也能處理 HTMX 局部更新（SPA 體驗）。

### 實作範例 (views.py)
```python
def my_view(request):
    context = { ... }
    # 檢測是否為 HTMX 請求
    if request.headers.get("HX-Request"):
        # 返回不含 base.html 繼承的局部模板
        return render(request, "app/partials/_view_wrapper.html", context)
    # 返回繼承 base.html 的全頁模板
    return render(request, "app/my_view.html", context)
```

## 2. 導覽標籤切換 (Tab Navigation)

針對 `/books/bookshelf/` 與 `/deals/` 等具有標籤分頁的頁面，使用 `hx-boost` 實現無縫切換。

### 模式定義
- **觸發器**：`<nav hx-boost="true" hx-target="#page-container" hx-swap="outerHTML transition:true">`
- **優點**：
  - 自動處理瀏覽器歷史記錄 (PushState)。
  - 減少約 40-60% 的資料傳輸量（跳過 Header/Footer/Nav）。
  - 配合 CSS View Transitions 實現平滑動畫。

## 3. 搜尋與篩選 (Search & Filter)

針對 `/books/` 搜尋頁面，採用「防抖 AJAX」模式。

### 模式定義
- **觸發器**：`hx-trigger="keyup changed delay:500ms"`
- **目標**：`hx-target="#results-container"`
- **事件恢復**：在 `htmx:afterSwap` 中重新初始化滾動監聽器或其他 JS 組件。

## 4. 待優化項目 (P1/P2)

- [ ] **底部導覽列 HTMX 化**：目前的導覽列跳轉仍觸發全頁邏輯，應改為 `hx-get` 配合 `#main-content` 替換。
- [ ] **快取機制**：針對 Deal Tab 的聚合查詢加入 30 秒快取。
- [ ] **平行化 Service 呼叫**：在個人資料頁面使用 ThreadPoolExecutor 優化統計數據獲取。

---
*最後更新：2026-04-11*
