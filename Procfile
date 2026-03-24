web: python manage.py collectstatic --noinput && python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 4 --timeout 120
worker: celery -A config worker --loglevel=info
beat: celery -A config beat --loglevel=info
