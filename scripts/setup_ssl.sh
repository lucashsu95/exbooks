#!/bin/bash
# Exbooks SSL 憑證設定腳本
# 使用 certbot standalone mode 為指定網域取得 Let's Encrypt 憑證
set -euo pipefail

DOMAIN="${1:-}"
if [ -z "$DOMAIN" ]; then
    echo "用法: $0 <your-domain.example.com>"
    echo ""
    echo "步驟："
    echo "  1. 先將 DNS A 記錄指向本機 IP"
    echo "  2. 執行本腳本取得憑證"
    echo "  3. 複製 nginx/ssl.conf.example → nginx/default.conf"
    echo "  4. 修改 server_name 為你的網域"
    echo "  5. docker compose restart nginx"
    exit 1
fi

echo "========================================"
echo "  Exbooks SSL Setup — $DOMAIN"
echo "========================================"

# 檢查 docker 是否正在執行
if ! docker info >/dev/null 2>&1; then
    echo "Error: Docker is not running."
    exit 1
fi

# 先用 certbot standalone 模式取得憑證
# 需要暫時停止 nginx 釋放 port 80
echo ""
echo "[1/3] Stopping nginx to free port 80..."
docker compose stop nginx || true

echo ""
echo "[2/3] Obtaining certificate from Let's Encrypt..."
docker run --rm -it \
    -v "$(pwd)/certbot_data:/etc/letsencrypt" \
    -v "$(pwd)/certbot_data:/var/www/certbot" \
    -p 80:80 \
    certbot/certbot certonly --standalone \
    --non-interactive \
    --agree-tos \
    --email admin@"$DOMAIN" \
    --domains "$DOMAIN"

echo ""
echo "[3/3] Restarting nginx..."
docker compose start nginx

echo ""
echo "Certificate obtained successfully!"
echo ""
echo "下一步："
echo "  1. cp nginx/ssl.conf.example nginx/default.conf"
echo "  2. 編輯 nginx/default.conf，將 your-domain.example.com 改為 $DOMAIN"
echo "  3. docker compose restart nginx"
echo ""
echo "自動續約（certbot renew）："
echo "  docker run --rm -v \"\$(pwd)/certbot_data:/etc/letsencrypt\" certbot/certbot renew"
echo ""
echo "建議加到 crontab 每兩個月執行一次："
echo "  0 0 1 */2 * docker run --rm -v \$PWD/certbot_data:/etc/letsencrypt certbot/certbot renew && docker compose restart nginx"
