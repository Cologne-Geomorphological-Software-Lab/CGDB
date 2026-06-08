"""Tests for bibliography models.

Covers: Author.__str__, ReferenceKeyword.__str__, Reference.__str__,
ordering, parent_publication self-reference, M2M relations.
"""
from django.db.models import RestrictedError
from django.test import TestCase

from bibliography.models import Author, Reference, ReferenceKeyword
from prototype.models import Project


class _BibliographySetup(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = Author.objects.create(last_name="Müller", first_name="Hans")
        cls.second_author = Author.objects.create(last_name="Schmidt", first_name="Eva")
        cls.keyword = ReferenceKeyword.objects.create(keyword="loess")
        cls.reference = Reference.objects.create(
            title="Löss und Paläoböden",
            year=2020,
            lead_author=cls.author,
            abstract="Ein Abstract über Löss.",
            type="Paper",
        )
        cls.reference.second_author.add(cls.second_author)
        cls.reference.keywords.add(cls.keyword)


# ===========================================================================
# Author
# ===========================================================================


class AuthorStrTest(_BibliographySetup):

    def test_str_format(self):
        self.assertEqual(str(self.author), "Müller, Hans")

    def test_str_with_empty_first_name(self):
        a = Author(last_name="Doe", first_name="")
        self.assertEqual(str(a), "Doe, ")

    def test_str_with_umlauts(self):
        a = Author(last_name="Schäfer", first_name="Jörg")
        self.assertEqual(str(a), "Schäfer, Jörg")


# ===========================================================================
# ReferenceKeyword
# ===========================================================================


class ReferenceKeywordStrTest(_BibliographySetup):

    def test_str_returns_keyword(self):
        self.assertEqual(str(self.keyword), "loess")

    def test_str_with_special_chars(self):
        kw = ReferenceKeyword(keyword="grain-size")
        self.assertEqual(str(kw), "grain-size")


# ===========================================================================
# Reference.__str__
# ===========================================================================


class ReferenceStrTest(_BibliographySetup):

    def test_str_format(self):
        expected = "Müller, Hans (2020): Löss und Paläoböden"
        self.assertEqual(str(self.reference), expected)

    def test_str_with_none_year(self):
        ref = Reference(
            title="Kein Jahr",
            year=None,
            lead_author=self.author,
            abstract="x",
            type="Paper",
        )
        result = str(ref)
        self.assertIn("Müller, Hans", result)
        self.assertIn("None", result)
        self.assertIn("Kein Jahr", result)


# ===========================================================================
# Reference ordering
# ===========================================================================


class ReferenceOrderingTest(_BibliographySetup):

    def test_ordering_by_year_descending(self):
        Reference.objects.create(
            title="Alte Arbeit", year=2015, lead_author=self.author,
            abstract="x", type="Paper",
        )
        Reference.objects.create(
            title="Neuere Arbeit", year=2022, lead_author=self.author,
            abstract="x", type="Paper",
        )
        first = Reference.objects.all()[0]
        self.assertEqual(first.year, 2022)

    def test_ordering_secondary_by_title(self):
        Reference.objects.create(
            title="B-Titel", year=2018, lead_author=self.author,
            abstract="x", type="Paper",
        )
        Reference.objects.create(
            title="A-Titel", year=2018, lead_author=self.author,
            abstract="x", type="Paper",
        )
        same_year = Reference.objects.filter(year=2018).order_by("year", "title")
        self.assertEqual(same_year[0].title, "A-Titel")


# ===========================================================================
# Reference – parent_publication & M2M
# ===========================================================================


class ReferenceRelationsTest(_BibliographySetup):

    def test_parent_publication_self_reference(self):
        book = Reference.objects.create(
            title="Sammelband", year=2019, lead_author=self.author,
            abstract="x", type="Collection",
        )
        chapter = Reference.objects.create(
            title="Kapitel 1", year=2019, lead_author=self.second_author,
            abstract="x", type="Chapter", parent_publication=book,
        )
        self.assertEqual(chapter.parent_publication, book)

    def test_parent_publication_restrict_prevents_deletion(self):
        book = Reference.objects.create(
            title="Geschütztes Buch", year=2021, lead_author=self.author,
            abstract="x", type="Collection",
        )
        Reference.objects.create(
            title="Abhängiges Kapitel", year=2021, lead_author=self.author,
            abstract="x", type="Chapter", parent_publication=book,
        )
        with self.assertRaises(RestrictedError):
            book.delete()

    def test_choices_contain_all_types(self):
        choice_keys = [c[0] for c in Reference._meta.get_field("type").choices]
        for expected in ("Paper", "Chapter", "Collection", "Monography",
                         "Master's thesis", "Bachelor's thesis", "PhD thesis"):
            self.assertIn(expected, choice_keys)

    def test_many_to_many_second_author(self):
        self.assertEqual(self.reference.second_author.count(), 1)
        self.assertIn(self.second_author, self.reference.second_author.all())

    def test_keywords_many_to_many(self):
        self.assertTrue(
            self.reference.keywords.filter(keyword="loess").exists()
        )
