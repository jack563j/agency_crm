"""Dashboard, Team Management, and RBAC views for agency_crm."""
import json
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.db import transaction
from django.db.models import Count, Sum
from django.shortcuts import redirect, render
from django.utils import timezone

from crm.models import Company, Contact, Lead, LeadStatus, LeadSource, Opportunity, OpportunityStage
from sales.models import Product, Quote, SalesOrder
from invoicing.models import Invoice, InvoiceStatus, Payment
from .roles import get_user_role, is_admin, is_sales_rep, is_accountant, admin_required, ALL_ROLES, ROLE_ADMIN, ROLE_SALES, ROLE_ACCOUNTANT

User = get_user_model()


@login_required
def dashboard_view(request):
    """Role-aware executive dashboard."""
    user = request.user
    user_role = get_user_role(user)

    # Base Querysets with RBAC filtering
    leads_qs = Lead.objects.all()
    opps_qs = Opportunity.objects.all()
    quotes_qs = Quote.objects.all()
    orders_qs = SalesOrder.objects.all()

    if is_sales_rep(user):
        leads_qs = leads_qs.filter(assigned_to=user)
        opps_qs = opps_qs.filter(assigned_to=user)
        quotes_qs = quotes_qs.filter(assigned_to=user)
        orders_qs = orders_qs.filter(assigned_to=user)

    # 1. Lead Metrics
    active_leads_count = leads_qs.exclude(status__in=[LeadStatus.CONVERTED, LeadStatus.UNQUALIFIED]).count()
    total_leads_count = leads_qs.count()
    converted_leads_count = leads_qs.filter(status=LeadStatus.CONVERTED).count()
    lead_conversion_rate = round((converted_leads_count / total_leads_count * 100), 1) if total_leads_count > 0 else 0

    # 2. Opportunity / Pipeline Metrics
    open_opps = opps_qs.exclude(stage__in=[OpportunityStage.CLOSED_WON, OpportunityStage.CLOSED_LOST])
    pipeline_value = open_opps.aggregate(total=Sum("value"))["total"] or Decimal("0.00")
    weighted_pipeline = sum(opp.weighted_value for opp in open_opps)

    won_deals = opps_qs.filter(stage=OpportunityStage.CLOSED_WON)
    won_revenue = won_deals.aggregate(total=Sum("value"))["total"] or Decimal("0.00")
    total_closed = opps_qs.filter(stage__in=[OpportunityStage.CLOSED_WON, OpportunityStage.CLOSED_LOST]).count()
    win_rate = round((won_deals.count() / total_closed * 100), 1) if total_closed > 0 else 0

    # 3. Invoicing Metrics (Hidden for standard Sales Reps)
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
        stage_opps = opps_qs.filter(stage=stage_key)
        stage_labels.append(stage_name)
        stage_counts.append(stage_opps.count())
        stage_values.append(float(stage_opps.aggregate(total=Sum("value"))["total"] or 0))

    # 5. Chart Data: Lead Sources Breakdown
    source_labels = []
    source_counts = []
    for source_key, source_name in LeadSource.choices:
        count = leads_qs.filter(source=source_key).count()
        if count > 0:
            source_labels.append(source_name)
            source_counts.append(count)

    # 6. Recent Activities
    recent_leads = leads_qs.select_related("company", "contact").order_by("-created_at")[:5]
    recent_invoices = all_invoices.select_related("company", "contact").order_by("-created_at")[:5]

    context = {
        "user_role": user_role,
        "is_sales_rep": is_sales_rep(user),
        "is_accountant": is_accountant(user),
        "is_admin": is_admin(user),

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
        "recent_invoices": recent_invoices,
    }
    return render(request, "dashboard/index.html", context)


@login_required
@admin_required
def team_management_view(request):
    """Admin-only User & Role Access Management."""
    if request.method == "POST":
        username = request.POST.get("username", "").strip().lower()
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password")
        role = request.POST.get("role", ROLE_SALES)
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()

        if User.objects.filter(username=username).exists():
            messages.error(request, f"User '{username}' already exists.")
        else:
            with transaction.atomic():
                new_user = User.objects.create_user(
                    username=username, email=email, password=password,
                    first_name=first_name, last_name=last_name
                )
                group, _ = Group.objects.get_or_create(name=role)
                new_user.groups.add(group)
                if role == ROLE_ADMIN:
                    new_user.is_staff = True
                    new_user.save()
            messages.success(request, f"User '{username}' created successfully as {role}!")
            return redirect("team_management")

    users = User.objects.prefetch_related("groups").order_by("username")
    user_list = []
    for u in users:
        user_list.append({
            "user": u,
            "role": get_user_role(u),
        })

    return render(request, "agency_crm/team_list.html", {
        "team_members": user_list,
        "available_roles": ALL_ROLES
    })
