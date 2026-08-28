#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate

# Automatically provision default RBAC roles and admin superuser
python manage.py shell -c "
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

# Ensure RBAC Groups exist
for role in ['Admin', 'Sales Representative', 'Accountant']:
    Group.objects.get_or_create(name=role)

User = get_user_model()
admin_user = User.objects.filter(username='admin').first()
if not admin_user:
    admin_user = User.objects.create_superuser('admin', 'admin@agency.local', 'admin1234')
    print('Superuser created: admin / admin1234')
else:
    print('Superuser admin already exists')

# Attach Admin group to superuser
admin_group, _ = Group.objects.get_or_create(name='Admin')
admin_user.groups.add(admin_group)
"
