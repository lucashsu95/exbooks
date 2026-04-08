---
marp: true
theme: default
class: lead
backgroundColor: #111827
color: #e5e7eb
style: |
  section {
    font-family: 'Inter', sans-serif;
    padding: 40px;
    background-color: #111827;
  }
  h1, h2 {
    color: #3b82f6;
  }
  h3 {
    color: #60a5fa;
    border-bottom: 1px solid #1e293b;
    padding-bottom: 5px;
  }
  ul li {
    font-size: 26px;
    line-height: 1.5;
    margin-bottom: 10px;
  }
  .columns {
    display: flex;
    gap: 24px;
    margin-top: 10px;
    align-items: start;
  }
  .card {
    flex: 1;
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 14px 16px;
    background-color: #1f2937;
  }
  .badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 9999px;
    font-size: 14px;
    font-weight: 600;
    margin-bottom: 10px;
  }
  .badge-feat { background-color: #064e3b; color: #6ee7b7; }
  .badge-refactor { background-color: #1e3a8a; color: #93c5fd; }
  .badge-style { background-color: #4c1d95; color: #ddd6fe; }
  .badge-fix { background-color: #7f1d1d; color: #fca5a5; }
---

# Exbooks 共享書籍
## 每週開發進度報告 (2026.04.01 - 2026.04.08)

報告人：Sisyphus (Antigravity Agent)
專案狀態：Phase 3 預備階段

---

# 概覽與重點進展

本週重點在於 **前端 UI/UX 深度優化**、**系統架構重構 (FSM)** 以及 **核心功能補強**。

<div class="columns">
  <div class="card">
    <h3>前端演進</h3>
    <ul>
      <li>Web Interface Guidelines 合規</li>
      <li>View Transitions 平滑過渡</li>
      <li>手機版手勢與觸控優化</li>
    </ul>
  </div>
  <div class="card">
    <h3>系統穩定</h3>
    <ul>
      <li>django-fsm 狀態機遷移</li>
      <li>Service 層拆分重構</li>
      <li>測試覆蓋率提升至 82%</li>
    </ul>
  </div>
</div>

---

# 前端 UI/UX 優化 (Mobile First)

致力於提升 PWA 體驗，確保在不同設備上的流暢感。

<div class="columns">
  <div class="card">
    <span class="badge badge-feat">Feature</span>
    <ul>
      <li>底部導覽列平滑切換動畫</li>
      <li> View Transition API 標題過渡</li>
      <li>改善圖片閃現與字型載入</li>
    </ul>
  </div>
  <div class="card">
    <span class="badge badge-style">Style</span>
    <ul>
      <li>統一交易頁面色調與組件</li>
      <li>優化搜尋與選單佈局設計</li>
      <li>無障礙 (A11y) 支援全面改善</li>
    </ul>
  </div>
</div>

---

# 系統重構與技術債清理

本週進行了大規模的程式碼清理，減少了對舊有資料結構的依賴。

<div class="columns">
  <div class="card">
    <span class="badge badge-refactor">Refactor</span>
    <ul>
      <li><b>狀態機遷移</b>: Deal, SharedBook, LoanExtension 導入 django-fsm</li>
      <li><b>清理過時程式碼</b>: 移除大量 <code>hasattr</code> 向後相容邏輯</li>
      <li><b>信任等級計算</b>: 將 <code>trust_level</code> 移至計算屬性</li>
    </ul>
  </div>
  <div class="card">
    <span class="badge badge-feat">DevOps</span>
    <ul>
      <li>靜態資源處理優化 (.gitignore)</li>
      <li>測試基礎設施補強</li>
      <li>Ruff 與 djlint 全面格式化</li>
    </ul>
  </div>
</div>

---

# 新功能與業務邏輯補強

補齊了 P0/P1 等級的核心需求與自動化機制。

- <span class="badge badge-feat">Feat</span> **TrustScore 積分系統**: 整合 APScheduler 自動計算
- <span class="badge badge-feat">Feat</span> **CSV 匯出功能**: 支援多格式資料匯出
- <span class="badge badge-feat">Feat</span> **自動化邏輯**: 通知自動標記已讀、交易自動完成
- <span class="badge badge-feat">Feat</span> **安全驗證**: 書籍上傳照片必填與權限檢查

---

# 品質控管與 Bug Fixes

在開發過程中持續監控與修補邊緣案例。

<div class="columns">
  <div class="card">
    <span class="badge badge-fix">Fix</span>
    <ul>
      <li>ISBN 查詢與封面顯示邏輯</li>
      <li>修復交易評價頁面的導引路徑</li>
      <li>解決 URL 參數重複堆疊問題</li>
      <li>修復信任服務的除零錯誤</li>
    </ul>
  </div>
  <div class="card">
    <span class="badge badge-fix">Test</span>
    <ul>
      <li>E2E 測試選擇器穩定性優化</li>
      <li>單元測試案例修復 (trust_service)</li>
      <li><b>覆蓋率里程碑</b>: 82%</li>
    </ul>
  </div>
</div>

---

# 下步計畫 (Next Week)

持續往 Phase 3 目標邁進，並優化系統營運。

- [ ] **DRF REST API**: 開始實作 Serializers 與 ViewSets
- [ ] **Email 通知發送**: 整合第三方服務發送核心場景 Email
- [ ] **效能監控**: 對資料庫索引補強後的生產環境監控
- [ ] **文件同步**: 更新 Schema 與用例圖以反映 FSM 變動

---

<!-- _class: lead -->

# 感謝觀看！
## Exbooks - 讓每一本書都能再次啟航

報告時間：2026-04-08
Sisyphus Orchestrator
