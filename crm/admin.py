"""
Django admin configuration for the crm app.

All four models (Company, Contact, Lead, Opportunity) are registered
with rich list views, filters, and search fields so you can test
data entry immediately at /admin/.
"""
from django.contrib import admin

from .models import Company, Contact, Lead, Opportunity


# ---------------------------------------------------------------------------
# Company
# ---------------------------------------------------------------------------

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display  = ("name", "industry", "email", "phone", "website", "created_at")
    list_filter   = ("industry",)
    search_fields = ("name", "email", "website")
    date_hierarchy = "created_at"
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (None, {
            "fields": ("name", "industry"),
        }),
        ("Contact details", {
            "fields": ("email", "phone", "website", "address"),
        }),
        ("Notes", {
            "fields": ("notes",),
            "classes": ("collapse",),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )


# ---------------------------------------------------------------------------
# Contact
# ---------------------------------------------------------------------------

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display   = ("full_name", "email", "job_title", "company", "created_at")
    list_filter    = ("company",)
    search_fields  = ("first_name", "last_name", "email", "job_title")
    autocomplete_fields = ("company",)
    date_hierarchy  = "created_at"
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (None, {
            "fields": ("first_name", "last_name", "email"),
        }),
        ("Professional info", {
            "fields": ("job_title", "company", "phone"),
        }),
        ("Notes", {
            "fields": ("notes",),
            "classes": ("collapse",),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="Name")
    def full_name(self, obj: Contact) -> str:
        return obj.full_name


# ---------------------------------------------------------------------------
# Lead
# ---------------------------------------------------------------------------

@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display   = ("title", "status", "source", "contact", "company", "assigned_to", "created_at")
    list_filter    = ("status", "source", "assigned_to")
    search_fields  = ("title", "contact__first_name", "contact__last_name", "company__name")
    autocomplete_fields = ("contact", "company", "assigned_to")
    date_hierarchy  = "created_at"
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (None, {
            "fields": ("title", "status", "source"),
        }),
        ("Related records", {
            "fields": ("contact", "company", "assigned_to"),
        }),
        ("Notes", {
            "fields": ("notes",),
            "classes": ("collapse",),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )


# ---------------------------------------------------------------------------
# Opportunity
# ---------------------------------------------------------------------------

@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display   = (
        "title", "stage", "value", "probability",
        "expected_close_date", "company", "assigned_to", "created_at",
    )
    list_filter    = ("stage", "assigned_to", "expected_close_date")
    search_fields  = ("title", "contact__first_name", "contact__last_name", "company__name")
    autocomplete_fields = ("lead", "contact", "company", "assigned_to")
    date_hierarchy  = "created_at"
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (None, {
            "fields": ("title", "stage"),
        }),
        ("Financials", {
            "fields": ("value", "probability", "expected_close_date"),
        }),
        ("Related records", {
            "fields": ("lead", "contact", "company", "assigned_to"),
        }),
        ("Notes", {
            "fields": ("notes",),
            "classes": ("collapse",),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )
