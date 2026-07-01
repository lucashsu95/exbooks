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
# Exbooks 期末報告
## 讓換書變得更簡單、更快、更安全

---

<!-- _class: lead -->
# 今天談什麼？

<div class="columns">
<div>

### 用戶體驗升級
- **極速搜尋**：查 ISBN 從 2 秒變 2 毫秒
- **AI 推薦助手**：24 小時在線的書籍顧問
- **多語言支援**：繁中、英文、韓文三語系

</div>
<div>

### 成本與架構
- **省錢的儲存方案**：用戶越多，單位成本越低
- **穩定的通知系統**：重要消息不遺漏
- **全方位安全防護**：雙層防線阻擋惡意攻擊

</div>
</div>

---

# 用戶痛點一：找書太慢

**過去的問題**
- 掃描 ISBN 查書名要等 2 秒，使用者以為當機
- 書籍列表頁載入一次要跑 42 次資料庫查詢
- 首頁熱門書籍每次都要重新計算，載入要 800 毫秒

**這代表什麼？**
每多等 1 秒，就有 7% 的使用者直接關掉頁面離開。慢 = 流失。

---

# 解決方案：三層快取策略

**核心概念：能記住答案，就不要重新算一次**

<div class="columns">
<div class="card">
<h3>第一層：本地記憶</h3>
<p>查過的書直接存在系統記憶體</p>
<p>再次查詢 → <strong>即時回應</strong></p>
</div>
<div class="card">
<h3>第二層：常用捷徑</h3>
<p>熱門書籍每小時預先算好</p>
<p>打開首頁 → <strong>直接呈現</strong></p>
</div>
<div class="card">
<h3>第三層：外部查詢</h3>
<p>真的沒見過的書才問 Google</p>
<p>問完就記住 → <strong>下次不用問</strong></p>
</div>
</div>

---

# 成果：速度提升對照

| 功能 | 改善前 | 改善後 | 使用者感受 |
|------|--------|--------|-----------|
| **ISBN 查詢** | 2 秒等待 | 2 毫秒 | 掃完條碼，書名立刻出現 |
| **書籍列表** | 3.2 秒載入 | 0.4 秒 | 滑手機不卡頓 |
| **首頁熱門書** | 每次重新算 | 直接讀取 | 打開頁面就看完 |

> **關鍵影響**：50 人同時使用時，速度差異最明顯。系統不再「人多就變慢」。

---

# 用戶痛點二：不知道看什麼書

**過去的問題**
- 平台書很多，但使用者不知道從哪本開始
- 沒有「幫我挑書」的功能，只能自己翻

**解決方案：AI 書籍顧問**

- 輸入「我想看輕鬆的書」或「推薦心理學入門」，直接給答案
- 24 小時在線，不需要等客服
- 不只推薦，還能查交易狀態、查 ISBN

> **商業價值**：降低新用戶「第一次使用就迷路」的機率，提升留存。

---

# 多語言 = 多市場

**為什麼做三語系？**

<div class="columns">
<div class="card">
<h3>繁體中文</h3>
<p>台灣主力市場</p>
<p>預設語言，完整體驗</p>
</div>
<div class="card">
<h3>English</h3>
<p>國際學生、僑民</p>
<p>100% 翻譯覆蓋</p>
</div>
<div class="card">
<h3>한국어</h3>
<p>韓國交換生族群</p>
<p>完整架構已建立</p>
</div>
</div>

> **成果**：3,175 條翻譯字串，使用者可在網站右上角一鍵切換語言。

---

# 用戶痛點三：檔案儲存太貴

**問題**：書籍照片、使用者頭像需要儲存空間。用戶越多，照片越多，開銷越大。

**四種方案的比喻**

<div class="columns">
<div class="card">
<h3>本地硬碟</h3>
<p>像把書放在自己房間</p>
<p>免費，但只有一台電腦能讀</p>
</div>
<div class="card">
<h3>自架儲存 (MinIO)</h3>
<p>像家裡買一個書櫃</p>
<p>一次買斷，開再多門都不加錢</p>
</div>
<div class="card">
<h3>雲端儲存 (R2/S3)</h3>
<p>像圖書館租 locker</p>
<p>每次開門都要收手續費</p>
</div>
</div>

---

# 成本比較：為什麼選「書櫃」方案

| 使用情境 | 本地硬碟 | 自架書櫃 | 雲端 locker |
|---------|---------|---------|------------|
| **現在**（1 萬次存取/月） | 無法擴展 | **約 $5/月** | $45-49/月 |
| **成長後**（10 萬次/月） | 無法擴展 | **約 $5/月** | $451-492/月 |

**關鍵差異**：
- **自架方案**：固定成本，用戶越多「每次存取成本」越低
- **雲端方案**：按次收費，用戶越活躍，帳單越貴

> **結果**：選擇自架儲存，用戶成長 10 倍，成本不變。

---

# 痛點四：重要通知收不到

**問題**：交易被接受、書要到期了、註冊要驗證 —— 這些消息沒送到，用戶體驗就崩了。

**我們的做法**

<div class="columns">
<div class="card">
<h3>立即寫入紀錄</h3>
<p>先存一份到通知中心</p>
<p>用戶隨時可查歷史</p>
</div>
<div class="card">
<h3>背景發送 Email</h3>
<p>不佔用主要頁面載入時間</p>
<p>失敗自動重試 3 次</p>
</div>
<div class="card">
<h3>開發時隔離測試</h3>
<p>測試信不會寄到真實信箱</p>
<p>本地就能驗證格式內容</p>
</div>
</div>

---

# 痛點五：系統被惡意攻擊怎麼辦？

**雙層防線，暴力破解無效**

<div class="columns">
<div class="card">
<h3>第一道閘門：入口管制</h3>
<p>短時間內瘋狂嘗試登入 → 直接擋下</p>
<p>如同 ATM 連續輸錯密碼就鎖卡</p>
</div>
<div class="card">
<h3>第二道閘門：帳號保護</h3>
<p>單一 IP 多次失敗 → 暫時鎖定</p>
<p>帳號層級額外計次，雙重保險</p>
</div>
</div>

> **效果**：即使對方用大量機器嘗試破解，也無法撞開任何一道門。

---

# 系統穩定性：持續驗證

**怎麼知道系統沒有壞？**

- **自動化測試**：390+ 個測試案例，每次改程式都自動跑一遍
- **壓力測試**：模擬 50 人同時使用，確認「人多不會當機」
- **四種情境驗證**：
  - 剛部署完 → 30 秒快速確認基本功能正常
  - 每週例行 → 模擬日常流量，確認基線穩定
  - 重大改版後 → 逐步加壓，找出瓶頸在哪
  - 活動前 → 模擬瞬間高峰，確保搶購潮撐得住

---

# 觀測性：系統的「健康檢查報告」

**核心問題：用戶說「頁面打不開」，工程師要知道是哪裡壞了**

**我們的解決方案**

<div class="columns">
<div class="card">
<h3>每筆交易有編號</h3>
<p>從進入網站到完成動作</p>
<p>全程可追溯，不會斷鏈</p>
</div>
<div class="card">
<h3>日誌自動分類</h3>
<p>工程師看錯誤、稽核員看紀錄、PM 看行為</p>
<p>各取所需，不用在垃圾堆裡翻找</p>
</div>
<div class="card">
<h3>視覺化儀表板</h3>
<p>測試跑完自動產出報告</p>
<p>一眼看出「哪裡正常、哪裡異常」</p>
</div>
</div>

---

# 總結：這個學期的三大成果

<div class="columns">
<div class="card">
<h3>用戶體驗提升</h3>
<p>查書速度提升 <strong>99%</strong></p>
<p>AI 助手降低使用門檻</p>
<p>多語言打開國際市場</p>
</div>
<div class="card">
<h3>成本結構優化</h3>
<p>儲存成本固定，不因用戶成長而暴漲</p>
<p>架構支援多台伺服器擴展</p>
</div>
<div class="card">
<h3>系統可靠安全</h3>
<p>通知到達率近 100%</p>
<p>雙層防線阻擋惡意攻擊</p>
<p>自動化測試確保品質</p>
</div>
</div>

---

<!-- _class: lead -->
# 下一步

## 擴大用戶規模，驗證商業模式

- **短期**：優化 onboarding 流程，提升首次交易轉換率
- **中期**：引入信任評分機制，降低交易糾紛
- **長期**：企業 B2B 書籍共享、校園圖書館整合

---

<!-- _class: lead -->
# 感謝聆聽

## 歡迎提問
