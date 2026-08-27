"""
Sales app models.

Entities:
  Product           — a sellable product or service
  Quote             — a price proposal sent to a prospect
  QuoteLineItem     — individual lines on a Quote
  SalesOrder        — a confirmed order (may originate from a Quote)
  SalesOrderLineItem— individual lines on a SalesOrder
"""
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

from crm.models import Company, Contact, Opportunity

User = get_user_model()


# ---------------------------------------------------------------------------
# Choices
# ---------------------------------------------------------------------------

class QuoteStatus(models.TextChoices):
    DRAFT    = "draft",    "Draft"
    SENT     = "sent",     "Sent"
    ACCEPTED = "accepted", "Accepted"
    REJECTED = "rejected", "Rejected"
    EXPIRED  = "expired",  "Expired"


class OrderStatus(models.TextChoices):
    PENDING   = "pending",   "Pending"
    CONFIRMED = "confirmed", "Confirmed"
    SHIPPED   = "shipped",   "Shipped"
    DELIVERED = "delivered", "Delivered"
    CANCELLED = "cancelled", "Cancelled"


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------

class Product(TimeStampedModel):
    """A product or service that can appear on quotes and orders."""

    name        = models.CharField(max_length=255)
    sku         = models.CharField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True)
    unit_price  = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.sku})" if self.sku else self.name


# ---------------------------------------------------------------------------
# Quote
# ---------------------------------------------------------------------------

class Quote(TimeStampedModel):
    """A price proposal sent to a prospect or client."""

    title       = models.CharField(max_length=255)
    opportunity = models.ForeignKey(
        Opportunity,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="quotes",
    )
    contact = models.ForeignKey(
        Contact,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="quotes",
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="quotes",
    )
    status = models.CharField(
        max_length=20,
        choices=QuoteStatus.choices,
        default=QuoteStatus.DRAFT,
    )
    valid_until = models.DateField(null=True, blank=True)
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="quotes",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title

    @property
    def total(self) -> float:
        return sum(item.subtotal for item in self.line_items.all())


# ---------------------------------------------------------------------------
# QuoteLineItem
# ---------------------------------------------------------------------------

class QuoteLineItem(TimeStampedModel):
    """A single line on a Quote."""

    quote = models.ForeignKey(
        Quote,
        on_delete=models.CASCADE,
        related_name="line_items",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="quote_lines",
    )
    # Free-text description overrides product name for custom items
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
# SalesOrder
# ---------------------------------------------------------------------------

class SalesOrder(TimeStampedModel):
    """A confirmed sales order, optionally converted from a Quote."""

    title   = models.CharField(max_length=255)
    quote   = models.ForeignKey(
        Quote,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="orders",
        help_text="Originating quote (optional).",
    )
    contact = models.ForeignKey(
        Contact,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="orders",
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="orders",
    )
    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING,
    )
    ordered_at  = models.DateField(null=True, blank=True)
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="orders",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title

    @property
    def total(self) -> float:
        return sum(item.subtotal for item in self.line_items.all())


# ---------------------------------------------------------------------------
# SalesOrderLineItem
# ---------------------------------------------------------------------------

class SalesOrderLineItem(TimeStampedModel):
    """A single line on a SalesOrder."""

    order = models.ForeignKey(
        SalesOrder,
        on_delete=models.CASCADE,
        related_name="line_items",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="order_lines",
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
