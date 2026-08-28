"""agency_crm URL configuration."""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include

from .views import dashboard_view

urlpatterns = [
    path("", dashboard_view, name="dashboard"),
    path("dashboard/", dashboard_view, name="dashboard_alias"),
    path("admin/", admin.site.urls),
    path("invoices/", include("invoicing.urls")),
    
    # Built-in Auth
    path("accounts/login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(next_page="login"), name="logout"),
]
