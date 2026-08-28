"""Invoicing views for viewing, creating, and printing professional invoices."""
import datetime
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import Invoice, InvoiceLineItem, InvoiceStatus, Payment
from crm.models import Company, Contact
from agency_crm.roles import is_sales_rep, is_accountant, is_admin


@login_required
def invoice_list_view(request):
    """Modern Billing & Invoices Hub."""
    if is_sales_rep(request.user):
        messages.warning(request, "Billing is restricted to Accountants and Administrators.")
        return redirect("dashboard")

    invoices = (
        Invoice.objects.select_related("company", "contact", "assigned_to")
        .prefetch_related("line_items", "payments")
        .order_by("-created_at")
    )
    status_filter = request.GET.get("status")
    if status_filter:
        invoices = invoices.filter(status=status_filter)

    return render(request, "invoicing/invoice_list.html", {
        "invoices": invoices,
        "statuses": InvoiceStatus.choices,
        "current_status": status_filter,
    })


@login_required
def invoice_create_view(request):
    """Manual Invoice Generator."""
    if is_sales_rep(request.user):
        messages.error(request, "Permission Denied: Invoicing is restricted to Finance & Admins.")
        return redirect("dashboard")

    if request.method == "POST":
        company_name = request.POST.get("company_name")
        days = int(request.POST.get("due_date_days", 30))
        notes = request.POST.get("notes", "")

        today = timezone.now().date()
        inv_num = f"INV-{today.strftime('%Y%m')}-{int(timezone.now().timestamp()) % 10000:04d}"

        company, _ = Company.objects.get_or_create(name=company_name)
        invoice = Invoice.objects.create(
            invoice_number=inv_num,
            company=company,
            issue_date=today,
            due_date=today + datetime.timedelta(days=days),
            status=InvoiceStatus.SENT,
            assigned_to=request.user,
            notes=notes
        )

        desc_list = request.POST.getlist("item_description[]")
        qty_list = request.POST.getlist("item_quantity[]")
        price_list = request.POST.getlist("item_price[]")

        for desc, qty, price in zip(desc_list, qty_list, price_list):
            if desc and price:
                InvoiceLineItem.objects.create(
                    invoice=invoice,
                    description=desc,
                    quantity=int(qty or 1),
                    unit_price=Decimal(price or 0)
                )

        messages.success(request, f"Invoice #{invoice.invoice_number} created!")
        return redirect("invoice_detail", pk=invoice.id)

    return render(request, "invoicing/invoice_form.html")


@login_required
def invoice_detail(request, pk):
    """Render full professional invoice document with actions."""
    invoice = get_object_or_404(
        Invoice.objects.select_related("company", "contact", "order", "assigned_to")
        .prefetch_related("line_items__product", "payments"),
        pk=pk,
    )
    return render(request, "invoicing/invoice_detail.html", {"invoice": invoice})


@login_required
def invoice_print(request, pk):
    """Render print-optimized invoice view."""
    invoice = get_object_or_404(
        Invoice.objects.select_related("company", "contact", "order")
        .prefetch_related("line_items__product", "payments"),
        pk=pk,
    )
    return render(request, "invoicing/invoice_print.html", {"invoice": invoice})
