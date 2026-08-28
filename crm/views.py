"""Frontend views for CRM app (Leads, Opportunities, Companies, Contacts)."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import Company, Contact, Lead, LeadStatus, LeadSource, Opportunity, OpportunityStage
from agency_crm.roles import is_sales_rep, get_user_role


@login_required
def lead_list_view(request):
    """Modern Leads Hub view."""
    qs = Lead.objects.select_related("company", "contact", "assigned_to")
    if is_sales_rep(request.user):
        qs = qs.filter(assigned_to=request.user)
    
    status_filter = request.GET.get("status")
    if status_filter:
        qs = qs.filter(status=status_filter)

    return render(request, "crm/lead_list.html", {
        "leads": qs.order_by("-created_at"),
        "statuses": LeadStatus.choices,
        "current_status": status_filter,
    })


@login_required
def lead_create_view(request):
    """Create new lead with automatic company/contact creation."""
    if request.method == "POST":
        title = request.POST.get("title")
        company_name = request.POST.get("company_name")
        contact_name = request.POST.get("contact_name")
        email = request.POST.get("email")
        source = request.POST.get("source", "website")
        notes = request.POST.get("notes", "")

        company, _ = Company.objects.get_or_create(name=company_name)
        contact = None
        if email or contact_name:
            first = contact_name.split()[0] if contact_name else "Contact"
            last = " ".join(contact_name.split()[1:]) if " " in contact_name else ""
            contact, _ = Contact.objects.get_or_create(
                email=email or f"contact_{company.id}@agency.local",
                defaults={"first_name": first, "last_name": last, "company": company}
            )

        lead = Lead.objects.create(
            title=title,
            company=company,
            contact=contact,
            source=source,
            assigned_to=request.user,
            notes=notes
        )
        messages.success(request, f"Lead '{lead.title}' created successfully!")
        return redirect("lead_list")

    return render(request, "crm/lead_form.html", {
        "sources": LeadSource.choices
    })


@login_required
def lead_convert_view(request, pk):
    """1-Click conversion from Lead to Opportunity Deal."""
    lead = get_object_or_404(Lead, pk=pk)
    if lead.status != LeadStatus.CONVERTED:
        opp = Opportunity.objects.create(
            title=f"Deal: {lead.title}",
            lead=lead,
            company=lead.company,
            contact=lead.contact,
            assigned_to=lead.assigned_to or request.user,
            stage=OpportunityStage.PROSPECTING,
            notes=lead.notes
        )
        lead.status = LeadStatus.CONVERTED
        lead.save(update_fields=["status", "updated_at"])
        messages.success(request, f"Converted lead to Deal '{opp.title}'!")
    return redirect("opportunity_list")


@login_required
def opportunity_list_view(request):
    """Modern Opportunities & Deals Pipeline view."""
    qs = Opportunity.objects.select_related("company", "contact", "assigned_to", "lead")
    if is_sales_rep(request.user):
        qs = qs.filter(assigned_to=request.user)

    stage_filter = request.GET.get("stage")
    if stage_filter:
        qs = qs.filter(stage=stage_filter)

    return render(request, "crm/opportunity_list.html", {
        "opportunities": qs.order_by("-created_at"),
        "stages": OpportunityStage.choices,
        "current_stage": stage_filter,
    })


@login_required
def opportunity_create_view(request):
    """Create new deal."""
    if request.method == "POST":
        title = request.POST.get("title")
        company_name = request.POST.get("company_name")
        stage = request.POST.get("stage", OpportunityStage.PROSPECTING)
        value = request.POST.get("value", 0)
        prob = request.POST.get("probability", 50)
        close_date = request.POST.get("expected_close_date") or None

        company, _ = Company.objects.get_or_create(name=company_name)
        opp = Opportunity.objects.create(
            title=title,
            company=company,
            stage=stage,
            value=value,
            probability=prob,
            expected_close_date=close_date,
            assigned_to=request.user
        )
        messages.success(request, f"Opportunity '{opp.title}' created!")
        return redirect("opportunity_list")

    return render(request, "crm/opportunity_form.html", {
        "stages": OpportunityStage.choices
    })


@login_required
def company_list_view(request):
    """List of client companies."""
    companies = Company.objects.prefetch_related("contacts", "opportunities", "leads").order_by("name")
    return render(request, "crm/company_list.html", {"companies": companies})


@login_required
def contact_list_view(request):
    """List of client contacts."""
    contacts = Contact.objects.select_related("company").order_by("last_name", "first_name")
    return render(request, "crm/contact_list.html", {"contacts": contacts})
