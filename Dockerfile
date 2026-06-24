# ---- Build Stage ----
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc pkg-config libmariadb-dev libjpeg-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY pyproject.toml .

# 安裝正式 + 生產 + 測試依賴到 /install，方便後續 COPY
RUN pip install --no-cache-dir --prefix=/install . ".[prod,test]"  # 包含 factory-boy、faker 等測試工具

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

# 複製已編譯的 Python 套件
COPY --from=builder /install /usr/local

WORKDIR /app
COPY . .

# collectstatic 在 entrypoint 執行（需要環境變數）
RUN mkdir -p /app/staticfiles /app/media /var/log/exbook \
    && chown -R django:django /app /var/log/exbook

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

USER django
EXPOSE 8000

ENTRYPOINT ["/docker-entrypoint.sh"]
