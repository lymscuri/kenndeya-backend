release: python manage.py migrate --settings=config.settings.production && python manage.py collectstatic --noinput --settings=config.settings.production
web: gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 4 --timeout 120
worker: celery -A config worker --loglevel=info
beat: celery -A config beat --loglevel=info
