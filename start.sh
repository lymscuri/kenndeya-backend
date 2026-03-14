#!/bin/bash
# Script de démarrage pour Railway

set -e

echo "=== Starting Kendeya Backend ==="
echo "Running migrations..."
python manage.py migrate --noinput || {
    echo "Migration failed!"
    exit 1
}

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear || {
    echo "Warning: collectstatic failed, continuing..."
}

echo "Starting Gunicorn..."
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
