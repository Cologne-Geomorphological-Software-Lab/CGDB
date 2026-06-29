"""Tests for field_data forms."""

from django.test import TestCase

from field_data.forms import (
    CampaignForm,
    LayerForm,
    LocationForm,
    SampleForm,
    StudyAreaForm,
    TagForm,
)
from prototype.models import Project


class CampaignFormTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.project = Project.objects.create(
            title="Form Test Project", label="FTP01", status="ACTIVE"
        )

    def test_init_without_project_id(self):
        form = CampaignForm()
        self.assertIsNotNone(form.helper)
        self.assertNotIn("project", form.initial)

    def test_init_with_valid_project_id(self):
        form = CampaignForm(project_id=self.project.pk)
        self.assertEqual(form.initial["project"], self.project)

    def test_init_with_invalid_project_id(self):
        form = CampaignForm(project_id=999999)
        self.assertNotIn("project", form.initial)


class LocationFormTest(TestCase):
    def test_init_creates_helper(self):
        form = LocationForm()
        self.assertIsNotNone(form.helper)

    def test_processor_field_readonly(self):
        form = LocationForm()
        self.assertEqual(
            form.fields["processor"].widget.attrs.get("readonly"), True
        )


class StudyAreaFormTest(TestCase):
    def test_init_creates_helper_with_layout(self):
        form = StudyAreaForm()
        self.assertIsNotNone(form.helper)
        self.assertIsNotNone(form.helper.layout)


class SampleFormTest(TestCase):
    def test_init_without_location(self):
        form = SampleForm()
        self.assertIsNotNone(form.helper)
        self.assertNotIn("location", form.initial)

    def test_init_with_location(self):
        sentinel = object()
        form = SampleForm(location=sentinel)
        self.assertIs(form.initial["location"], sentinel)
        self.assertEqual(
            form.fields["location"].widget.attrs.get("readonly"), True
        )


class TagFormTest(TestCase):
    def test_init_creates_helper(self):
        form = TagForm()
        self.assertIsNotNone(form.helper)


class LayerFormTest(TestCase):
    def test_init_creates_helper(self):
        form = LayerForm()
        self.assertIsNotNone(form.helper)
