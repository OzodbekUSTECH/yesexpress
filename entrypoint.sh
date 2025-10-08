#!/bin/sh

# Apply database migrations
echo "Apply database migrations"
uv run manage.py migrate

# Start collect staticfiles
echo "Start collect static"
uv run manage.py collectstatic --noinput

# Start Gunicorn processes
echo "Starting Gunicorn server."
exec uv run gunicorn tuktuk.wsgi:application --bind 0.0.0.0:4546 --workers 2 --log-level info --access-logfile - --error-logfile -
