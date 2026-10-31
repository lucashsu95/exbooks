# Exbooks 色彩設計盤點

> 盤點日期：2026-10-26  
> 範圍：產品 UI、共用元件、錯誤頁、登入入口、像素寵物，以及 repo 內的簡報與測試報告樣式。  
> 目的：把目前已存在的色塊與色碼集中記錄；本文件是現況 inventory，不代表所有顏色都已經被統一成 design token。

## 讀法與來源

- **產品主題色**以 [`static/js/tailwind-config.js`](./static/js/tailwind-config.js) 為準。
- **Tailwind 公開色階**是由 Tailwind class 產生，模板通常不直接寫 hex；下表列出目前實際出現的 class 家族及其標準色碼。
- **元件專用色**保留其實作中的 CSS custom property 或 literal，並標出來源檔案。
- **透明色**以 `rgba()` 記錄；同一個 RGB 以不同 alpha 使用時分開列出。
- Google 標誌、Mermaid/Graphviz 圖表、Marp 簡報與 k6 報告屬於外部或文件視覺，不應直接視為產品 UI token。

## 1. 產品核心 palette

| 色塊 | Token / 色碼 | 目前用途 | 來源 |
|---|---|---|---|
| <span style="display:inline-block;width:1.2em;height:1.2em;background:#14b8a6"></span> | `primary` · `#14B8A6` · rgb(20, 184, 166) | 主要 CTA、品牌標題、選取狀態、信任進度、像素寵物身體 | [`tailwind-config.js`](./static/js/tailwind-config.js#L6)、[`404.html`](./core/templates/404.html#L32) |
| <span style="display:inline-block;width:1.2em;height:1.2em;background:#0d9488"></span> | `secondary` · `#0D9488` · rgb(13, 148, 136) | hover、連結、較深的品牌狀態 | [`tailwind-config.js`](./static/js/tailwind-config.js#L7)、[`404.html`](./core/templates/404.html#L39) |
| <span style="display:inline-block;width:1.2em;height:1.2em;background:#06b6d4"></span> | `accent` · `#06B6D4` · rgb(6, 182, 212) | 輔助強調、像素寵物臉頰、k6 報告 cyan | [`tailwind-config.js`](./static/js/tailwind-config.js#L8)、[`pixel-pet.css`](./static/css/pixel-pet.css#L5) |
| <span style="display:inline-block;width:1.2em;height:1.2em;background:#f6f7f8"></span> | `background-light` · `#F6F7F8` | 淺色頁面背景、404 背景 | [`tailwind-config.js`](./static/js/tailwind-config.js#L9)、[`404.html`](./core/templates/404.html#L14) |
| <span style="display:inline-block;width:1.2em;height:1.2em;background:#101822"></span> | `background-dark` · `#101822` | Tailwind dark mode 背景 token | [`tailwind-config.js`](./static/js/tailwind-config.js#L10) |
| <span style="display:inline-block;width:1.2em;height:1.2em;background:#f2f2f7"></span> | `--ios-bg` · `#F2F2F7` | 書籍 UI 的 iOS 風格頁面背景 | [`book-ui.css`](./static/css/book-ui.css#L3) |
| <span style="display:inline-block;width:1.2em;height:1.2em;background:#000000"></span> | OLED ink · `#000000` | OLED 文字樣式 | [`book-ui.css`](./static/css/book-ui.css#L65-L67) |

### 核心色彩關係

```text
ground       #F6F7F8 / #F2F2F7 / #101822
ink          Tailwind slate-900 (#0F172A) 或 black (#000000)
brand        primary #14B8A6
brand-hover  secondary #0D9488
accent       #06B6D4
```

目前產品主色是 teal/cyan 系，而不是文件中偶爾出現的 blue/purple。新 UI 優先使用 `primary`、`secondary`、`accent` 與 slate 色階，不要另造近似 teal。

## 2. Tailwind 中實際使用的色階

以下是模板目前使用的 Tailwind 顏色 class 對應的標準 hex。`white`、`black`、`transparent` 是 Tailwind 基本色；`primary`、`secondary`、`accent` 見上一節。

### Neutral

| Class family | 色碼 |
|---|---|
| `white` | `#FFFFFF` |
| `black` | `#000000` |
| `slate-50` / `slate-100` / `slate-200` / `slate-300` | `#F8FAFC` / `#F1F5F9` / `#E2E8F0` / `#CBD5E1` |
| `slate-400` / `slate-500` / `slate-600` / `slate-700` | `#94A3B8` / `#64748B` / `#475569` / `#334155` |
| `slate-800` / `slate-900` | `#1E293B` / `#0F172A` |
| `gray-100` / `gray-400` / `gray-500` / `gray-600` / `gray-700` | `#F3F4F6` / `#9CA3AF` / `#6B7280` / `#4B5563` / `#374151` |

### Semantic / status

| Class family | 色碼 | 常見語意 |
|---|---|---|
| `blue-50` / `blue-100` / `blue-200` | `#EFF6FF` / `#DBEAFE` / `#BFDBFE` | 資訊、審核中、一般選取 |
| `blue-400` / `blue-500` / `blue-600` / `blue-700` / `blue-800` / `blue-900` | `#60A5FA` / `#3B82F6` / `#2563EB` / `#1D4ED8` / `#1E40AF` / `#1E3A8A` | 書籍選取元件、資訊文字 |
| `green-50` / `green-100` | `#F0FDF4` / `#DCFCE7` | 成功背景 |
| `green-500` / `green-600` / `green-700` / `green-800` | `#22C55E` / `#16A34A` / `#15803D` / `#166534` | 成功、信任等級 |
| `emerald-100` / `emerald-600` / `emerald-700` | `#D1FAE5` / `#059669` / `#047857` | 成功或完成狀態 |
| `amber-50` / `amber-100` / `amber-200` | `#FFFBEB` / `#FEF3C7` / `#FDE68A` | 警告、待處理 |
| `amber-400` / `amber-500` / `amber-600` / `amber-700` / `amber-800` | `#FBBF24` / `#F59E0B` / `#D97706` / `#B45309` / `#92400E` | 警告文字與信任等級 |
| `red-50` / `red-100` / `red-200` | `#FEF2F2` / `#FEE2E2` / `#FECACA` | 錯誤背景 |
| `red-400` / `red-500` / `red-600` / `red-700` / `red-800` | `#F87171` / `#EF4444` / `#DC2626` / `#B91C1C` / `#991B1B` | 錯誤、拒絕、危險操作 |
| `rose-50` / `rose-100` / `rose-200` | `#FFF1F2` / `#FFE4E6` / `#FECDD3` | 停權、異常背景 |
| `rose-400` / `rose-500` / `rose-600` / `rose-700` | `#FB7185` / `#F43F5E` / `#E11D48` / `#BE123C` | 停權、異常文字 |
| `cyan-500` | `#06B6D4` | 輔助強調、文件報告 |
| `purple-500` | `#8B5CF6` | k6 報告圖表；非產品主題色 |

### 使用中的 opacity variants

Tailwind opacity class 會套用於上述基礎色，現況包括：

- `bg-primary/5`, `/10`, `/15`, `/20`, `/90`
- `text-primary/60`, `/80`
- `border-primary/10`, `/20`, `/30`
- `ring-primary/20`, `/50`
- `bg-white/50`, `/60`, `/65`, `/70`, `/75`, `/80`, `/90`, `/95`
- `bg-black/40`, `/50`, `/60`；`from-black/20`, `/40`, `/80`
- `bg-slate-50/50`、`bg-slate-100/80`、`bg-slate-100/90`、`bg-slate-200/70`、`bg-slate-200/80`
- `bg-blue-50/70`、`bg-blue-400/10`、`bg-blue-500/10`
- `bg-green-100/80`、`bg-rose-100/80`、`border-amber-100/50`、`border-amber-200/80`

## 3. 元件與頁面專用色

### 書籍 UI、玻璃導覽與 Bento

來源：[`static/css/book-ui.css`](./static/css/book-ui.css)

| 色碼 | 用途 |
|---|---|
| `rgba(19, 109, 236, 0.5)` | `--primary-glow`，藍色 glow（目前與 teal 主題不一致） |
| `rgba(20, 184, 166, 0.08)` / `rgba(20, 184, 166, 0.05)` | mesh aura 的 teal 光暈 |
| `rgba(13, 148, 136, 0.05)` | mesh aura 的深 teal 光暈 |
| `rgba(6, 182, 212, 0.08)` | mesh aura 的 cyan 光暈 |
| `rgba(255, 255, 255, 0.7)` / `0.85` | glass nav 表面（一般 / scrolled） |
| `rgba(0, 0, 0, 0.1)` | glass nav 底線 |
| `rgba(0, 0, 0, 0.05)` | glass nav shadow |
| `rgba(20, 184, 166, 0.25)` | active category shadow |
| `rgba(0, 0, 0, 0.04)` | Bento 邊框 |
| `rgba(0, 0, 0, 0.02)` | Bento shadow |
| `#FFFFFF` / `#000000` | Bento surface / OLED text |

### 交易 UI

來源：[`static/css/deal-ui.css`](./static/css/deal-ui.css)

| 元件 | 背景 | 文字 / 邊框 |
|---|---|---|
| `.deal-card` | `rgba(255, 255, 255, 0.85)` | `rgba(255, 255, 255, 0.7)` 邊框 |
| `.deal-card` shadow | — | `rgba(148, 163, 184, 0.2)`；hover `0.28` |
| `.deal-card::before` | `rgba(255, 255, 255, 0.65)` → `rgba(255, 255, 255, 0.2)` → `rgba(20, 184, 166, 0.05)` | 漸層 overlay |
| `.deal-card:hover` | — | `rgba(203, 213, 225, 0.9)` 邊框 |
| `status-badge-amber` | `#FEF3C7` | `#B45309` |
| `status-badge-blue` | `#DBEAFE` | `#1D4ED8` |
| `status-badge-green` | `#DCFCE7` | `#15803D` |
| `status-badge-gray` | `#F3F4F6` | `#4B5563` |
| `status-badge-red` | `#FEE2E2` | `#B91C1C` |
| `.deal-tab` | transparent | `#64748B`；hover `#334155` |
| `.deal-tab-active` | `#FFFFFF` | `#14B8A6`，邊框 `rgba(20, 184, 166, 0.2)` |
| `.deal-tab-active` shadow | — | `rgba(20, 184, 166, 0.15)` |

### 書籍選擇 widget

來源：[`static/css/widgets/book-select.css`](./static/css/widgets/book-select.css)

| 色碼 | 用途 |
|---|---|
| `#FFFFFF` | 卡片與選取 icon 背景 |
| `#F1F5F9` | 未選取卡片邊框 |
| `#F8FAFC` | hover 背景 |
| `#3B82F6` | checked 邊框、選取 icon 背景與邊框 |
| `rgba(59, 130, 246, 0.05)` / `0.1` | checked 背景 / shadow |
| `#CBD5E1` | 未選取 icon 邊框 |

此元件目前使用 blue，而非產品 `primary` teal；若要統一品牌，這是需要明確決策的遷移點。

### MeDou 像素寵物

來源：[`static/js/pixel-pet.js`](./static/js/pixel-pet.js)、[`static/css/pixel-pet.css`](./static/css/pixel-pet.css)、精靈圖 [`static/img/medou/medou-sheet.png`](./static/img/medou/medou-sheet.png)

米豆是點陣圖精靈，不再由 CSS 變數上色：白色口鼻／胸毛在深色模式也維持白色，深色模式只對浮動小版加一圈淡白 `drop-shadow` 勾邊（聊天 header 的大版固定白底，不加）。精靈圖是一張水平排列的索引色 PNG，每格 48×48 px、共 10 格；顯示尺寸必須是 48 的整數倍（目前浮動小版與聊天 header 都是 48 px，`image-rendering: pixelated`），用 `background-position` 切換影格，JS 只在影格真的改變時寫入 `--mipet-frame`。

| 影格 | 狀態 | 來源 | 說明 |
|---|---|---|---|
| 0 / 1 | `idle` | s0 / s0 衍生 | 正面坐姿；偶爾眨眼（衍生影格：閉眼） |
| 2 | `thinking` | s1 | 歪頭、手托下巴、「?」 |
| 3 / 4 | `talking` | s2 / s2 衍生 | 側身張嘴、「…」對話框；`MiPet.pulse()` 帶動開合，最後一次 pulse 後約 600 ms 闔嘴（衍生影格：閉嘴） |
| 5 | `error` | s3 | >< 眼、紅色「!」、汗滴；2.5 秒後回 `idle` |
| 6 | `sleep` | s4 | 趴睡、Zzz；60 秒無互動自動進入 |
| 7 | `hover` | s5 | 眨眼＋游標；只在 `idle` / `sleep` 時滑鼠移入或鍵盤聚焦浮動小版才觸發（其他狀態不打斷），離開後回 `idle` |
| 8 | `notify` | s6 | 側眼、黃色閃光；4 秒後回 `idle` |
| 9 | `cheer` | s7 | ^^ 眼、舉手、星星；`MiPet.cheer()`，約 2.4 秒後回 `idle` |

`thinking` / `talking` 30 秒內沒有新的 `setState` 或 `pulse` 會自動回 `idle`。`hover` 是內部狀態：只能由小版的 `mouseenter`/`focus` 進入、`mouseleave`/`blur` 離開，`MiPet.setState('hover')` 會被忽略（外部設定沒有回程）；聊天視窗開關（`html.mipet-chat-open` 變化或 `MiPet.setChatOpen`）、視窗失焦、分頁切走時一律強制離開 `hover`，因為小版被隱藏後不一定收得到 `mouseleave`。聊天 header 的狀態文字（`aria-live`）初始值直接寫在 markup，不在載入時朗讀，之後狀態改變才更新。`prefers-reduced-motion: reduce` 時（即時監聽）停止計時器、每個狀態只畫上表第一張影格、不跳動。

| CSS variable | 預設 | 用途 |
|---|---|---|
| `--mipet-bottom` | `4rem + 1.5rem + safe-area`（墊在 bottom nav 上方）；頁面沒有 `#bottom-nav` 時 JS 在 `<html>` 加 `.mipet-no-nav`，改為 `1.5rem + safe-area` | 浮動小版離底部距離；不依賴 `:has()`。交易詳情頁由 action bar 的 `ResizeObserver` 以 inline style 改寫 |
| `--mipet-focus` | `#14B8A6`（= `primary`） | 浮動小版鍵盤焦點框 |
| `--mipet-scale` | `1` | 顯示倍率（整數），精靈尺寸 = 48 px × 倍率 |
| `--mipet-muted` | `#64748B` / dark `#94A3B8` | 地面陰影、狀態文字 |
| `--mipet-fg` | `#0F172A` / dark `#E2E8F0` | 名稱文字（聊天 header 固定白底，走淺色值） |

**重新產生精靈圖**：原始參考圖（業主核可）放在 `docs/assets/medou/s0.png … s7.png`，執行 `uv run python scripts/medou/build_sprites.py`（加 `--preview` 另存 10× 預覽到 `/tmp`）。腳本會自動偵測放大倍率、取每格中心色並量化到 10 色色盤、從邊緣 flood fill 去掉白底／淺灰暈邊／地影、補出眨眼與閉嘴兩張衍生影格，最後底部對齊輸出精靈圖。影格順序寫在腳本的 `FRAME_ORDER`，與 `pixel-pet.js` 的 `FRAME` 對照表必須一致；來源檔清單由 `FRAME_ORDER` 推出。輸出單格必須是 `FRAME_PX`＝48 px（= `--mipet-frame-px`），尺寸改變時腳本會直接失敗，避免精靈圖與 CSS 切格錯位。

## 4. 登入入口與錯誤頁

### 登入 / 註冊入口

來源：[`templates/account/base_entrance.html`](./templates/account/base_entrance.html)

| CSS variable / 色碼 | 用途 |
|---|---|
| `--accent: #14B8A6` | 入口頁主要 accent |
| `--accent-hover: #0D9488` | hover |
| `--border: #E5E7EB` | 表單邊框 |
| `--text-secondary: #6B7280` | 次要文字 |
| `--input-bg: #F9FAFB` | input 背景 |
| `rgba(20, 184, 166, 0.08)` → `rgba(20, 184, 166, 0.02)` | 頁面背景漸層 |
| `rgba(0, 0, 0, 0.1)`、`rgba(20, 184, 166, 0.15)`、`rgba(20, 184, 166, 0.3)` | 卡片與 icon box shadows |

### 404

來源：[`core/templates/404.html`](./core/templates/404.html)

`#F6F7F8` 背景、`#334155` 主要文字、`#64748B` ASCII 貓與次要文字、`#14B8A6` 錯誤碼、`#0D9488` 連結、`#0F766E` hover、`#94A3B8` 分隔符。

### 500

來源：[`core/templates/500.html`](./core/templates/500.html)

`#1E293B` 背景、`#E2E8F0` 主要文字、`#F87171` 錯誤碼、`#94A3B8` 說明文字、`#38BDF8` 連結、`#475569` 細節文字。

## 5. 透明色與效果完整清單

以下是 repo 前端與文件樣式中找到的 `rgba()` / `rgb()` literal 去重清單：

```text
rgb(59, 130, 246)
rgba(0, 0, 0, 0.02)       rgba(0, 0, 0, 0.04)
rgba(0, 0, 0, 0.05)       rgba(0, 0, 0, 0.08)
rgba(0, 0, 0, 0.1)        rgba(0, 0, 0, 0.12)
rgba(6, 182, 212, 0.08)   rgba(6, 182, 212, 0.2)
rgba(13, 148, 136, 0.05)
rgba(16, 185, 129, 0.3)
rgba(19, 109, 236, 0.02)  rgba(19, 109, 236, 0.08)
rgba(19, 109, 236, 0.15)  rgba(19, 109, 236, 0.4)
rgba(19, 109, 236, 0.5)
rgba(20, 184, 166, 0.02) rgba(20, 184, 166, 0.05)
rgba(20, 184, 166, 0.08) rgba(20, 184, 166, 0.15)
rgba(20, 184, 166, 0.2)  rgba(20, 184, 166, 0.25)
rgba(20, 184, 166, 0.3)
rgba(34, 197, 94, 0.15)  rgba(59, 130, 246, 0.05)
rgba(59, 130, 246, 0.1)   rgba(59, 130, 246, 0.15)
rgba(139, 92, 246, 0.2)   rgba(148, 163, 184, 0.2)
rgba(148, 163, 184, 0.28) rgba(203, 213, 225, 0.9)
rgba(239, 68, 68, 0.15)   rgba(245, 158, 11, 0.1)
rgba(245, 158, 11, 0.15)  rgba(245, 158, 11, 0.2)
rgba(245, 158, 11, 0.3)   rgba(255, 255, 255, 0.1)
rgba(255, 255, 255, 0.2)  rgba(255, 255, 255, 0.65)
rgba(255, 255, 255, 0.7)  rgba(255, 255, 255, 0.85)
```

透明漸層/玻璃效果目前集中在書籍 UI、交易卡片與登入入口；它們不是新的實色 token。

## 5.1 Explicit hex literal 完整索引

這份索引保留 repo 掃描到的所有完整 hex literal；已在前文有語意說明的顏色仍在此列出，方便 grep 與移除重複值。大小寫差異視為同一色。

```text
#000000  #059669  #06B6D4  #0D5BB8  #0D9488  #0F172A  #0F766E
#101822  #10B981  #134E4A  #136DEC  #14B8A6  #15803D  #1D4ED8
#1E293B  #1F2937  #22C55E  #22D3EE  #334155  #34A853  #38BDF8
#3B82F6  #4285F4  #475569  #4B5563  #64748B  #6B7280  #6D6464
#8B5CF6  #9333EA  #94A3B8  #B45309  #B91C1C  #BFDBFE  #CBD5E1
#D1D5DB  #DBEAFE  #DC2626  #DCFCE7  #E2E8F0  #E5E7EB  #EA4335
#EA580C  #EF4444  #EFF6FF  #F0FDFA  #F1F5F9  #F2F2F7  #F3F4F6
#F59E0B  #F6F7F8  #F87171  #F8FAFC  #F9FAFB  #FBBC05  #FECACA
#FEE2E2  #FEF3C7  #FFFFFF  #FFF
```

## 6. 文件、測試與外部品牌色（不納入產品 UI）

### k6 壓力測試報告

來源：[`docs/k6-report-614.html`](./docs/k6-report-614.html#L8-L19)

`#0F172A` 背景、`#1E293B` card、`#334155` border、`#E2E8F0` text、`#94A3B8` dim text、`#22C55E` green、`#EF4444` red、`#F59E0B` amber、`#3B82F6` blue、`#8B5CF6` purple、`#06B6D4` cyan。

### Marp 簡報

來源：[`docs/presentation-0703.md`](./docs/presentation-0703.md#L13-L18)

`#FFFFFF` background、`#1F2937` foreground、`#0F766E` heading、`#14B8A6` accent、`#D1D5DB` border，另使用 `#6B7280`、`#F9FAFB`、`#EFF6FF` 作為頁尾、淺色 surface 與資訊區塊。

### Google 標誌

登入與註冊 SVG 直接使用 Google 官方四色：`#4285F4`、`#34A853`、`#FBBC05`、`#EA4335`。出現於 [`templates/account/login.html`](./templates/account/login.html)、[`templates/account/signup.html`](./templates/account/signup.html) 與 [`templates/socialaccount/signup.html`](./templates/socialaccount/signup.html)，不應改成 Exbooks 品牌色。

### 圖表 / diagram 來源中的短 hex

`docs/usecase.md` 使用 `<color #1A6>`、`#16A`、`grey`；這是圖表語法或文件標記，不是瀏覽器產品 palette。`#8FE`、`#9C3`、`#9CF`、`#9EF`、`#AFA`、`#B83`、`#BFB`、`#C93`、`#CFE`、`#DBE`、`#DEA`、`#DEFA`、`#DFD`、`#EDF`、`#F66`、`#F94`、`#FAA`、`#FBD`、`#FCB`、`#FEE`、`#FF6`、`#FFB` 等短碼來自 diagram / 產生物或文件資料，不應當作 UI token。

## 7. 現況觀察與維護規則

1. **品牌基準已很清楚**：`#14B8A6` → `#0D9488` → `#06B6D4` 是產品的 teal/cyan 軸線。
2. **目前存在 blue drift**：書籍選擇 widget 使用 `#3B82F6`，`--primary-glow` 使用 `#136DEC`。除非這兩處需要「選取」或「外部內容」的特殊語意，新增樣式應優先改用 `primary`。
3. **neutral 不要自行重複命名**：正文優先 `text-slate-900`，次要文字使用 `text-slate-500`/`text-slate-400`，surface 使用 `white`、`slate-50`、`slate-100`。
4. **狀態顏色保持配對**：背景與文字要使用同一語意色族，例如 `blue-100 + blue-700`、`green-100 + green-700`、`amber-100 + amber-700`、`rose-100 + rose-700`。
5. **透明層只用於效果**：glass、shadow、mesh aura 可以用 `rgba`；不要把透明白直接當成新的 surface token。
6. **新增顏色前先更新本文件與 Tailwind config**：若是可重複使用的產品色，應先成為 token，而不是在模板中新增 literal。
