#!/bin/bash
# Script de démarrage pour Railway

set -e

echo "=== Starting Kendeya Backend ==="

# Créer les répertoires nécessaires
mkdir -p /app/staticfiles
mkdir -p /app/media

echo "Running migrations..."
python manage.py migrate --noinput || {
    echo "ERROR: Migration failed!"
    exit 1
}

echo "Collecting static files..."
python manage.py collectstatic --noinput || {
    echo "ERROR: collectstatic failed!"
    exit 1
}

echo "Static files collected successfully in /app/staticfiles/"
ls -la /app/staticfiles/ | head -10

echo "Starting Gunicorn..."
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    --capture-output
