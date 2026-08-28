"""
Django admin configuration for the invoicing app.

- Invoice: full detail with InvoiceLineItem + Payment inlines & 1-click Print/PDF link
- Payment: standalone list (also accessible via Invoice inline)
"""
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import Invoice, InvoiceLineItem, Payment


# ---------------------------------------------------------------------------
# Inlines
# ---------------------------------------------------------------------------

class InvoiceLineItemInline(admin.TabularInline):
    model   = InvoiceLineItem
    extra   = 1
    autocomplete_fields = ("product",)
    fields  = ("product", "description", "quantity", "unit_price", "discount")
    readonly_fields = ("subtotal_display",)

    @admin.display(description="Subtotal")
    def subtotal_display(self, obj: InvoiceLineItem) -> str:
        return f"{obj.subtotal:,.2f}" if obj.pk else "—"


class PaymentInline(admin.TabularInline):
    model  = Payment
    extra  = 1
    fields = ("payment_date", "amount", "method", "reference")


# ---------------------------------------------------------------------------
# Invoice
# ---------------------------------------------------------------------------

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display   = (
        "invoice_number", "status", "company", "contact",
        "issue_date", "due_date", "balance_due_display", "print_action", "assigned_to",
    )
    list_filter    = ("status", "assigned_to", "due_date")
    search_fields  = ("invoice_number", "company__name", "contact__first_name", "contact__last_name")
    autocomplete_fields = ("order", "contact", "company", "assigned_to")
    date_hierarchy  = "created_at"
    readonly_fields = ("created_at", "updated_at", "subtotal_display", "amount_paid_display", "balance_due_display")
    inlines        = [InvoiceLineItemInline, PaymentInline]

    fieldsets = (
        (None, {
            "fields": ("invoice_number", "status"),
        }),
        ("Dates", {
            "fields": ("issue_date", "due_date"),
        }),
        ("Related records", {
            "fields": ("order", "contact", "company", "assigned_to"),
        }),
        ("Financials (read-only)", {
            "fields": ("subtotal_display", "amount_paid_display", "balance_due_display"),
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

    @admin.display(description="Subtotal")
    def subtotal_display(self, obj: Invoice) -> str:
        return f"{obj.subtotal:,.2f}"

    @admin.display(description="Paid")
    def amount_paid_display(self, obj: Invoice) -> str:
        return f"{obj.amount_paid:,.2f}"

    @admin.display(description="Balance Due")
    def balance_due_display(self, obj: Invoice) -> str:
        balance = obj.balance_due
        return f"{balance:,.2f}"

    @admin.display(description="PDF / Print")
    def print_action(self, obj: Invoice) -> str:
        url = reverse("invoice_detail", args=[obj.pk])
        return format_html(
            '<a class="button" href="{}" target="_blank" style="padding: 3px 8px; background: #2563eb; color: white; border-radius: 4px; text-decoration: none; font-size: 11px; font-weight: bold;">📄 View Invoice</a>',
            url
        )


# ---------------------------------------------------------------------------
# Payment (standalone, for easy browsing across all invoices)
# ---------------------------------------------------------------------------

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display   = ("invoice", "amount", "method", "payment_date", "reference", "created_at")
    list_filter    = ("method", "payment_date")
    search_fields  = ("invoice__invoice_number", "reference")
    autocomplete_fields = ("invoice",)
    date_hierarchy  = "payment_date"
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (None, {
            "fields": ("invoice", "amount", "payment_date", "method", "reference"),
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
