sh -c "python backend/manage.py migrate &&
             python backend/manage.py collectstatic --noinput &&
             gunicorn backend.config.wsgi:application --bind 0.0.0.0:8000"