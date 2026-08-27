"""
Django admin configuration for the sales app.

- Product: standard list/search
- Quote: full detail with QuoteLineItem inline
- SalesOrder: full detail with SalesOrderLineItem inline
"""
from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Product,
    Quote, QuoteLineItem,
    SalesOrder, SalesOrderLineItem,
)


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display   = ("name", "sku", "unit_price", "is_active", "created_at")
    list_filter    = ("is_active",)
    search_fields  = ("name", "sku")
    list_editable  = ("is_active",)
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (None, {
            "fields": ("name", "sku", "unit_price", "is_active"),
        }),
        ("Description", {
            "fields": ("description",),
            "classes": ("collapse",),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )


# ---------------------------------------------------------------------------
# Quote
# ---------------------------------------------------------------------------

class QuoteLineItemInline(admin.TabularInline):
    model       = QuoteLineItem
    extra       = 1
    autocomplete_fields = ("product",)
    fields      = ("product", "description", "quantity", "unit_price", "discount")
    readonly_fields = ("subtotal_display",)

    @admin.display(description="Subtotal")
    def subtotal_display(self, obj: QuoteLineItem) -> str:
        if obj.pk:
            return f"{obj.subtotal:,.2f}"
        return "—"


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display   = ("title", "status", "company", "contact", "valid_until", "assigned_to", "created_at")
    list_filter    = ("status", "assigned_to")
    search_fields  = ("title", "company__name", "contact__first_name", "contact__last_name")
    autocomplete_fields = ("opportunity", "contact", "company", "assigned_to")
    date_hierarchy  = "created_at"
    readonly_fields = ("created_at", "updated_at")
    inlines        = [QuoteLineItemInline]

    fieldsets = (
        (None, {
            "fields": ("title", "status", "valid_until"),
        }),
        ("Related records", {
            "fields": ("opportunity", "contact", "company", "assigned_to"),
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
# SalesOrder
# ---------------------------------------------------------------------------

class SalesOrderLineItemInline(admin.TabularInline):
    model       = SalesOrderLineItem
    extra       = 1
    autocomplete_fields = ("product",)
    fields      = ("product", "description", "quantity", "unit_price", "discount")
    readonly_fields = ("subtotal_display",)

    @admin.display(description="Subtotal")
    def subtotal_display(self, obj: SalesOrderLineItem) -> str:
        if obj.pk:
            return f"{obj.subtotal:,.2f}"
        return "—"


@admin.register(SalesOrder)
class SalesOrderAdmin(admin.ModelAdmin):
    list_display   = ("title", "status", "company", "contact", "ordered_at", "assigned_to", "created_at")
    list_filter    = ("status", "assigned_to")
    search_fields  = ("title", "company__name", "contact__first_name", "contact__last_name")
    autocomplete_fields = ("quote", "contact", "company", "assigned_to")
    date_hierarchy  = "created_at"
    readonly_fields = ("created_at", "updated_at")
    inlines        = [SalesOrderLineItemInline]

    fieldsets = (
        (None, {
            "fields": ("title", "status", "ordered_at"),
        }),
        ("Related records", {
            "fields": ("quote", "contact", "company", "assigned_to"),
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
