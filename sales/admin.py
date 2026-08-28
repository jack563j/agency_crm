"""
Django admin configuration for the sales app.

- Product: standard list/search
- Quote: full detail with QuoteLineItem inline & Convert to Order action
- SalesOrder: full detail with SalesOrderLineItem inline & Generate Invoice action
"""
import datetime
from django.contrib import admin
from django.utils import timezone

from .models import (
    Product,
    Quote, QuoteLineItem, QuoteStatus,
    SalesOrder, SalesOrderLineItem, OrderStatus,
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
    actions        = ["convert_to_sales_order"]

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

    @admin.action(description="Convert selected Quote(s) to Confirmed Sales Order")
    def convert_to_sales_order(self, request, queryset):
        created_orders = 0
        for quote in queryset:
            quote.status = QuoteStatus.ACCEPTED
            quote.save(update_fields=["status", "updated_at"])

            order = SalesOrder.objects.create(
                title=f"Order: {quote.title}",
                quote=quote,
                contact=quote.contact,
                company=quote.company,
                status=OrderStatus.CONFIRMED,
                ordered_at=timezone.now().date(),
                assigned_to=quote.assigned_to or request.user,
                notes=quote.notes,
            )

            # Copy line items
            for item in quote.line_items.all():
                SalesOrderLineItem.objects.create(
                    order=order,
                    product=item.product,
                    description=item.description,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    discount=item.discount,
                )
            created_orders += 1
        self.message_user(request, f"Successfully converted {created_orders} quote(s) to Sales Order(s).")


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
    actions        = ["generate_invoice"]

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

    @admin.action(description="Generate Invoice from selected Sales Order(s)")
    def generate_invoice(self, request, queryset):
        from invoicing.models import Invoice, InvoiceLineItem, InvoiceStatus
        created_invoices = 0
        today = timezone.now().date()
        due_date = today + datetime.timedelta(days=30)

        for order in queryset:
            # Generate unique invoice number
            inv_number = f"INV-{today.strftime('%Y%m')}-{order.id:04d}"
            # Check if invoice with this number exists and make unique if needed
            counter = 1
            original_inv_number = inv_number
            while Invoice.objects.filter(invoice_number=inv_number).exists():
                inv_number = f"{original_inv_number}-{counter}"
                counter += 1

            invoice = Invoice.objects.create(
                invoice_number=inv_number,
                order=order,
                contact=order.contact,
                company=order.company,
                status=InvoiceStatus.SENT,
                issue_date=today,
                due_date=due_date,
                assigned_to=order.assigned_to or request.user,
                notes=f"Generated from {order.title}",
            )

            # Copy line items
            for item in order.line_items.all():
                InvoiceLineItem.objects.create(
                    invoice=invoice,
                    product=item.product,
                    description=item.description,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    discount=item.discount,
                )
            created_invoices += 1
        self.message_user(request, f"Successfully created {created_invoices} Invoice(s) from selected Sales Orders.")
