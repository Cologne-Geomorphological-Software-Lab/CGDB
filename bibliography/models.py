from django.contrib.auth.models import User
from django.db import models

from prototype.models import BaseModel, Project


class Author(BaseModel):
    """Represents an author of a publication.

    Attributes:
        last_name (str): The last name of the author.
        first_name (str): The first name of the author.
        user (User): The user associated with the author (if applicable).
    """

    last_name = models.CharField(max_length=50)
    first_name = models.CharField(max_length=50)
    user = models.ForeignKey(
        User,
        blank=True,
        null=True,
        on_delete=models.RESTRICT,
    )

    def __str__(self):
        """Returns a string representation of the author in the format "{last_name}, {first_name}"."""
        return f"{self.last_name}, {self.first_name}"


class ReferenceKeyword(BaseModel):
    keyword = models.CharField(max_length=250, unique=True)
    keyword_ger = models.CharField(
        max_length=250,
        blank=True,
        null=True,
    )

    def __str__(self):
        return f"{self.keyword}"


class Reference(BaseModel):
    """Represents a reference entry for a publication, thesis, or paper.

    Attributes:
        title (str): The title of the reference.
        year (int): The year of publication.
        lead_author (Author): The lead author of the reference.
        second_author (QuerySet): Additional authors of the reference.
        abstract (str): The abstract of the reference.
        journal (str): The journal where the reference is published.
        volume (int): The volume number of the journal.
        number (int): The issue number of the journal.
        pages (int): The page numbers of the reference.
        publisher (str): The publisher of the reference.
        type (str): The type of reference (e.g., Master's thesis, Bachelor's thesis, PhD thesis, Paper).
        project (Project): The project associated with the reference.
        doi (str): The Digital Object Identifier (DOI) of the reference.
        ISSN (int): The International Standard Serial Number (ISSN) of the journal.
        how_to_cite (str): Instructions on how to cite the reference.

    Methods:
        __str__: Returns a string representation of the reference in the format "{lead_author} ({year}): {title}".
    """

    title = models.CharField(max_length=250)
    year = models.IntegerField(
        blank=True,
        null=True,
    )
    published = models.BooleanField(
        blank=True,
        null=True,
    )
    parent_publication = models.ForeignKey(
        "self",
        on_delete=models.RESTRICT,
        blank=True,
        null=True,
    )
    lead_author = models.ForeignKey(
        Author,
        on_delete=models.RESTRICT,
        related_name="lead_author",
    )
    second_author = models.ManyToManyField(
        Author,
        related_name="second_author",
    )
    supervisor = models.ManyToManyField(
        Author,
        related_name="supervisor",
        blank=True,
    )
    abstract = models.TextField()
    journal = models.CharField(
        max_length=250,
        blank=True,
        null=True,
    )
    volume = models.IntegerField(
        blank=True,
        null=True,
    )
    number = models.IntegerField(
        blank=True,
        null=True,
    )
    pages = models.CharField(
        max_length=250,
        blank=True,
        null=True,
    )
    publisher = models.CharField(
        max_length=250,
        blank=True,
        null=True,
    )
    location_of_publication = models.CharField(
        max_length=250,
        blank=True,
        null=True,
    )
    CHOICES = [
        ("Monography", "Monography"),
        ("Master's thesis", "Master's thesis"),
        ("Bachelor's thesis", "Bachelor's thesis"),
        ("PhD thesis", "PhD thesis"),
        ("Paper", "Paper"),
        ("Chapter", "Chapter"),
        ("Collection", "Collection"),
    ]
    type = models.CharField(choices=CHOICES, max_length=20)
    project = models.ManyToManyField(
        Project,
        blank=True,
        help_text="Select a project, provided that a unique one can be assigned to the publication.",
    )
    doi = models.URLField(
        max_length=50,
        blank=True,
        null=True,
    )
    issn = models.IntegerField(
        blank=True,
        null=True,
        verbose_name="ISSN",
    )
    isbn_print = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="ISBN Print",
    )
    isbn_online = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="ISBN Online",
    )
    how_to_cite = models.CharField(
        max_length=350,
        blank=True,
        null=True,
    )
    keywords = models.ManyToManyField(
        ReferenceKeyword,
        blank=True,
    )

    class Meta:
        ordering = [
            "-year",
            "title",
        ]
        verbose_name = "Reference"
        verbose_name_plural = "References"

    def __str__(self):
        return f"{self.lead_author} ({self.year}): {self.title}"
