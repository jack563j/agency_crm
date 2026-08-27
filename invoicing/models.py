"""
Invoicing app models.

Entities:
  Invoice         — a billing document issued to a client
  InvoiceLineItem — individual lines on an Invoice
  Payment         — a payment recorded against an Invoice
"""
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

from crm.models import Company, Contact
from sales.models import Product, SalesOrder

User = get_user_model()


# ---------------------------------------------------------------------------
# Choices
# ---------------------------------------------------------------------------

class InvoiceStatus(models.TextChoices):
    DRAFT     = "draft",     "Draft"
    SENT      = "sent",      "Sent"
    PAID      = "paid",      "Paid"
    OVERDUE   = "overdue",   "Overdue"
    CANCELLED = "cancelled", "Cancelled"


class PaymentMethod(models.TextChoices):
    BANK_TRANSFER = "bank_transfer", "Bank Transfer"
    CREDIT_CARD   = "credit_card",   "Credit Card"
    CASH          = "cash",          "Cash"
    CHEQUE        = "cheque",        "Cheque"
    OTHER         = "other",         "Other"


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# ---------------------------------------------------------------------------
# Invoice
# ---------------------------------------------------------------------------

class Invoice(TimeStampedModel):
    """A billing document sent to a client."""

    invoice_number = models.CharField(max_length=50, unique=True)
    order = models.ForeignKey(
        SalesOrder,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="invoices",
        help_text="Originating sales order (optional).",
    )
    contact = models.ForeignKey(
        Contact,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="invoices",
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="invoices",
    )
    status = models.CharField(
        max_length=20,
        choices=InvoiceStatus.choices,
        default=InvoiceStatus.DRAFT,
    )
    issue_date = models.DateField(null=True, blank=True)
    due_date   = models.DateField(null=True, blank=True)
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="invoices",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"INV-{self.invoice_number}"

    # ------------------------------------------------------------------
    # Computed financials
    # ------------------------------------------------------------------

    @property
    def subtotal(self) -> float:
        """Sum of all line item subtotals (before any invoice-level adjustments)."""
        return sum(item.subtotal for item in self.line_items.all())

    @property
    def amount_paid(self) -> float:
        """Total confirmed payments recorded against this invoice."""
        return sum(p.amount for p in self.payments.all())

    @property
    def balance_due(self) -> float:
        """Remaining unpaid balance."""
        return self.subtotal - self.amount_paid

    @property
    def is_overdue(self) -> bool:
        from django.utils import timezone
        if self.due_date and self.status not in (InvoiceStatus.PAID, InvoiceStatus.CANCELLED):
            return self.due_date < timezone.now().date()
        return False


# ---------------------------------------------------------------------------
# InvoiceLineItem
# ---------------------------------------------------------------------------

class InvoiceLineItem(TimeStampedModel):
    """A single billable line on an Invoice."""

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="line_items",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="invoice_lines",
    )
    description = models.CharField(max_length=255, blank=True)
    quantity    = models.PositiveIntegerField(default=1)
    unit_price  = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    discount = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Discount percentage (0–100).",
    )

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return self.description or (str(self.product) if self.product else f"Line {self.pk}")

    @property
    def subtotal(self) -> float:
        return float(self.unit_price) * self.quantity * (1 - float(self.discount) / 100)


# ---------------------------------------------------------------------------
# Payment
# ---------------------------------------------------------------------------

class Payment(TimeStampedModel):
    """A payment recorded against an Invoice."""

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="payments",
    )
    amount = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    payment_date = models.DateField()
    method       = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.BANK_TRANSFER,
    )
    reference = models.CharField(
        max_length=100, blank=True,
        help_text="Transaction ID or cheque number.",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-payment_date"]

    def __str__(self) -> str:
        return f"Payment of {self.amount} on {self.payment_date} [{self.get_method_display()}]"
