"""Core models for CGDB project.

This module contains the core models for the CGDB project:
- BaseModel: Abstract base model with common fields
- ResearchGroup: Represents a research group within the institution
- Researcher: Represents a researcher within the institution
- Project: Represents a research project within the institution

These models form the foundation for the entire CGDB system.

Author: Dennis Handy
Date: July 18, 2025 (consolidated from organisation app)
"""

from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.db import models
from guardian.models import UserObjectPermissionBase


class BaseModel(models.Model):
    """Abstract base model with common fields for all models."""

    created_at = models.DateTimeField(
        auto_now_add=True,
        blank=True,
        null=True,
        editable=False,
    )
    modified_at = models.DateTimeField(
        auto_now=True,
        blank=True,
        null=True,
        editable=False,
    )
    created_by = models.ForeignKey(
        User,
        related_name="%(class)s_created",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        editable=False,
    )
    updated_by = models.ForeignKey(
        User,
        related_name="%(class)s_updated",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        editable=False,
    )

    class Meta:
        abstract = True
        ordering = ["-modified_at", "-created_at"]


class ResearchGroup(BaseModel):
    """Represents a research group within the institution.

    Attributes:
        label (CharField): The name or label of the research group.
        head_of_group (ForeignKey): A reference to the head of the research group, a researcher.

    Methods:
        __str__(): Returns a human-readable representation of the research group.
    """

    label = models.CharField(max_length=100)
    head_of_group = models.ForeignKey(
        "Researcher",
        on_delete=models.SET_NULL,
        null=True,
        related_name="group_head",
    )
    auth_group = models.OneToOneField(
        Group,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
    )

    def __str__(self):
        """Returns a human-readable representation of the research group."""
        return f"{self.label}"


class Researcher(BaseModel):
    """Represents a researcher within the institution.

    Attributes:
        user (OneToOneField): A reference to the associated user profile.
        academic_rank (CharField): The academic rank of the researcher.
        position (CharField): The position or role of the researcher.
        research_groups (ManyToManyField): Research groups the researcher is affiliated with.
    Meta:
        verbose_name_plural = "Researchers"

    Methods:
        __str__(): Returns a human-readable representation of the researcher.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.RESTRICT,
    )
    ACADEMIC_RANK_CHOICES = [
        ("P", "Professor"),
        ("D", "Doctor"),
        ("M", "MSc"),
        ("B", "BSc"),
        ("S", "Student"),
        ("U", "unknown"),
    ]
    academic_rank = models.CharField(
        max_length=5,
        choices=ACADEMIC_RANK_CHOICES,
    )
    POSITION_CHOICES = [
        ("P", "Professor"),
        ("PhDS", "PhD student"),
        ("SHK", "Student Assistant"),
        ("WHB", "Research Assistant (Bachelor's degree)"),
        ("WHK", "Research Assistant"),
        ("WiMa", "Research Associate"),
        ("LH", "Head of Laboratory"),
        ("TM", "Technician"),
        ("EX", "External"),
    ]
    position = models.CharField(max_length=5, choices=POSITION_CHOICES)
    orcid = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name_plural = "Researchers"

    def __str__(self):
        """Returns a human-readable representation of the researcher."""
        return f"{self.user.last_name}, {self.user.first_name}"


class Project(BaseModel):
    """Represents a research project within the institution.

    Attributes:
        title (CharField): The full name of the research project.
        subtitle (CharField): Subtitle of the project (optional).
        label (CharField): A short label or identifier for the project.
        principal_investigator (ManyToManyField): researchers leading the project.
        research_group (ManyToManyField): Research groups associated with the project.
        parent (ForeignKey): Parent project (optional).
        start_date (DateField): The project's starting date (optional).
        deadline (DateField): The project's deadline (optional).
        description (TextField): A description of the research project (optional).
        status (CharField): Project status - FIXED: Was BooleanField(default=None)
        public (BooleanField): Indicates whether the project is public.

    Methods:
        __str__(): Returns a human-readable representation of the research project.
    """

    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=200, blank=True, null=True)
    label = models.CharField(max_length=50)
    principal_investigator = models.ManyToManyField(Researcher)
    associated_investigator = models.ManyToManyField(
        Researcher,
        related_name="associated_investigator",
        blank=True,
    )
    research_group = models.ManyToManyField(ResearchGroup)
    parent = models.ForeignKey(
        "Project",
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
    )
    start_date = models.DateField(
        blank=True,
        null=True,
    )
    deadline = models.DateField(
        blank=True,
        null=True,
    )
    description = models.TextField(
        blank=True,
        null=True,
    )

    STATUS_CHOICES = [
        ("ACTIVE", "Active"),
        ("COMPLETED", "Completed"),
        ("PAUSED", "Paused"),
        ("CANCELLED", "Cancelled"),
    ]

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="ACTIVE",
        help_text="Current status of the project",
    )

    public = models.BooleanField(
        default=False,
        help_text="Is the project currently public?",
    )

    def clean(self):
        if self.principal_investigator.exists() and self.associated_investigator.exists():
            if (self.principal_investigator.all() & self.associated_investigator.all()).exists():
                raise ValidationError(
                    "A researcher cannot be both a principal investigator and an associated investigator.",
                )

    def __str__(self):
        """Returns a human-readable representation of the research project."""
        return str(self.label)


class ProjectUserObjectPermission(UserObjectPermissionBase):
    """User object permissions for Project model."""

    content_object = models.ForeignKey(Project, on_delete=models.CASCADE)
