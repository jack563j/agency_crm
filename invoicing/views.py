"""Invoicing views for viewing and printing professional invoices."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from .models import Invoice


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
