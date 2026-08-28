"""Frontend views for Sales app (Quotes, Orders, Products)."""
import datetime
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import Product, Quote, QuoteLineItem, QuoteStatus, SalesOrder, SalesOrderLineItem, OrderStatus
from crm.models import Company, Contact, Opportunity
from invoicing.models import Invoice, InvoiceLineItem, InvoiceStatus
from agency_crm.roles import is_sales_rep, is_accountant


@login_required
def quote_list_view(request):
    """Modern Quotes List."""
    qs = Quote.objects.select_related("company", "contact", "assigned_to").prefetch_related("line_items")
    if is_sales_rep(request.user):
        qs = qs.filter(assigned_to=request.user)
    return render(request, "sales/quote_list.html", {"quotes": qs.order_by("-created_at")})


@login_required
def quote_create_view(request):
    """Create new quote with line items."""
    if request.method == "POST":
        title = request.POST.get("title")
        company_name = request.POST.get("company_name")
        days = int(request.POST.get("valid_until_days", 30))
        
        company, _ = Company.objects.get_or_create(name=company_name)
        quote = Quote.objects.create(
            title=title,
            company=company,
            valid_until=timezone.now().date() + datetime.timedelta(days=days),
            assigned_to=request.user
        )

        # Process multiple dynamic line items
        desc_list = request.POST.getlist("item_description[]")
        qty_list = request.POST.getlist("item_quantity[]")
        price_list = request.POST.getlist("item_price[]")

        for desc, qty, price in zip(desc_list, qty_list, price_list):
            if desc and price:
                QuoteLineItem.objects.create(
                    quote=quote,
                    description=desc,
                    quantity=int(qty or 1),
                    unit_price=Decimal(price or 0)
                )

        messages.success(request, f"Quote '{quote.title}' created successfully!")
        return redirect("quote_list")

    products = Product.objects.filter(is_active=True)
    return render(request, "sales/quote_form.html", {"products": products})


@login_required
def quote_convert_view(request, pk):
    """1-Click convert Quote -> Confirmed Sales Order."""
    quote = get_object_or_404(Quote, pk=pk)
    quote.status = QuoteStatus.ACCEPTED
    quote.save(update_fields=["status", "updated_at"])

    order = SalesOrder.objects.create(
        title=f"Order: {quote.title}",
        quote=quote,
        company=quote.company,
        contact=quote.contact,
        status=OrderStatus.CONFIRMED,
        ordered_at=timezone.now().date(),
        assigned_to=quote.assigned_to or request.user,
        notes=quote.notes
    )

    for item in quote.line_items.all():
        SalesOrderLineItem.objects.create(
            order=order, product=item.product, description=item.description,
            quantity=item.quantity, unit_price=item.unit_price, discount=item.discount
        )

    messages.success(request, f"Quote converted to Confirmed Sales Order #{order.id}!")
    return redirect("order_list")


@login_required
def order_list_view(request):
    """Modern Sales Orders List."""
    qs = SalesOrder.objects.select_related("company", "contact", "quote").prefetch_related("line_items")
    if is_sales_rep(request.user):
        qs = qs.filter(assigned_to=request.user)
    return render(request, "sales/order_list.html", {"orders": qs.order_by("-created_at")})


@login_required
def order_invoice_view(request, pk):
    """1-Click convert Sales Order -> Invoice."""
    if is_sales_rep(request.user):
        messages.error(request, "Permission Denied: Only Accountants and Admins can generate Invoices.")
        return redirect("order_list")

    order = get_object_or_404(SalesOrder, pk=pk)
    today = timezone.now().date()
    inv_num = f"INV-{today.strftime('%Y%m')}-{order.id:04d}"

    invoice = Invoice.objects.create(
        invoice_number=inv_num,
        order=order,
        company=order.company,
        contact=order.contact,
        issue_date=today,
        due_date=today + datetime.timedelta(days=30),
        status=InvoiceStatus.SENT,
        assigned_to=request.user
    )

    for item in order.line_items.all():
        InvoiceLineItem.objects.create(
            invoice=invoice, product=item.product, description=item.description,
            quantity=item.quantity, unit_price=item.unit_price, discount=item.discount
        )

    messages.success(request, f"Generated Invoice #{invoice.invoice_number} from order!")
    return redirect("invoice_detail", pk=invoice.id)


@login_required
def product_list_view(request):
    """Product Catalog List."""
    products = Product.objects.all().order_by("name")
    return render(request, "sales/product_list.html", {"products": products})
