"""
AI CRM Copilot Engine with Google Gemini API & Strict Role-Based Access Control.
"""
import os
import json
import requests
import datetime
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import transaction
from django.utils import timezone

from crm.models import Company, Contact, Lead, LeadStatus, LeadSource, Opportunity, OpportunityStage
from sales.models import Product, Quote, QuoteLineItem, QuoteStatus, SalesOrder, SalesOrderLineItem, OrderStatus
from invoicing.models import Invoice, InvoiceLineItem, InvoiceStatus, Payment
from .roles import get_user_role, is_admin, is_sales_rep, is_accountant, ROLE_ADMIN, ROLE_SALES, ROLE_ACCOUNTANT

User = get_user_model()


# ---------------------------------------------------------------------------
# CRM Tool Declarations for Gemini Function Calling
# ---------------------------------------------------------------------------

TOOLS_DEFINITION = [
    {
        "name": "create_user_account",
        "description": "Create a new team member/user account. STRICTLY RESTRICTED TO ADMINS AND MANAGERS ONLY.",
        "parameters": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "description": "Unique username (e.g., 'john_doe')"},
                "email": {"type": "string", "description": "User email address"},
                "password": {"type": "string", "description": "Initial password (if not provided, a secure one will be generated)"},
                "role": {"type": "string", "description": "Role to assign: 'Admin', 'Sales Representative', or 'Accountant'"},
                "first_name": {"type": "string", "description": "First name"},
                "last_name": {"type": "string", "description": "Last name"}
            },
            "required": ["username", "email", "role"]
        }
    },
    {
        "name": "create_lead",
        "description": "Create a new inbound or outbound sales lead with company and contact details.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Lead subject or deal interest (e.g. 'Cloud Migration Contract')"},
                "company_name": {"type": "string", "description": "Name of the prospective client company"},
                "contact_name": {"type": "string", "description": "Full name of the primary contact person"},
                "email": {"type": "string", "description": "Contact email address"},
                "phone": {"type": "string", "description": "Contact phone number (optional)"},
                "source": {"type": "string", "description": "Lead source: website, referral, cold_call, social, event, other"},
                "notes": {"type": "string", "description": "Notes or requirements from the lead"}
            },
            "required": ["title", "company_name"]
        }
    },
    {
        "name": "create_quote",
        "description": "Create a sales price proposal (Quote) with line items for a client.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Quote title (e.g. 'Quote for Q3 Marketing Retainer')"},
                "company_name": {"type": "string", "description": "Client company name"},
                "contact_name": {"type": "string", "description": "Contact person name (optional)"},
                "valid_until_days": {"type": "integer", "description": "Days until expiration (default: 30)"},
                "line_items": {
                    "type": "array",
                    "description": "List of billable line items",
                    "items": {
                        "type": "object",
                        "properties": {
                            "description": {"type": "string", "description": "Product or service description"},
                            "quantity": {"type": "integer", "description": "Quantity"},
                            "unit_price": {"type": "number", "description": "Price per unit"},
                            "discount": {"type": "number", "description": "Discount percentage (0-100)"}
                        },
                        "required": ["description", "quantity", "unit_price"]
                    }
                }
            },
            "required": ["title", "company_name", "line_items"]
        }
    },
    {
        "name": "create_invoice",
        "description": "Generate a new client invoice with line items. RESTRICTED TO ADMINS AND ACCOUNTANTS.",
        "parameters": {
            "type": "object",
            "properties": {
                "company_name": {"type": "string", "description": "Client company name"},
                "contact_name": {"type": "string", "description": "Contact person name (optional)"},
                "due_date_days": {"type": "integer", "description": "Days until payment due (default: 30)"},
                "notes": {"type": "string", "description": "Invoice notes or payment terms"},
                "line_items": {
                    "type": "array",
                    "description": "List of billed line items",
                    "items": {
                        "type": "object",
                        "properties": {
                            "description": {"type": "string", "description": "Item description"},
                            "quantity": {"type": "integer", "description": "Quantity"},
                            "unit_price": {"type": "number", "description": "Price per unit"},
                            "discount": {"type": "number", "description": "Discount percentage (0-100)"}
                        },
                        "required": ["description", "quantity", "unit_price"]
                    }
                }
            },
            "required": ["company_name", "line_items"]
        }
    },
    {
        "name": "convert_record",
        "description": "Convert a Lead to an Opportunity, or convert a Quote to a Sales Order, or convert an Order to an Invoice.",
        "parameters": {
            "type": "object",
            "properties": {
                "conversion_type": {"type": "string", "description": "'lead_to_opportunity', 'quote_to_order', or 'order_to_invoice'"},
                "identifier": {"type": "string", "description": "ID or title/company of the record to convert"}
            },
            "required": ["conversion_type", "identifier"]
        }
    },
    {
        "name": "get_crm_insights",
        "description": "Query CRM performance metrics, pipeline totals, overdue balances, or active lead stats.",
        "parameters": {
            "type": "object",
            "properties": {
                "query_topic": {"type": "string", "description": "Topic to query: 'pipeline', 'revenue', 'overdue_invoices', 'my_leads', 'team_summary'"}
            },
            "required": ["query_topic"]
        }
    }
]


# ---------------------------------------------------------------------------
# Tool Execution Handlers with RBAC Validation
# ---------------------------------------------------------------------------

def execute_tool(tool_name: str, args: dict, user) -> dict:
    """Executes a CRM action on behalf of user, enforcing strict RBAC."""
    user_role = get_user_role(user)

    # 1. Create User Account (Admin Only)
    if tool_name == "create_user_account":
        if not is_admin(user):
            return {
                "error": True,
                "message": f"Permission Denied: Only Administrators and Managers can create user accounts. Your role is '{user_role}'."
            }
        username = args.get("username", "").strip().lower()
        email = args.get("email", "").strip().lower()
        role = args.get("role", ROLE_SALES)
        password = args.get("password") or f"Pass_{username}_2026!"
        first_name = args.get("first_name", "")
        last_name = args.get("last_name", "")

        if not username or not email:
            return {"error": True, "message": "Username and Email are required to create a user."}

        if User.objects.filter(username=username).exists():
            return {"error": True, "message": f"User with username '{username}' already exists."}
        
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

        return {
            "success": True,
            "message": f"Successfully created user account for '{username}' with role '{role}'. Credentials: Username=`{username}`, Password=`{password}`",
            "credentials": {"username": username, "password": password, "role": role}
        }

    # 2. Create Lead
    elif tool_name == "create_lead":
        company_name = args.get("company_name", "").strip()
        title = args.get("title", "").strip()
        contact_name = args.get("contact_name", "").strip()
        email = args.get("email", "").strip()
        phone = args.get("phone", "").strip()
        source = args.get("source", "website").lower()
        notes = args.get("notes", "")

        with transaction.atomic():
            company, _ = Company.objects.get_or_create(name=company_name)
            contact = None
            if contact_name or email:
                first = contact_name.split()[0] if contact_name else "Contact"
                last = " ".join(contact_name.split()[1:]) if " " in contact_name else ""
                contact_email = email or f"contact_{company.id}_{int(timezone.now().timestamp())}@agency.local"
                contact, _ = Contact.objects.get_or_create(
                    email=contact_email,
                    defaults={"first_name": first, "last_name": last, "company": company, "phone": phone}
                )
            
            lead = Lead.objects.create(
                title=title,
                company=company,
                contact=contact,
                source=source if source in [c[0] for c in LeadSource.choices] else LeadSource.OTHER,
                assigned_to=user,
                notes=notes
            )
        return {
            "success": True,
            "message": f"Lead '{lead.title}' created successfully for {company.name}. View it at [Leads Hub](/crm/leads/).",
            "lead_id": lead.id
        }

    # 3. Create Quote
    elif tool_name == "create_quote":
        company_name = args.get("company_name", "").strip()
        title = args.get("title", "").strip()
        contact_name = args.get("contact_name", "").strip()
        days = int(args.get("valid_until_days", 30))
        line_items_data = args.get("line_items", [])

        if not line_items_data:
            return {"error": True, "message": "Please specify at least one line item (description, quantity, price) for the quote."}

        with transaction.atomic():
            company, _ = Company.objects.get_or_create(name=company_name)
            contact = None
            if contact_name:
                contact = Contact.objects.filter(company=company).first()

            quote = Quote.objects.create(
                title=title,
                company=company,
                contact=contact,
                valid_until=timezone.now().date() + datetime.timedelta(days=days),
                assigned_to=user,
            )

            total = Decimal("0.00")
            for item in line_items_data:
                desc = item.get("description", "Service")
                qty = int(item.get("quantity", 1))
                price = Decimal(str(item.get("unit_price", 0)))
                disc = Decimal(str(item.get("discount", 0)))
                line = QuoteLineItem.objects.create(
                    quote=quote, description=desc, quantity=qty, unit_price=price, discount=disc
                )
                total += Decimal(str(line.subtotal))

        return {
            "success": True,
            "message": f"Quote '{quote.title}' created for {company.name} with {len(line_items_data)} items. Total: **${float(total):,.2f}**. View at [Quotes Hub](/sales/quotes/).",
            "quote_id": quote.id,
            "total": float(total)
        }

    # 4. Create Invoice (Admin / Accountant Only)
    elif tool_name == "create_invoice":
        if is_sales_rep(user):
            return {
                "error": True,
                "message": "Permission Denied: Invoicing is restricted to Accountants and Administrators."
            }

        company_name = args.get("company_name", "").strip()
        days = int(args.get("due_date_days", 30))
        notes = args.get("notes", "")
        line_items_data = args.get("line_items", [])

        if not line_items_data:
            return {"error": True, "message": "Cannot create an empty invoice. Please specify items, quantities, and prices."}

        today = timezone.now().date()
        inv_num = f"INV-{today.strftime('%Y%m')}-{int(timezone.now().timestamp()) % 10000:04d}"

        with transaction.atomic():
            company, _ = Company.objects.get_or_create(name=company_name)
            contact = Contact.objects.filter(company=company).first()

            invoice = Invoice.objects.create(
                invoice_number=inv_num,
                company=company,
                contact=contact,
                issue_date=today,
                due_date=today + datetime.timedelta(days=days),
                status=InvoiceStatus.SENT,
                assigned_to=user,
                notes=notes
            )

            for item in line_items_data:
                InvoiceLineItem.objects.create(
                    invoice=invoice,
                    description=item.get("description", "Consulting Services"),
                    quantity=int(item.get("quantity", 1)),
                    unit_price=Decimal(str(item.get("unit_price", 0))),
                    discount=Decimal(str(item.get("discount", 0)))
                )

        return {
            "success": True,
            "message": f"Invoice **#{invoice.invoice_number}** created for {company.name}. Total: **${invoice.subtotal:,.2f}**. [View & Print PDF](/invoices/{invoice.id}/).",
            "invoice_id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "pdf_link": f"/invoices/{invoice.id}/"
        }

    # 5. Convert Record
    elif tool_name == "convert_record":
        conv_type = args.get("conversion_type")
        identifier = args.get("identifier", "").strip()

        if conv_type == "lead_to_opportunity":
            lead = Lead.objects.filter(title__icontains=identifier).first() or Lead.objects.filter(id__iexact=identifier).first()
            if not lead:
                return {"error": True, "message": f"Could not find a Lead matching '{identifier}'."}
            
            with transaction.atomic():
                opp = Opportunity.objects.create(
                    title=f"Deal: {lead.title}",
                    lead=lead,
                    company=lead.company,
                    contact=lead.contact,
                    assigned_to=lead.assigned_to or user,
                    stage=OpportunityStage.PROSPECTING,
                    notes=lead.notes
                )
                lead.status = LeadStatus.CONVERTED
                lead.save()
            return {"success": True, "message": f"Lead '{lead.title}' converted to Opportunity Deal '{opp.title}'. View at [Opportunities Hub](/crm/opportunities/)."}

        elif conv_type == "quote_to_order":
            quote = Quote.objects.filter(title__icontains=identifier).first() or Quote.objects.filter(id__iexact=identifier).first()
            if not quote:
                return {"error": True, "message": f"Could not find a Quote matching '{identifier}'."}
            
            with transaction.atomic():
                quote.status = QuoteStatus.ACCEPTED
                quote.save()
                order = SalesOrder.objects.create(
                    title=f"Order: {quote.title}",
                    quote=quote,
                    company=quote.company,
                    contact=quote.contact,
                    status=OrderStatus.CONFIRMED,
                    ordered_at=timezone.now().date(),
                    assigned_to=quote.assigned_to or user
                )
                for item in quote.line_items.all():
                    SalesOrderLineItem.objects.create(
                        order=order, product=item.product, description=item.description,
                        quantity=item.quantity, unit_price=item.unit_price, discount=item.discount
                    )
            return {"success": True, "message": f"Quote '{quote.title}' converted to Confirmed Sales Order #{order.id}. View at [Orders Hub](/sales/orders/)."}

        elif conv_type == "order_to_invoice":
            if is_sales_rep(user):
                return {"error": True, "message": "Permission Denied: Invoicing is restricted to Accountants and Administrators."}
            order = SalesOrder.objects.filter(title__icontains=identifier).first() or SalesOrder.objects.filter(id__iexact=identifier).first()
            if not order:
                return {"error": True, "message": f"Could not find a Sales Order matching '{identifier}'."}
            
            today = timezone.now().date()
            inv_num = f"INV-{today.strftime('%Y%m')}-{order.id:04d}"
            with transaction.atomic():
                invoice = Invoice.objects.create(
                    invoice_number=inv_num, order=order, company=order.company,
                    contact=order.contact, issue_date=today, due_date=today + datetime.timedelta(days=30),
                    status=InvoiceStatus.SENT, assigned_to=user
                )
                for item in order.line_items.all():
                    InvoiceLineItem.objects.create(
                        invoice=invoice, product=item.product, description=item.description,
                        quantity=item.quantity, unit_price=item.unit_price, discount=item.discount
                    )
            return {"success": True, "message": f"Invoice **#{invoice.invoice_number}** created from Order '{order.title}'. [View & Print PDF](/invoices/{invoice.id}/)."}

    # 6. Query Insights (Role Filtered)
    elif tool_name == "get_crm_insights":
        if is_sales_rep(user):
            my_leads = Lead.objects.filter(assigned_to=user)
            my_opps = Opportunity.objects.filter(assigned_to=user)
            my_pipeline = sum(float(o.value) for o in my_opps if o.stage not in ['closed_won', 'closed_lost'])
            return {
                "role": user_role,
                "assigned_leads_count": my_leads.count(),
                "assigned_opportunities_count": my_opps.count(),
                "my_pipeline_value": my_pipeline,
                "note": "Metrics strictly filtered to your assigned accounts."
            }
        else:
            all_invoices = Invoice.objects.exclude(status=InvoiceStatus.CANCELLED)
            total_invoiced = sum(inv.subtotal for inv in all_invoices)
            total_collected = float(sum(p.amount for p in Payment.objects.all()))
            open_opps = Opportunity.objects.exclude(stage__in=['closed_won', 'closed_lost'])
            pipeline_val = sum(float(o.value) for o in open_opps)

            overdue_list = [
                {"invoice": inv.invoice_number, "company": inv.company.name if inv.company else "N/A", "due": inv.balance_due}
                for inv in all_invoices if inv.is_overdue
            ]

            return {
                "total_pipeline_value": pipeline_val,
                "total_invoiced": total_invoiced,
                "total_collected": total_collected,
                "outstanding_balance": total_invoiced - total_collected,
                "overdue_invoices": overdue_list
            }

    return {"error": True, "message": f"Unknown tool: {tool_name}"}


# ---------------------------------------------------------------------------
# Gemini Conversational Agent Caller
# ---------------------------------------------------------------------------

def run_ai_copilot(user_message: str, chat_history: list, user) -> tuple[str, list]:
    """
    Sends conversation + tool definitions to Gemini API.
    Handles tool calls with role verification and returns natural response.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    user_role = get_user_role(user)

    if not api_key:
        return (
            "⚠️ **Gemini API Key Missing**: Please set `GEMINI_API_KEY` in your environment variables to activate AI Copilot. Get a free key at https://aistudio.google.com/.",
            chat_history
        )

    system_instruction = f"""
You are the Agency CRM AI Copilot and Interactive Assistant.
You assist agency teams in creating records, executing workflows, managing billing, and guiding them through CRM features.

CURRENT USER CONTEXT:
- Username: {user.username}
- Role: {user_role} (Permissions: Admin={is_admin(user)}, SalesRep={is_sales_rep(user)}, Accountant={is_accountant(user)})

STRICT PERMISSION & SECURITY RULES:
1. USER CREATION: Only 'Admin' or 'Manager' roles can create new users/team members. If a Sales Rep or Accountant asks to create a user, politely refuse and state that only Administrators have this privilege.
2. FINANCIAL ACCESS: Sales Reps cannot view global company profit or all-team billing totals. They only see their assigned pipeline.
3. DATA MODIFICATION: Always execute actions via function tools.

CLARIFICATION & MISSING DETAILS PROTOCOL:
- If the user asks to create an item (Lead, Quote, Invoice) but omits critical parameters (such as company name, line item descriptions, quantities, or prices), DO NOT guess or create dummy values.
- Instead, respond conversationally asking for the specific missing information before triggering the tool.

USER MANUAL & PRODUCT GUIDE:
- When asked how something works (e.g. converting quotes, downloading PDF invoices, pipeline stages, user roles), provide clear, step-by-step instructions.
- Format responses nicely with markdown, bullet points, and bold highlights.
"""

    # Supported model identifiers in Google AI Studio v1beta API
    models_to_try = ["gemini-1.5-flash", "gemini-1.5-flash-latest", "gemini-1.5-pro", "gemini-2.0-flash-exp"]

    last_error = ""

    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"

        # Build contents payload
        contents = []
        for msg in chat_history[-6:]:  # keep last 6 turns
            contents.append({
                "role": "user" if msg["role"] == "user" else "model",
                "parts": [{"text": msg["content"]}]
            })
        contents.append({
            "role": "user",
            "parts": [{"text": user_message}]
        })

        payload = {
            "system_instruction": {
                "parts": [{"text": system_instruction}]
            },
            "contents": contents,
            "tools": [{"function_declarations": TOOLS_DEFINITION}],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 1000
            }
        }

        try:
            res = requests.post(url, json=payload, timeout=20)
            res_data = res.json()

            if "error" in res_data:
                last_error = res_data["error"].get("message", "API Error")
                continue

            candidates = res_data.get("candidates", [])
            if not candidates:
                continue

            content_obj = candidates[0].get("content", {})
            parts = content_obj.get("parts", [])

            # Check for function calls
            for part in parts:
                if "functionCall" in part:
                    func_call = part["functionCall"]
                    fn_name = func_call["name"]
                    fn_args = func_call.get("args", {})

                    # Execute tool
                    tool_result = execute_tool(fn_name, fn_args, user)

                    # Return direct clear message or follow-up
                    return tool_result.get("message", "Action completed."), chat_history

                elif "text" in part:
                    return part["text"], chat_history

        except Exception as e:
            last_error = str(e)
            continue

    if last_error:
        return f"⚠️ AI Assistant Response: {last_error}", chat_history

    return "⚠️ Could not connect to Gemini API. Please ensure your GEMINI_API_KEY is valid.", chat_history
