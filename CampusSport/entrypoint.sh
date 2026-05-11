#!/bin/bash
set -e

echo "Waiting for MySQL..."
while ! python -c "import pymysql; pymysql.connect(host='${DB_HOST}', user='${DB_USER}', password='${DB_PASSWORD}', db='${DB_NAME}', port=int('${DB_PORT:-3306}'), charset='utf8mb4')" 2>/dev/null; do
    echo "MySQL not ready, retrying in 3s..."
    sleep 3
done
echo "MySQL is ready."

python manage.py migrate --noinput

python manage.py collectstatic --noinput --clear

exec "$@"
