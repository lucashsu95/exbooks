# Exbook 專案開發報告
**Commit 範圍**: `2521794` ~ `e88abf`  
**開發者**: lucashsu95  
**時間範圍**: 2026-03-18 ~ 2026-03-26  
**總提交數**: 22 commits  
**程式碼變更**: +9,157 行 / -3,348 行（淨增加 5,809 行）  
**影響檔案**: 104 個檔案

---

## 一、新功能開發 (Features)

### 1. Web Push 通知系統
**Commit**: `5a78604`

- 新增 `PushSubscription` Model 儲存用戶訂閱資訊
- 新增 `WebPushConfig` Model 管理 VAPID 金鑰
- 實作 `push_service.py` 封裝 pywebpush 發送邏輯
- 新增 `push_subscribe/push_unsubscribe` Views
- 整合 `notification_service.py` 串接 Push 發送
- 前端實作 Push 訂閱註冊邏輯於 `base.html`
- 新增 VAPID 金鑰生成指令 `generate_vapid_keys`

### 2. 信任機制核心功能
**Commit**: `ef94d10`

- 新增 UserProfile 信任相關欄位：
  - `trust_level`（信用等級）
  - `successful_returns`（成功歸還次數）
  - `overdue_count`（逾期次數）
- 實作信用等級計算服務 `trust_service.py`
- 實作逾期公開服務 `overdue_service.py`
- 整合借閱權限檢查到 `deal_service.create_deal`
- 新增每日信用等級更新管理指令

**信用等級規則**:
| 等級 | 條件 |
|------|------|
| Level 0 (新手) | 完成交易 < 3 或 逾期 ≥ 3 次 |
| Level 1 (一般) | 完成交易 ≥ 3 且 逾期 < 3 次 |
| Level 2 (可信) | 完成交易 ≥ 10 + 評價均分 ≥ 4 且 逾期 < 2 次 |
| Level 3 (優良) | 完成交易 ≥ 30 + 評價均分 ≥ 4.5 且 逾期 = 0 |

**逾期公開規則**:
- 逾期 3 天：書籍詳情頁顯示警告
- 逾期 7 天：全站逾期名單
- 逾期 14 天：嚴重逾期標記

### 3. 申訴系統
**Commits**: `1c7f532`, `bf23f41`

- 新增 `Appeal` Model 與狀態流轉邏輯
- 實作 `appeal_service.py` 處理業務邏輯與通知發送
- 整合 `AppealAdmin` 管理介面與快捷操作
- 新增申訴相關通知類型
- 完整單元測試與服務層測試
- 前端模板：List, Form, Detail

### 4. 套書管理功能
**Commit**: `df9f06a`

- 新增 BookSet CRUD 功能（Service + Views + Templates）
- 新增書籍例外狀態處理（E/L/D 狀態申請與審核）
- 新增例外處理相關路由與模板
- 整合套書資訊與例外按鈕到書籍詳情頁

### 5. 書況追蹤時間線
**Commit**: `b70dd6e`

- 書況追蹤時間線 UI：於書籍詳情頁顯示上架、交易、延長等歷程
- 即將到期提醒：支援 7/14/30 天篩選，顯示剩餘天數與到期日
- 書籍歸還確認流程：持有者可確認歸還並重新上架「閱畢即還」書籍

### 6. 通知中心與用戶頁面增強
**Commit**: `6e20374`

- 新增通知中心（列表頁、未讀 badge、標記已讀）
- 增強用戶個人頁面（上架書籍、借閱紀錄、評價 tabs）
- 新增信用評價查詢頁面（評分詳情、歷史記錄）
- 新增用戶活動統計（貢獻/借閱/出借次數）
- 新增延長借閱 UI（申請/審核/取消）
- 新增書籍搜尋篩選增強（出版社、狀態、流通性、分頁）
- 更新側邊欄連結（願望書車、通知中心、交易紀錄）

### 7. 資料匯出功能
**Commit**: `8d101b3`

- 資料匯出：用戶可下載個人資料 JSON，每日限 3 次
- 可取書時間 UI：Alpine.js 動態表單讓用戶設定可取書時段
- 搜尋結果信用顯示：在書籍列表顯示持有者信用等級徽章

### 8. 系統架構文件
**Commit**: `e4af99a`

- 新增系統架構文件 `docs/0325_exbook_architecture.pdf`
- 新增設計理念文件 `docs/0325_exbook_design_philosophy.pdf`
- 新增簡報文件 `docs/0325_exbook_presentation.pdf`

---

## 二、程式碼重構 (Refactoring)

### 1. Crispy Forms 整合
**Commits**: `0c6806c`, `9192c85`

- 安裝 `django-crispy-forms` + `crispy-tailwind` 並配置 settings.py
- 清理 `accounts/forms.py`、`books/forms.py`、`deals/forms.py` 的 dark: 內聯樣式
- 為所有表單類別新增 FormHelper（共 15 個）
- 建立 3 個自訂 widget templates：
  - `image_preview`（圖片預覽）
  - `schedule_picker`（時間選擇器）
  - `rating_slider`（評分滑桿）
- 重構 login.html, signup.html, socialaccount/signup.html 為 Crispy Forms
- 重構 complete_profile.html, register.html, profile_edit.html 為 Crispy Forms
- 重構 book_add.html, book_set_create.html 為 Crispy Forms

### 2. 深色模式樣式移除
**Commits**: `f1002da`, `9192c85`

- 移除 32 個模板檔案中的所有 dark: Tailwind 類別
- 涵蓋 layout、accounts、books、deals 及其 partials
- 總計移除 608 行 dark: 相關樣式
- 329 測試全數通過

### 3. 信用等級徽章模板抽離
**Commit**: `e88abf4`

- 抽離信用等級徽章為共用 partial 模板
- 新增 `templates/partials/trust_badge.html`
- 新增 `templates/partials/trust_badge_inline.html`
- 減少重複程式碼，提升維護性

### 4. 死碼清理
**Commits**: `cbb6f79`, `0c6806c`

- 移除 `accounts/forms.py` 中的 RegisterForm 類別（已不再使用）
- 刪除 `templates/registration/login.html`（allauth 使用 account/login.html）
- 刪除 `templates/stitch_original/` 死碼（8 檔案，1476 行）

---

## 三、UI/UX 改進

### 1. Glassmorphism 設計風格
**Commits**: `a493683`, `8cfd0a1`

- Header: backdrop-blur-md, bg-white/80, hover effects
- Search: glass container with transparent background
- Categories: glass chips with active state shadow
- Book cards: glass cards with hover transitions
- Detail page: glass navigation, hero, keeper card
- Condition section: glass container with gradient rating
- Action buttons: enhanced glass footer with shadows

### 2. 書籍列表與詳情頁重新設計
**Commit**: `8cfd0a1`

- 新增漸層背景 Hero Section
- 強化搜尋框樣式（圓角、陰影、焦點效果）
- 分類標籤新增縮放動畫
- 書籍卡片重新設計（圓角升級、hover 效果）
- NEW 標籤重新設計

### 3. 個人資料頁增強
**Commit**: `33a4683`

- profile.html 新增信用等級卡片與借閱限制說明
- profile.html 新增活動統計區塊（貢獻書籍、借閱、出借次數）
- public_profile.html 新增信用等級徽章與統計資訊顯示

---

## 四、錯誤修復 (Fixes)

| Commit | 問題 | 解決方案 |
|--------|------|----------|
| `420769d` | E2E 測試選擇器過於寬鬆 | 使用更精確的選擇器，限定在 main 元素內，排除特定路徑 |
| `92a0dd7` | 登出 URL 名稱錯誤 | 將 'logout' 改為 'account_logout' 以符合 allauth 命名 |
| `a4ace8c` | 分類滾動容器 padding 錯誤 | 使用 py-2 取代 pb-2 |
| `98bcbe1` | 分類標籤被切到 | 新增 -mx-4 px-4 水平 padding |

---

## 五、測試覆蓋

### 新增測試檔案

| 檔案 | 測試內容 |
|------|----------|
| `accounts/tests/test_appeal_service.py` | 申訴服務層測試 |
| `accounts/tests/test_export_service.py` | 資料匯出服務測試 |
| `accounts/tests/test_trust_service.py` | 信任機制服務測試 |
| `books/tests/test_book_search.py` | 書籍搜尋測試 |
| `tests/deals/test_extension_views.py` | 延長借閱視圖測試 |
| `tests/deals/test_overdue_service.py` | 逾期服務測試 |

### 測試狀態
- 329 測試全數通過（於 `f1002da` 提交時驗證）

---

## 六、基礎設施與工具

### 新增管理指令

| 指令 | 功能 |
|------|------|
| `generate_vapid_keys` | 生成 VAPID 金鑰 |
| `update_trust_levels` | 每日信用等級更新 |
| `process_due_books` | 處理到期書籍 |
| `send_due_reminders` | 發送到期提醒 |

### 新增依賴

| 套件 | 用途 |
|------|------|
| `django-crispy-forms` | 表單渲染 |
| `crispy-tailwind` | Tailwind 樣式整合 |

---


---

## 八、總結

本開發週期涵蓋了多個核心功能實作，包括：

1. **Web Push 通知系統**：建立完整的推播基礎設施
2. **信任機制**：實作信用等級計算與逾期管理
3. **申訴系統**：完整的申訴流程與管理介面
4. **套書管理**：新增套書 CRUD 與例外處理
5. **程式碼品質**：Crispy Forms 整合、死碼清理、dark: 樣式移除
6. **UI/UX 改進**：Glassmorphism 設計風格、響應式優化

整體而言，本週期重點在於建立使用者信任機制與提升系統可維護性，同時持續優化使用者體驗。
