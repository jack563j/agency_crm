#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate

# Automatically provision default RBAC roles, clean test data, and ensure superuser
python manage.py shell -c "
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from crm.models import Company, Contact, Lead, Opportunity
from sales.models import Product, Quote, QuoteLineItem, SalesOrder, SalesOrderLineItem
from invoicing.models import Invoice, InvoiceLineItem, Payment

# 1. Clean previous data palette for fresh testers
print('Cleaning database palette...')
Payment.objects.all().delete()
InvoiceLineItem.objects.all().delete()
Invoice.objects.all().delete()
SalesOrderLineItem.objects.all().delete()
SalesOrder.objects.all().delete()
QuoteLineItem.objects.all().delete()
Quote.objects.all().delete()
Product.objects.all().delete()
Opportunity.objects.all().delete()
Lead.objects.all().delete()
Contact.objects.all().delete()
Company.objects.all().delete()

# 2. Ensure RBAC Groups exist
for role in ['Admin', 'Sales Representative', 'Accountant']:
    Group.objects.get_or_create(name=role)

User = get_user_model()
# Remove non-admin test user accounts
User.objects.exclude(username='admin').delete()

admin_user = User.objects.filter(username='admin').first()
if not admin_user:
    admin_user = User.objects.create_superuser('admin', 'admin@agency.local', 'admin1234')
    print('Superuser created: admin / admin1234')
else:
    print('Superuser admin already exists')

# Attach Admin group to superuser
admin_group, _ = Group.objects.get_or_create(name='Admin')
admin_user.groups.add(admin_group)
print('Database cleaned and ready for new testers!')
"

