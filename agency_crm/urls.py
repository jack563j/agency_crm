"""agency_crm URL configuration."""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include

from .views import dashboard_view, team_management_view
from .ai_views import ai_chat_endpoint, ai_clear_history

urlpatterns = [
    # Dashboard & Team
    path("", dashboard_view, name="dashboard"),
    path("dashboard/", dashboard_view, name="dashboard_alias"),
    path("team/", team_management_view, name="team_management"),

    # AI Copilot Endpoints
    path("api/ai/chat/", ai_chat_endpoint, name="ai_chat_api"),
    path("api/ai/clear/", ai_clear_history, name="ai_clear_api"),

    # Frontend Apps
    path("crm/", include("crm.urls")),
    path("sales/", include("sales.urls")),
    path("invoices/", include("invoicing.urls")),

    # Direct top-level shortcuts for convenience
    path("leads/", include("crm.urls")),
    path("quotes/", include("sales.urls")),

    # Admin Panel
    path("admin/", admin.site.urls),

    # Built-in Auth
    path("accounts/login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(next_page="login"), name="logout"),
]
