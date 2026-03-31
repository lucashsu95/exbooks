# 手機版 UX 分析報告

> 分析日期：2026-03-30
> 分析範圍：Exbooks 共享書籍平台手機版使用者體驗

---

## 一、問題識別

### 🔴 嚴重問題（反人性設計）

#### 1. 導航架構混亂

**問題描述**：
- 有三種導航機制：Sidebar（左側抽屜）、Bottom Nav（底部導航）、Header 返回鍵
- Sidebar 和 Bottom Nav 功能重複（都有首頁、書架、通知、設定）
- 手機用戶習慣底部導航，Sidebar 在手機版是多餘的

**影響**：
- 用戶不知道用哪個導航
- 增加認知負擔
- 浪費螢幕空間

#### 2. 觸控區域不足

**問題描述**：
- 底部導航的 icon + 文字高度只有 `pt-3 pb-6`（約 44px），勉強達到 Apple 的 44pt 最小建議
- Sidebar 選單項目 `py-3`（24px 垂直 padding）太小
- 按鈕間距 `gap-1` 太緊，容易誤觸

**影響**：
- 誤觸率增加
- 操作挫折感
- 手大的用戶體驗差

#### 3. 頁面切換無載入狀態

**問題描述**：
- HTMX 使用 `hx-boost="true"` 做頁面切換，但沒有全域 loading indicator
- 用戶點擊後不知道是否有反應
- 網速慢時體驗差

**影響**：
- 用戶會重複點擊
- 不確定系統狀態
- 感覺卡頓

#### 4. 底部操作按鈕被系統 UI 遮擋

**問題描述**：
- 固定在底部的按鈕（如「確認面交完成」）使用 `fixed bottom-0`
- 沒有考慮 iPhone 的 Home Indicator（約 34px）
- 沒有考慮 Android 的 Navigation Bar

**影響**：
- 操作按鈕難以點擊
- 與系統 UI 衝突
- 特別影響 iPhone X 以後的機型

#### 5. 表單輸入與虛擬鍵盝衝突

**問題描述**：
- 留言輸入框在頁面底部
- 虛擬鍵盝彈出時會遮擋輸入框
- 沒有 `visualViewport` 處理

**影響**：
- 用戶看不到自己輸入的內容
- 無法確認訊息是否正確
- 需要來回縮放螢幕

---

### 🟡 中等問題（體驗不佳）

#### 6. Tab 切換無視覺回饋

**問題描述**：
- HTMX tab 切換使用 `transition:0.2s`，但這是 CSS transition
- 切換時整個頁面消失再出現，而非平滑過渡
- 用戶會感覺「閃爍」

#### 7. 缺少手勢支援

**問題描述**：
- 沒有下拉刷新
- 沒有左滑返回
- 沒有右滑呼叫 Sidebar
- 手機用戶習慣手勢操作，全部都要靠按鈕

#### 8. 搜尋 Modal 的問題

**問題描述**：
- 搜尋 Modal 從上方滑入，不符合手機習慣
- 應該從底部滑入或全螢幕展開
- 鍵盤彈出時會有動畫問題

#### 9. 書籍卡片資訊密度過高

**問題描述**：
- 卡片內容擠在一起（標題、作者、標籤、持有者）
- 手機螢幕小，閱讀困難
- `truncate` 截斷標題，用戶看不到完整資訊

#### 10. 缺少骨架屏

**問題描述**：
- 載入時顯示空白或舊內容
- 沒有 skeleton loading
- 用戶感覺「卡住」

---

### 🟢 輕微問題（可優化）

#### 11. FAB 按鈕位置衝突

**問題描述**：
- FAB（新增書籍）在 `bottom-24 right-6`
- 與 Bottom Nav 距離太近
- 可能誤觸

#### 12. Toast 位置問題

**問題描述**：
- Toast 在 `top-4 right-4`
- 劉海螢幕可能被遮擋
- 應該考慮 safe area

---

## 二、改善方案

### 方案 A：導航統一（優先級：最高）

#### 問題分析

**現狀問題**：
```
Sidebar（左抽屜）+ Bottom Nav + Header 返回鍵 = 三套導航
```

這種設計在手機版造成：
1. 用戶困惑（該用哪個導航？）
2. 螢幕空間浪費
3. 維護成本增加

#### 改善方案

##### 1. 廢除 Sidebar

**實作方式**：
- 手機版完全移除 `_sidebar.html` 的引入
- 移除 Header 的漢堡選單按鈕
- 移除相關的 JavaScript（`toggleSidebar()`）

**需要修改的檔案**：
- `templates/base.html`：移除 `{% include '_sidebar.html' %}`
- `templates/_sidebar.html`：可以保留給桌面版使用（如果未來需要）
- 所有使用漢堡選單的 Header

##### 2. Bottom Nav 重新設計

**改善後的 Bottom Nav 結構**：

```
┌─────────────────────────────────────┐
│  首頁  │  書架  │  交易  │  個人  │
│  🏠   │  📚   │  🔄   │  👤   │
└─────────────────────────────────────┘
```

**功能整合**：
- **首頁**：探索書籍（原 books:list）
- **書架**：我的書籍（原 books:bookshelf）
- **交易**：合併「通知中心」和「交易紀錄」，帶未讀 badge
- **個人**：設定 + 個人資料（原 accounts:profile）

##### 3. Header 簡化

**改善前**：
```html
<button onclick="toggleSidebar()">☰</button>
<h1>標題</h1>
<button>通知</button>
```

**改善後**：
```html
<a href="javascript:history.back()">
  <span class="material-symbols-outlined">arrow_back</span>
</a>
<h1>標題</h1>
<div><!-- 可能放其他操作 --></div>
```

#### 技術實作

##### base.html 修改

```html
<!-- 移除 Sidebar 引入 -->
<!-- {% include '_sidebar.html' %} --> <!-- 刪除這行 -->

<!-- 修改 main wrapper，移除 sidebar 相關空間 -->
<div class="relative flex h-auto min-h-screen w-full flex-col bg-background-light overflow-x-hidden fade-in">
```

##### _bottom_nav.html 重新設計

```html
<!-- Bottom Navigation Bar - 改善版 -->
<nav class="fixed bottom-0 left-0 right-0 border-t border-slate-200 bg-white/95 backdrop-blur-md z-20 safe-area-pb">
  <div class="flex justify-around items-center h-16">
    <!-- 首頁 -->
    <a class="flex flex-col items-center justify-center min-w-[64px] min-h-[56px] gap-1
              {% if is_home_active %}text-primary{% else %}text-slate-400{% endif %}"
       href="{% url 'books:list' %}">
      <span class="material-symbols-outlined text-2xl {% if is_home_active %}fill-1{% endif %}">home</span>
      <span class="text-[10px] font-bold uppercase tracking-wider">首頁</span>
    </a>
    
    <!-- 書架 -->
    <a class="flex flex-col items-center justify-center min-w-[64px] min-h-[56px] gap-1
              {% if is_bookshelf_active %}text-primary{% else %}text-slate-400{% endif %}"
       href="{% url 'books:bookshelf' %}">
      <span class="material-symbols-outlined text-2xl {% if is_bookshelf_active %}fill-1{% endif %}">auto_stories</span>
      <span class="text-[10px] font-bold uppercase tracking-wider">書架</span>
    </a>
    
    <!-- 交易（合併通知） -->
    <a class="flex flex-col items-center justify-center min-w-[64px] min-h-[56px] gap-1 relative
              {% if is_deals_active %}text-primary{% else %}text-slate-400{% endif %}"
       href="{% url 'deals:list' %}">
      <span class="material-symbols-outlined text-2xl {% if is_deals_active %}fill-1{% endif %}">swap_horiz</span>
      <span class="text-[10px] font-bold uppercase tracking-wider">交易</span>
      <!-- 未讀 badge -->
      <span id="nav-notification-badge" class="absolute -top-1 right-2 bg-rose-500 text-white text-[10px] font-bold rounded-full min-w-[18px] h-[18px] flex items-center justify-center">
        3
      </span>
    </a>
    
    <!-- 個人 -->
    <a class="flex flex-col items-center justify-center min-w-[64px] min-h-[56px] gap-1
              {% if is_profile_active %}text-primary{% else %}text-slate-400{% endif %}"
       href="{% url 'accounts:profile' %}">
      <span class="material-symbols-outlined text-2xl {% if is_profile_active %}fill-1{% endif %}">person</span>
      <span class="text-[10px] font-bold uppercase tracking-wider">個人</span>
    </a>
  </div>
</nav>

<style>
  /* Safe Area 支援 */
  .safe-area-pb {
    padding-bottom: max(12px, env(safe-area-inset-bottom));
  }
</style>
```

---

### 方案 B：觸控友善設計（優先級：最高）

#### 問題分析

**現狀問題**：
1. 觸控區域太小（低於 48x48px 建議值）
2. 按鈕間距不足
3. 沒有處理 iPhone X+ 的 Safe Area
4. 固定底部元素被系統 UI 遮擋

#### 改善方案

##### 1. 增大觸控區域

**設計原則**：
- Apple HIG：最小觸控區域 44x44 pt
- Material Design：最小觸控區域 48x48 dp
- 建議使用 **48x48px** 作為最小值

**CSS 實作**：

```css
/* 全域觸控友善樣式 */
.touch-target {
  min-width: 48px;
  min-height: 48px;
}

/* 按鈕間距至少 8px */
.gap-touch {
  gap: 8px;
}

/* 卡片點擊區域擴大 */
.card-touch {
  padding: 16px;
  margin: -8px; /* 抵消 padding，保持視覺間距 */
}
```

##### 2. Bottom Nav 改善

**改善前**：
```html
<a class="flex flex-col items-center gap-1 pb-6 pt-3">
```

**改善後**：
```html
<a class="flex flex-col items-center justify-center min-w-[64px] min-h-[56px] gap-1">
```

**數值說明**：
- `min-w-[64px]`：確保每個導航項目有足夠寬度
- `min-h-[56px]`：超過 48px 建議值，增加舒適度
- `gap-1` → `gap-2`：增加 icon 和文字間距

##### 3. Safe Area 支援

**問題說明**：
iPhone X 以後的機型有 Home Indicator（底部橫條），約佔 34px。如果不處理，底部導航會被遮擋。

**CSS 實作**：

```css
/* Safe Area 變數 */
:root {
  --safe-area-inset-top: env(safe-area-inset-top, 0px);
  --safe-area-inset-bottom: env(safe-area-inset-bottom, 0px);
  --safe-area-inset-left: env(safe-area-inset-left, 0px);
  --safe-area-inset-right: env(safe-area-inset-right, 0px);
}

/* 固定底部元素 */
.fixed-bottom-safe {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  padding-bottom: max(16px, env(safe-area-inset-bottom));
}

/* 固定頂部元素 */
.fixed-top-safe {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  padding-top: max(16px, env(safe-area-inset-top));
}

/* Toast 位置 */
.toast-safe {
  top: max(16px, env(safe-area-inset-top));
  right: max(16px, env(safe-area-inset-right));
}
```

##### 4. 頁面底部留白

**問題**：內容被 Bottom Nav 遮擋

**改善方式**：

```html
<!-- 頁面主內容 -->
<main class="pb-20 safe-area-content-pb">
  <!-- 內容 -->
</main>

<style>
.safe-area-content-pb {
  padding-bottom: calc(64px + env(safe-area-inset-bottom, 0px));
  /* 64px = Bottom Nav 高度 (56px) + 額外留白 (8px) */
}
</style>
```

##### 5. FAB 按鈕位置

**改善前**：
```html
<a class="fixed bottom-24 right-6 ...">
```

**改善後**：
```html
<a class="fixed right-4 fab-safe-bottom ...">
```

```css
.fab-safe-bottom {
  bottom: calc(72px + env(safe-area-inset-bottom, 0px));
  /* 72px = Bottom Nav (56px) + 間距 (16px) */
}
```

##### 6. 按鈕觸控改善

**所有按鈕統一規格**：

```html
<!-- 主要按鈕 -->
<button class="min-h-[48px] px-6 py-3 rounded-xl bg-primary text-white font-bold active:scale-[0.98] transition-transform">
  確認
</button>

<!-- 次要按鈕 -->
<button class="min-h-[48px] px-6 py-3 rounded-xl border border-slate-200 text-slate-700 font-medium active:scale-[0.98] transition-transform">
  取消
</button>

<!-- Icon 按鈕 -->
<button class="min-w-[48px] min-h-[48px] flex items-center justify-center rounded-full hover:bg-slate-100 active:scale-95 transition-all">
  <span class="material-symbols-outlined">close</span>
</button>
```

---

## 三、實作優先級

| 優先級 | 項目 | 預估工時 | 影響範圍 |
|--------|------|----------|----------|
| 🔴 P0 | Safe Area 支援 | 2h | 全域 |
| 🔴 P0 | 觸控區域增大 | 3h | 全域 |
| 🔴 P0 | 導航統一（廢除 Sidebar） | 4h | 導航相關模板 |
| 🟡 P1 | Bottom Nav 重新設計 | 2h | _bottom_nav.html |
| 🟡 P1 | Header 簡化 | 2h | 所有頁面 Header |
| 🟡 P1 | FAB 位置調整 | 1h | my_bookshelf.html |

---

## 四、驗收標準

### 方案 A 驗收

- [ ] 手機版看不到 Sidebar
- [ ] Header 只有返回鍵 + 標題
- [ ] Bottom Nav 有 4 個項目
- [ ] 交易項目有未讀 badge
- [ ] 點擊導航項目可正確跳轉

### 方案 B 驗收

- [ ] 所有導航項目觸控區域 ≥ 48px
- [ ] 底部元素不被 Home Indicator 遮擋
- [ ] 內容不被 Bottom Nav 遮擋
- [ ] FAB 按鈕可正常點擊
- [ ] Toast 不被劉海遮擋

---

## 五、注意事項

1. **漸進式改善**：建議先完成 P0 項目，驗證無誤後再進行 P1
2. **測試裝置**：需在 iPhone X+ 和 Android 全面屏裝置測試 Safe Area
3. **回溯相容**：舊版瀏覽器不支援 `env(safe-area-inset-*)`，需有 fallback
4. **文件更新**：修改完成後更新 AGENTS.md 記錄變更
