#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate

# Automatically create admin superuser if not present
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@agency.local', 'admin1234')
    print('Superuser created: admin / admin1234')
else:
    print('Superuser admin already exists')
"
