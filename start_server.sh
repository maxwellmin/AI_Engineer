#!/bin/bash
# Start Django development server
cd /Users/maxrocketman/myproject/melon
export DJANGO_SETTINGS_MODULE=config.settings.local
exec poetry run python manage.py runserver 8000
