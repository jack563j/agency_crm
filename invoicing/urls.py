"""URL routing for invoicing app."""
from django.urls import path
from . import views

urlpatterns = [
    path("", views.invoice_list_view, name="invoice_list"),
    path("add/", views.invoice_create_view, name="invoice_create"),
    path("<int:pk>/", views.invoice_detail, name="invoice_detail"),
    path("<int:pk>/print/", views.invoice_print, name="invoice_print"),
]
