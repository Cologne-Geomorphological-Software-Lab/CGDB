"""Tests for the sample tabs in prototype/unfold_settings.py.

The tab bar that links a sample to its measurements must only appear when
the request belongs to one sample. On the sample add form it used to link
to the global measurement lists, which lost the form's entries (#271).
"""

import re

from django.contrib import admin as django_admin
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from django.urls import reverse
from unfold.sites import UnfoldAdminSite

from field_data.models import Location, Sample
from prototype.models import Project

_TABS_NAV = re.compile(r'<nav id="tabs-items".*?</nav>', re.DOTALL)


class SampleTabsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            "tabs_admin", "tabs@test.com", "pw"
        )
        cls.project = Project.objects.create(
            title="Tabs Project", label="TAB01", status="ACTIVE"
        )
        location = Location.objects.create(
            identifier="TAB_LOC", data_source="internal", project=cls.project
        )
        cls.sample = Sample.objects.create(
            identifier="TAB_S01", project=cls.project, location=location
        )

    def _tabs_for(self, path: str) -> list[dict]:
        site = django_admin.site
        assert isinstance(site, UnfoldAdminSite)
        request = RequestFactory().get(path)
        request.user = self.superuser
        (tab,) = site.get_tabs_list(request)
        return tab["items"]

    def test_no_tabs_without_a_sample(self):
        items = self._tabs_for(reverse("admin:field_data_sample_add"))
        self.assertEqual(len(items), 8)
        self.assertFalse(any(item["has_permission"] for item in items))

    def test_no_tabs_on_a_global_measurement_list(self):
        items = self._tabs_for(reverse("admin:analysis_grainsize_changelist"))
        self.assertFalse(any(item["has_permission"] for item in items))

    def test_tabs_on_an_existing_sample(self):
        items = self._tabs_for(
            reverse("admin:field_data_sample_change", args=[self.sample.pk])
        )
        self.assertTrue(all(item["has_permission"] for item in items))
        grain_size = next(i for i in items if "Grain" in str(i["title"]))
        self.assertEqual(
            str(grain_size["link_callback"]),
            reverse("admin:field_data_sample_grainsize", args=[self.sample.pk]),
        )

    def test_add_form_renders_no_measurement_links(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse("admin:field_data_sample_add"))
        self.assertEqual(response.status_code, 200)
        nav = _TABS_NAV.search(response.content.decode())
        nav_html = nav.group(0) if nav else ""
        self.assertNotIn(
            reverse("admin:analysis_grainsize_changelist"), nav_html
        )

    def test_change_form_renders_sample_scoped_links(self):
        self.client.force_login(self.superuser)
        response = self.client.get(
            reverse("admin:field_data_sample_change", args=[self.sample.pk])
        )
        self.assertEqual(response.status_code, 200)
        nav = _TABS_NAV.search(response.content.decode())
        assert nav is not None
        self.assertIn(
            reverse("admin:field_data_sample_grainsize", args=[self.sample.pk]),
            nav.group(0),
        )
