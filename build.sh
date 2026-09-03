#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate

# Provision RBAC groups and admin superuser
# FRESH_INSTALL=true  → wipes all data (use only for demo/testing deployments)
# FRESH_INSTALL=false → safe for production customers (data is NEVER deleted)
python manage.py shell -c "
import os
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

fresh_install = os.getenv('FRESH_INSTALL', 'false').lower() in ('1', 'true', 'yes')

if fresh_install:
    print('FRESH_INSTALL=true: Wiping all data for clean demo...')
    from crm.models import Company, Contact, Lead, Opportunity
    from sales.models import Product, Quote, QuoteLineItem, SalesOrder, SalesOrderLineItem
    from invoicing.models import Invoice, InvoiceLineItem, Payment
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
    User = get_user_model()
    User.objects.exclude(username='admin').delete()
    print('All demo data wiped.')
else:
    print('Production mode: existing customer data preserved.')

# Always ensure RBAC groups exist
for role in ['Admin', 'Sales Representative', 'Accountant']:
    Group.objects.get_or_create(name=role)

# Read admin credentials from environment (set per-customer on Render)
User = get_user_model()
admin_username = os.getenv('ADMIN_USERNAME', 'admin')
admin_email    = os.getenv('ADMIN_EMAIL', 'admin@agency.local')
admin_password = os.getenv('ADMIN_PASSWORD', 'changeme123')

admin_user = User.objects.filter(username=admin_username).first()
if not admin_user:
    admin_user = User.objects.create_superuser(admin_username, admin_email, admin_password)
    print(f'Superuser created: {admin_username}')
else:
    print(f'Superuser {admin_username} already exists — password unchanged.')

admin_group, _ = Group.objects.get_or_create(name='Admin')
admin_user.groups.add(admin_group)
print('Build complete!')
"
