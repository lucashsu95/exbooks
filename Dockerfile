# ---- Build Stage ----
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc pkg-config libmariadb-dev libjpeg-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# uv 負責依 lockfile 安裝（本專案用 uv 管理依賴）
RUN pip install --no-cache-dir uv

WORKDIR /build
# path 依賴 ai-client 需要 sdk/ 存在
COPY pyproject.toml uv.lock ./
COPY sdk/ ./sdk/

# 建立 venv 並依 lockfile 安裝正式 + 生產 + 測試依賴
# --no-dev 跳過 dev group；test group 含 factory-boy、faker 等測試工具
# exbook 本體在 runtime 階段由 /app 直接執行
RUN uv venv /install --python 3.12 && \
    uv sync --frozen --no-install-project --no-dev \
        --python /install/bin/python --extra prod --group test

# ---- Runtime Stage ----
FROM python:3.12-slim

# 安裝系統依賴、Node.js 以及 Playwright 瀏覽器環境
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmariadb3 libjpeg62-turbo zlib1g curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g playwright \
    && npx playwright install-deps chromium \
    && PLAYWRIGHT_BROWSERS_PATH=/ms-playwright npx playwright install chromium \
    && rm -rf /var/lib/apt/lists/* \
    && addgroup --system django && adduser --system --ingroup django django \
    && chown -R django:django /ms-playwright

# 設定 Playwright 瀏覽器路徑環境變數
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# 複製 build stage 建立的 venv（含所有已編譯的 Python 依賴）
COPY --from=builder /install /install
# 讓 venv 內的 python / gunicorn / celery 優先被找到
ENV PATH="/install/bin:$PATH" \
    VIRTUAL_ENV=/install

WORKDIR /app
COPY . .

# collectstatic 在 entrypoint 執行（需要環境變數）
RUN mkdir -p /app/staticfiles /app/media /var/log/exbook \
    && chown -R django:django /app /install /var/log/exbook

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

USER django
EXPOSE 8000

ENTRYPOINT ["/docker-entrypoint.sh"]
