# ---- Build Stage ----
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc pkg-config libmariadb-dev libjpeg-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY pyproject.toml .

# 安裝正式 + 生產依賴到 /install，方便後續 COPY
RUN pip install --no-cache-dir --prefix=/install . ".[prod]"

# ---- Runtime Stage ----
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libmariadb3 libjpeg62-turbo zlib1g \
    && rm -rf /var/lib/apt/lists/* \
    && addgroup --system django && adduser --system --ingroup django django

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
