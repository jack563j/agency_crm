"""WSGI config for agency_crm project."""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "agency_crm.settings")
application = get_wsgi_application()
