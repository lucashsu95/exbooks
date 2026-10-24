# docs/ 文件索引

> Exbooks 專案文件總覽。依主題分類，含描述與格式。

## 簡報（依課程進度排序）

| 文件 | 說明 |
|---|---|
| [0325_exbook_presentation.pdf](0325_exbook_presentation.pdf) | 03/25 選題報告 |
| [0325_exbook_architecture.pdf](0325_exbook_architecture.pdf) | 03/25 選題報告 — 系統架構 |
| [0325_exbook_design_philosophy.pdf](0325_exbook_design_philosophy.pdf) | 03/25 選題報告 — 設計哲學 |
| [tech-showcase-presentation.pdf](tech-showcase-presentation.pdf) | 04/14 期中報告簡報 |
| [presentation-0625.pdf](presentation-0625.pdf) | 06/25 前導簡報 |
| [presentation-0701.md](presentation-0701.md) · [presentation-0701.pdf](presentation-0701.pdf) | 07/01 期末報告簡報（Marp 原始碼 + 轉出 PDF），使用 [登入保護.png](登入保護.png)、[媒體檔案雙軌存取架構.png](媒體檔案雙軌存取架構.png) |
| [presentation-0703.md](presentation-0703.md) · [presentation-0703.pdf](presentation-0703.pdf) | 07/03 期末報告修訂版（採納老師建議後修改，Marp 原始碼 + 轉出 PDF） |

## 系統分析與需求

| 文件 | 說明 | 格式 |
|---|---|---|
| [acquire.md](acquire.md) | 共享書籍 — 需求擷取（stakeholder 訪談、功能/非功能需求） | Markdown |
| [schema.md](schema.md) | 系統分析：資料模型、API 設計 | Markdown |
| [seed.md](seed.md) | 資料填充指令（seed command）說明 | Markdown |

## 圖表（UML / ER）

| 文件 | 說明 | 格式 |
|---|---|---|
| [usecase.md](usecase.md) · [usecase.png](usecase.png) | Use Case Diagram 用例圖（PlantUML 原始碼 + 渲染圖） | PlantUML / PNG |
| [class-diagram.md](class-diagram.md) | Class Diagram 類別圖 | PlantUML |
| [er-diagram.md](er-diagram.md) · [er-diagram.svg](er-diagram.svg) | ER Diagram 實體關係圖（原始碼 + 渲染圖） | PlantUML / SVG |
| [web-push-architecture.md](web-push-architecture.md) | Web Push 架構圖 | PlantUML |

## 可觀測性（Observability）

| 文件 | 說明 |
|---|---|
| [observability/design.md](observability/design.md) | 進階可觀測性系統實作方案 |
| [observability/report.md](observability/report.md) | 進階可觀測性實作技術證明報告 |
| [k6-report-614.html](k6-report-614.html) | k6 效能測試報告（HTML） |

## 測試與維運

| 文件 | 說明 |
|---|---|
| [testing_strategy.md](testing_strategy.md) | Views 測試策略（目標覆蓋率 27–47% → 70%+） |
| [BACKUP.md](BACKUP.md) | 資料備份（MariaDB／媒體／Redis） |

## 決策記錄（ADR）

| 文件 | 說明 |
|---|---|
| [adr/django-fsm-migration.md](adr/django-fsm-migration.md) | ADR: 採用 django-fsm 重構 Deal 狀態機 |


