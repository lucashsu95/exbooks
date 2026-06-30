#!/bin/bash
set -e

echo "Waiting for database..."
python << 'EOF'
import time, os, socket
host = os.environ.get("DB_HOST", "db")
port = int(os.environ.get("DB_PORT", 3306))
for i in range(30):
    try:
        sock = socket.create_connection((host, port), timeout=2)
        sock.close()
        print(f"Database at {host}:{port} is ready.")
        break
    except OSError:
        print(f"Waiting for {host}:{port}... ({i+1}/30)")
        time.sleep(2)
else:
    print("Database not available after 60s, starting anyway...")
EOF

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting Gunicorn..."
exec gunicorn exbook.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-3}" \
    --worker-class gevent \
    --worker-connections 1000 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
