"""Dashboard and authentication views for agency_crm."""
import json
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, F, Q, ExpressionWrapper, DecimalField
from django.shortcuts import render
from django.utils import timezone

from crm.models import Company, Contact, Lead, LeadStatus, LeadSource, Opportunity, OpportunityStage
from sales.models import Product, Quote, SalesOrder, OrderStatus
from invoicing.models import Invoice, InvoiceStatus, Payment


@login_required
def dashboard_view(request):
    """Aggregates all agency metrics and charts for the main dashboard."""
    # 1. Lead Metrics
    active_leads_count = Lead.objects.exclude(
        status__in=[LeadStatus.CONVERTED, LeadStatus.UNQUALIFIED]
    ).count()
    total_leads_count = Lead.objects.count()
    converted_leads_count = Lead.objects.filter(status=LeadStatus.CONVERTED).count()
    lead_conversion_rate = (
        round((converted_leads_count / total_leads_count * 100), 1)
        if total_leads_count > 0 else 0
    )

    # 2. Opportunity / Pipeline Metrics
    open_opps = Opportunity.objects.exclude(
        stage__in=[OpportunityStage.CLOSED_WON, OpportunityStage.CLOSED_LOST]
    )
    pipeline_value = open_opps.aggregate(total=Sum("value"))["total"] or Decimal("0.00")
    
    # Calculate weighted value
    weighted_pipeline = sum(opp.weighted_value for opp in open_opps)

    won_deals = Opportunity.objects.filter(stage=OpportunityStage.CLOSED_WON)
    won_revenue = won_deals.aggregate(total=Sum("value"))["total"] or Decimal("0.00")
    
    total_closed = Opportunity.objects.filter(
        stage__in=[OpportunityStage.CLOSED_WON, OpportunityStage.CLOSED_LOST]
    ).count()
    win_rate = (
        round((won_deals.count() / total_closed * 100), 1)
        if total_closed > 0 else 0
    )

    # 3. Invoicing Metrics
    all_invoices = Invoice.objects.exclude(status=InvoiceStatus.CANCELLED)
    total_invoiced = sum(inv.subtotal for inv in all_invoices)
    total_collected = Payment.objects.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    outstanding_balance = float(total_invoiced) - float(total_collected)
    
    overdue_invoices_count = sum(1 for inv in all_invoices if inv.is_overdue)

    # 4. Chart Data: Opportunities by Stage
    stage_labels = []
    stage_counts = []
    stage_values = []
    for stage_key, stage_name in OpportunityStage.choices:
        stage_opps = Opportunity.objects.filter(stage=stage_key)
        count = stage_opps.count()
        val = float(stage_opps.aggregate(total=Sum("value"))["total"] or 0)
        stage_labels.append(stage_name)
        stage_counts.append(count)
        stage_values.append(val)

    # 5. Chart Data: Lead Sources Breakdown
    source_labels = []
    source_counts = []
    for source_key, source_name in LeadSource.choices:
        count = Lead.objects.filter(source=source_key).count()
        if count > 0:
            source_labels.append(source_name)
            source_counts.append(count)

    # 6. Recent Activities
    recent_leads = Lead.objects.select_related("company", "contact").order_by("-created_at")[:5]
    recent_opps = Opportunity.objects.select_related("company", "contact").order_by("-created_at")[:5]
    recent_invoices = Invoice.objects.select_related("company", "contact").order_by("-created_at")[:5]
    recent_orders = SalesOrder.objects.select_related("company", "contact").order_by("-created_at")[:5]

    context = {
        # KPI Cards
        "pipeline_value": pipeline_value,
        "weighted_pipeline": weighted_pipeline,
        "won_revenue": won_revenue,
        "win_rate": win_rate,
        "active_leads_count": active_leads_count,
        "lead_conversion_rate": lead_conversion_rate,
        "total_invoiced": total_invoiced,
        "total_collected": total_collected,
        "outstanding_balance": outstanding_balance,
        "overdue_invoices_count": overdue_invoices_count,

        # Chart JSON data
        "stage_labels_json": json.dumps(stage_labels),
        "stage_values_json": json.dumps(stage_values),
        "stage_counts_json": json.dumps(stage_counts),
        "source_labels_json": json.dumps(source_labels),
        "source_counts_json": json.dumps(source_counts),

        # Recent Lists
        "recent_leads": recent_leads,
        "recent_opps": recent_opps,
        "recent_invoices": recent_invoices,
        "recent_orders": recent_orders,

        # Quick Stats Counts
        "companies_count": Company.objects.count(),
        "contacts_count": Contact.objects.count(),
        "products_count": Product.objects.count(),
    }
    return render(request, "dashboard/index.html", context)
