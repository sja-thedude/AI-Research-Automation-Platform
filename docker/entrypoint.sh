#!/usr/bin/env bash
# Wait for Postgres + Redis, apply migrations, collect static, then exec the CMD.
set -euo pipefail

echo "⏳ Waiting for PostgreSQL at ${POSTGRES_HOST:-db}:${POSTGRES_PORT:-5432}..."
until python -c "import socket,os,sys; s=socket.socket(); s.settimeout(2); \
  s.connect((os.getenv('POSTGRES_HOST','db'), int(os.getenv('POSTGRES_PORT','5432')))) \
  " 2>/dev/null; do
  sleep 1
done
echo "✅ PostgreSQL is up."

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  echo "📦 Applying migrations..."
  python manage.py migrate --noinput
fi

if [ "${COLLECT_STATIC:-false}" = "true" ]; then
  python manage.py collectstatic --noinput
fi

exec "$@"
