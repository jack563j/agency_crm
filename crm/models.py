"""
CRM data models.

Entities:
  Company      — an organisation (client or prospect)
  Contact      — a person linked to a Company
  Lead         — an inbound/outbound sales lead
  Opportunity  — a qualified sales opportunity derived from a Lead
"""
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

User = get_user_model()


# ---------------------------------------------------------------------------
# Choices
# ---------------------------------------------------------------------------

class LeadSource(models.TextChoices):
    WEBSITE     = "website",     "Website"
    REFERRAL    = "referral",    "Referral"
    COLD_CALL   = "cold_call",   "Cold Call"
    SOCIAL      = "social",      "Social Media"
    EVENT       = "event",       "Event"
    OTHER       = "other",       "Other"


class LeadStatus(models.TextChoices):
    NEW         = "new",         "New"
    CONTACTED   = "contacted",   "Contacted"
    QUALIFIED   = "qualified",   "Qualified"
    UNQUALIFIED = "unqualified", "Unqualified"
    CONVERTED   = "converted",   "Converted"


class OpportunityStage(models.TextChoices):
    PROSPECTING  = "prospecting",  "Prospecting"
    QUALIFICATION = "qualification", "Qualification"
    PROPOSAL     = "proposal",     "Proposal"
    NEGOTIATION  = "negotiation",  "Negotiation"
    CLOSED_WON   = "closed_won",   "Closed Won"
    CLOSED_LOST  = "closed_lost",  "Closed Lost"


# ---------------------------------------------------------------------------
# Base model
# ---------------------------------------------------------------------------

class TimeStampedModel(models.Model):
    """Abstract base that adds created_at / updated_at to every model."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# ---------------------------------------------------------------------------
# Company
# ---------------------------------------------------------------------------

class Company(TimeStampedModel):
    """An organisation — client, prospect, or partner."""

    name     = models.CharField(max_length=255)
    website  = models.URLField(blank=True)
    phone    = models.CharField(max_length=50, blank=True)
    email    = models.EmailField(blank=True)
    industry = models.CharField(max_length=100, blank=True)
    address  = models.TextField(blank=True)
    notes    = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "companies"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


# ---------------------------------------------------------------------------
# Contact
# ---------------------------------------------------------------------------

class Contact(TimeStampedModel):
    """A person associated with a Company."""

    first_name = models.CharField(max_length=100)
    last_name  = models.CharField(max_length=100)
    email      = models.EmailField(unique=True)
    phone      = models.CharField(max_length=50, blank=True)
    job_title  = models.CharField(max_length=150, blank=True)
    company    = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contacts",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


# ---------------------------------------------------------------------------
# Lead
# ---------------------------------------------------------------------------

class Lead(TimeStampedModel):
    """An inbound or outbound sales lead."""

    title   = models.CharField(max_length=255)
    contact = models.ForeignKey(
        Contact,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leads",
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leads",
    )
    source  = models.CharField(
        max_length=20,
        choices=LeadSource.choices,
        default=LeadSource.OTHER,
    )
    status  = models.CharField(
        max_length=20,
        choices=LeadStatus.choices,
        default=LeadStatus.NEW,
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leads",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title


# ---------------------------------------------------------------------------
# Opportunity
# ---------------------------------------------------------------------------

class Opportunity(TimeStampedModel):
    """A qualified sales opportunity, optionally originating from a Lead."""

    title   = models.CharField(max_length=255)
    lead    = models.ForeignKey(
        Lead,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="opportunities",
        help_text="The originating lead (optional).",
    )
    contact = models.ForeignKey(
        Contact,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="opportunities",
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="opportunities",
    )
    stage = models.CharField(
        max_length=20,
        choices=OpportunityStage.choices,
        default=OpportunityStage.PROSPECTING,
    )
    value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Estimated deal value.",
    )
    probability = models.PositiveSmallIntegerField(
        default=50,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Probability of closing (0–100 %).",
    )
    expected_close_date = models.DateField(null=True, blank=True)
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="opportunities",
    )
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "opportunities"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title

    @property
    def weighted_value(self) -> float:
        """value × probability / 100 — useful for pipeline reports."""
        return float(self.value) * self.probability / 100
