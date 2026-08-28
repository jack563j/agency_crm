"""URL routing for CRM app."""
from django.urls import path
from . import views

urlpatterns = [
    path("leads/", views.lead_list_view, name="lead_list"),
    path("leads/add/", views.lead_create_view, name="lead_create"),
    path("leads/<int:pk>/convert/", views.lead_convert_view, name="lead_convert"),
    
    path("opportunities/", views.opportunity_list_view, name="opportunity_list"),
    path("opportunities/add/", views.opportunity_create_view, name="opportunity_create"),

    path("companies/", views.company_list_view, name="company_list"),
    path("contacts/", views.contact_list_view, name="contact_list"),
]
