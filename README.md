# Exbooks 共享書籍

> 一套公益性質的共享書籍平臺，鼓勵社群成員分享自有藏書，讓書籍自由流通，促進知識共享。

## 計劃主旨

透過社群成員自主分享書籍，建立一個去中心化的共享圖書平臺，讓書籍能夠自由流通，並促進社群成員之間的交流與知識共享。

近幾年共享經濟（Sharing Economy）火紅，已廣泛應用在環保、公益、商業等領域。本平臺以公益為出發點，鼓勵民眾加入社群，拿出自有藏書與他人交換閱讀。

## 核心概念

- **去中心化管理** — 書籍由用戶自行保管，無實體圖書館
- **雙軌流通模式** — 書籍可定義為「開放傳遞」或「閱畢即還」
- **面交取書** — 所有書籍交付一律採面交方式
- **信用評價** — 交易後雙方互評，建立社群信任機制
- **套書綁定** — 套書可綁定借出，避免分散難以追回

## 角色說明

| 角色 | 說明 |
|------|------|
| **會員 (Member)** | 透過 Google Account 註冊，可上架書籍、申請借閱、評價交易對象 |
| **貢獻者 (Owner)** | 分享自有書籍並上架至平臺供他人借閱 |
| **持有者 (Keeper)** | 目前持有該書籍的用戶（不一定是貢獻者） |
| **讀者 (Reader)** | 申請借閱書籍的用戶 |
| **管理員 (SysAdmin)** | 維護平臺運作、審核異常交易 |

> Owner、Keeper、Reader 為情境角色，同一用戶可同時擁有不同角色身份。

## 技術架構

| 層級 | 技術 |
|------|------|
| 後端框架 | Django + Django REST Framework |
| 資料庫 | MariaDB |
| 身份驗證 | Django Auth / OAuth 2.0 (Google) / JWT |

## 本地啟動

### 環境需求

- Python 3.12+
- MariaDB 10.6+（或 MySQL 8.0+）
- pip（隨 Python 內建）

### 1. 建立虛擬環境

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 2. 安裝依賴

```bash
# 正式依賴
pip install -e .

# 開發 + 測試依賴
pip install -e ".[dev,test]"
```

### 3. 環境變數

複製範本並填入資料庫密碼：

```bash
cp .env.example .env
```

編輯 `.env`：

```
DB_PASSWORD=你的MariaDB密碼
```

### 4. 建立資料庫

登入 MariaDB 建立資料庫：

```sql
CREATE DATABASE exbook CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 5. 執行遷移 & 建立管理員

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 6. 啟動開發伺服器

```bash
python manage.py runserver
```

開啟瀏覽器：
- 首頁：http://127.0.0.1:8000/
- 後台：http://127.0.0.1:8000/admin/

### 7. 執行測試

測試使用 SQLite in-memory，不需要 MariaDB：

```bash
pytest
```

## Docker 部署

### 環境需求

- Docker Engine 24+
- Docker Compose V2+

### 1. 設定環境變數

```bash
cp .env.example .env
```

編輯 `.env`，至少填入以下必要項目：

```
DB_PASSWORD=你的資料庫密碼
SECRET_KEY=一段隨機長字串
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost,http://127.0.0.1
```

### 2. 啟動所有服務

```bash
docker compose up -d --build
```

這會啟動三個容器：

| 容器 | 用途 | 對外 Port |
|------|------|-----------|
| `db` | MariaDB 10.11 | — (內部 3306) |
| `web` | Django + Gunicorn | — (內部 8000) |
| `nginx` | 反向代理 + 靜態檔案 | **80** |

首次啟動時 `web` 容器會自動執行 `migrate` 和 `collectstatic`。

### 3. 建立管理員帳號

```bash
docker compose exec web python manage.py createsuperuser
```

### 4. 存取

- 首頁：http://localhost/
- 後台：http://localhost/admin/

### 5. 常用指令

```bash
# 查看日誌
docker compose logs -f web

# 停止所有服務
docker compose down

# 停止並清除資料（含資料庫）
docker compose down -v
```

### 架構圖

```
┌──────────┐      ┌──────────────┐      ┌──────────┐
│  Nginx   │─:80──▶│    Django     │─:3306▶│ MariaDB  │
│ (alpine) │      │ (Gunicorn)   │      │ (10.11)  │
└────┬─────┘      └──────────────┘      └──────────┘
     │                    │
  static/              media/
  (volume)            (volume)
```

## CI/CD（Self-hosted Runner）

本專案使用 GitHub Actions + Self-hosted Runner，CI/CD pipeline 全部在你自己的 VM 上執行。

### 流程圖

```
開發者 git push
    │
    ▼
GitHub 觸發 webhook
    │
    ▼
VM 上的 Self-hosted Runner 接收任務
    │
    ├─ [1] lint    — ruff check .
    ├─ [2] test    — pytest
    └─ [3] deploy  — docker compose build + up
    │
    ▼
服務上線（Nginx :80）
```

### VM 環境準備

> 以 Ubuntu 22.04/24.04 為例，VM 最低規格：2 vCPU / 2 GB RAM / 25 GB Disk。

#### 1. 安裝 Docker

```bash
# 安裝 Docker Engine
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER

# 重新登入讓 docker 群組生效
exit
# 重新 SSH 進來

# 驗證
docker --version
docker compose version
```

#### 2. 安裝 GitHub Actions Runner

到你的 GitHub repo → Settings → Actions → Runners → **New self-hosted runner**，GitHub 會給你一組指令，大致如下：

```bash
# 建立 runner 目錄
mkdir ~/actions-runner && cd ~/actions-runner

# 下載（版本號依 GitHub 頁面提供的為準）
curl -o actions-runner-linux-x64.tar.gz -L \
  https://github.com/actions/runner/releases/download/v2.xxx.x/actions-runner-linux-x64.tar.gz
tar xzf actions-runner-linux-x64.tar.gz

# 設定（token 從 GitHub 頁面取得）
./config.sh --url https://github.com/你的帳號/exbook --token YOUR_TOKEN

# 安裝為 systemd 服務（開機自動啟動）
sudo ./svc.sh install
sudo ./svc.sh start
sudo ./svc.sh status
```

#### 3. 部署專案

```bash
# 把 repo clone 到 VM
cd ~
git clone https://github.com/你的帳號/exbook.git
cd exbook

# 設定環境變數
cp .env.example .env
nano .env  # 填入 DB_PASSWORD, SECRET_KEY, ALLOWED_HOSTS 等

# 首次啟動
docker compose up -d --build
```

### Pipeline 說明

Pipeline 定義在 `.github/workflows/ci.yml`，分三個階段：

| 階段 | 觸發條件 | 執行內容 |
|------|----------|----------|
| **lint** | push / PR 到 main | `ruff check .` 程式碼風格檢查 |
| **test** | lint 通過後 | `pytest` 執行全部測試 |
| **deploy** | test 通過 + push 到 main | `scripts/deploy.sh` 重建並啟動容器 |

> PR 只會跑 lint + test，不會觸發 deploy。只有 merge 到 main 才會部署。

### GitHub Secrets 設定

如果需要在 CI 中使用敏感資訊（目前的 pipeline 不需要，因為 runner 在本機），到 repo → Settings → Secrets and variables → Actions 新增。

## 文件索引

| 文件 | 說明 |
|------|------|
| [`docs/acquire.md`](docs/acquire.md) | 需求擷取 — 業務規則、流程、專有名詞定義 |
| [`docs/usecase.md`](docs/usecase.md) | 用例圖 — PlantUML Use Case Diagram |
| [`docs/schema.md`](docs/schema.md) | 系統分析 — Database Schema、ER Diagram、Django Models |
| [`docs/class-diagram.md`](docs/class-diagram.md) | 類別圖 — Mermaid Class Diagram |
| [`docs/er-diagram.md`](docs/er-diagram.md) | ER 圖 — 實體關係圖（分段） |
| [`docs/testing_strategy.md`](docs/testing_strategy.md) | Views 測試策略 |
| [`docs/seed.md`](docs/seed.md) | 資料填充指令說明 |
| [`docs/BACKUP.md`](docs/BACKUP.md) | 資料備份操作機制 |
| [`docs/progress.md`](docs/progress.md) | Session 進度追蹤 |
| [`docs/adr/`](docs/adr/) | 架構決策記錄（ADR） |
| [`docs/web-push-architecture.tex`](docs/web-push-architecture.tex) | Web Push 架構圖（LaTeX TikZ） |
