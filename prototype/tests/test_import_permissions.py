"""Tests that admin table imports follow the same project rules as the forms.

Exercises the real admin views: upload, preview and confirm. Each role is set
up the way production uses them: one academic group for the model-level
permissions, plus guardian permissions on individual projects.
"""

import csv
import io

import tablib
from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from guardian.shortcuts import assign_perm

from analysis.admin import (
    GrainSizeAdmin,
    LuminescenceDatingAdmin,
    RadiocarbonDatingAdmin,
)
from analysis.models import GrainSize, LuminescenceDating, RadiocarbonDating
from analysis.resources import (
    GrainSizeResource,
    LuminescenceDatingResource,
    RadiocarbonDatingResource,
)
from field_data.admin import SiteAdmin
from field_data.models import Location, Sample, Site, StudyArea
from field_data.resources import LocationResource, SiteResource
from prototype.models import Project
from prototype.permissions import create_permission_groups

LOCATION_COLUMNS = ["id", "project", "identifier", "easting", "northing", "srid"]


def _csv(columns, rows):
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode()


class _ImportTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        # post_migrate fills the groups before every app's permissions exist
        # on a fresh database, as the test database is.
        create_permission_groups()
        cls.project_a = Project.objects.create(
            title="Project A", label="A", status="ACTIVE"
        )
        cls.project_b = Project.objects.create(
            title="Project B", label="B", status="ACTIVE"
        )
        cls.superuser = User.objects.create_superuser(
            username="imp_super", password="pw", email="s@test.com"
        )
        cls.researcher = cls._user("imp_researcher", "Researcher")
        for perm in ("view_project", "add_project", "change_project"):
            assign_perm(perm, cls.researcher, cls.project_a)
        cls.viewer = cls._user("imp_viewer", "Viewer")
        assign_perm("view_project", cls.viewer, cls.project_a)
        cls.outsider = cls._user("imp_outsider", "Viewer")
        assign_perm("view_project", cls.outsider, cls.project_b)

        cls.location_a = Location.objects.create(
            identifier="LOC-A", project=cls.project_a, data_source="internal"
        )
        cls.location_b = Location.objects.create(
            identifier="LOC-B", project=cls.project_b, data_source="internal"
        )

    @classmethod
    def _user(cls, name, group):
        user = User.objects.create_user(
            username=name, password="pw", is_staff=True
        )
        user.groups.add(Group.objects.get(name=group))
        return user

    def _url(self, model, view):
        app_label = model._meta.app_label
        model_name = model._meta.model_name
        return reverse(f"admin:{app_label}_{model_name}_{view}")

    def _upload(self, user, model, content):
        """POST a CSV to the import view and return the preview response."""
        self.client.force_login(user)
        url = self._url(model, "import")
        page = self.client.get(url)
        self.assertEqual(page.status_code, 200)
        choices = page.context["form"].fields["format"].choices
        value = next(v for v, label in choices if label == "csv")
        return self.client.post(
            url,
            {
                "format": value,
                "import_file": SimpleUploadedFile("data.csv", content),
            },
        )

    def _import(self, user, model, content):
        """Run preview and, if it offers one, the confirm step."""
        response = self._upload(user, model, content)
        form = response.context.get("confirm_form")
        if form is None:
            return False
        confirmed = self.client.post(
            self._url(model, "process_import"), dict(form.initial)
        )
        self.assertEqual(confirmed.status_code, 302)
        return True

    def _location_row(self, project, identifier="NEW", **extra):
        return {
            "project": project.pk,
            "identifier": identifier,
            "easting": "20",
            "northing": "45",
            "srid": "4326",
            **extra,
        }


class ImportAccessTests(_ImportTestCase):
    def test_viewer_cannot_open_import(self):
        self.client.force_login(self.viewer)
        response = self.client.get(self._url(Location, "import"))
        self.assertEqual(response.status_code, 403)

    def test_viewer_cannot_post_import(self):
        self.client.force_login(self.viewer)
        response = self.client.post(
            self._url(Location, "import"),
            {
                "format": "0",
                "import_file": SimpleUploadedFile(
                    "data.csv",
                    _csv(
                        LOCATION_COLUMNS,
                        [self._location_row(self.project_a)],
                    ),
                ),
            },
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Location.objects.filter(identifier="NEW").exists())

    def test_viewer_cannot_post_process_import(self):
        self.client.force_login(self.viewer)
        response = self.client.post(self._url(Location, "process_import"), {})
        self.assertEqual(response.status_code, 403)

    def test_viewer_does_not_see_import_button(self):
        self.client.force_login(self.viewer)
        response = self.client.get(self._url(Location, "changelist"))
        self.assertNotContains(response, self._url(Location, "import"))

    def test_researcher_sees_import_button(self):
        self.client.force_login(self.researcher)
        response = self.client.get(self._url(Location, "changelist"))
        self.assertContains(response, self._url(Location, "import"))

    def test_viewer_can_still_export(self):
        self.client.force_login(self.viewer)
        response = self.client.get(self._url(Location, "export"))
        self.assertEqual(response.status_code, 200)

    def test_shared_lookups_need_the_model_permission(self):
        from field_data.models import Country

        self.client.force_login(self.researcher)
        response = self.client.get(self._url(Country, "import"))
        self.assertEqual(response.status_code, 403)
        self.client.force_login(self.superuser)
        response = self.client.get(self._url(Country, "import"))
        self.assertEqual(response.status_code, 200)


class LocationImportRowTests(_ImportTestCase):
    def test_researcher_creates_row_in_own_project(self):
        content = _csv(
            LOCATION_COLUMNS, [self._location_row(self.project_a)]
        )
        self.assertTrue(self._import(self.researcher, Location, content))
        created = Location.objects.get(identifier="NEW")
        self.assertEqual(created.project, self.project_a)

    def test_researcher_cannot_create_row_in_foreign_project(self):
        content = _csv(
            LOCATION_COLUMNS, [self._location_row(self.project_b)]
        )
        self.assertFalse(self._import(self.researcher, Location, content))
        self.assertFalse(Location.objects.filter(identifier="NEW").exists())

    def test_researcher_updates_row_in_own_project(self):
        content = _csv(
            LOCATION_COLUMNS,
            [
                self._location_row(
                    self.project_a, "RENAMED", id=self.location_a.pk
                )
            ],
        )
        self.assertTrue(self._import(self.researcher, Location, content))
        self.location_a.refresh_from_db()
        self.assertEqual(self.location_a.identifier, "RENAMED")

    def test_researcher_cannot_update_row_in_foreign_project(self):
        content = _csv(
            LOCATION_COLUMNS,
            [
                self._location_row(
                    self.project_b, "STOLEN", id=self.location_b.pk
                )
            ],
        )
        self.assertFalse(self._import(self.researcher, Location, content))
        self.location_b.refresh_from_db()
        self.assertEqual(self.location_b.identifier, "LOC-B")

    def test_researcher_cannot_pull_foreign_row_into_own_project(self):
        content = _csv(
            LOCATION_COLUMNS,
            [
                self._location_row(
                    self.project_a, "PULLED", id=self.location_b.pk
                )
            ],
        )
        self.assertFalse(self._import(self.researcher, Location, content))
        self.location_b.refresh_from_db()
        self.assertEqual(self.location_b.project, self.project_b)

    def test_researcher_cannot_push_own_row_into_foreign_project(self):
        content = _csv(
            LOCATION_COLUMNS,
            [
                self._location_row(
                    self.project_b, "PUSHED", id=self.location_a.pk
                )
            ],
        )
        self.assertFalse(self._import(self.researcher, Location, content))
        self.location_a.refresh_from_db()
        self.assertEqual(self.location_a.project, self.project_a)

    def test_refusal_does_not_reveal_the_foreign_row(self):
        content = _csv(
            LOCATION_COLUMNS,
            [
                self._location_row(
                    self.project_b, "STOLEN", id=self.location_b.pk
                )
            ],
        )
        response = self._upload(self.researcher, Location, content)
        self.assertNotContains(response, "LOC-B")

    def test_researcher_cannot_change_literature_row(self):
        literature = Location.objects.create(
            identifier="LIT", project=self.project_a, data_source="internal"
        )
        # update() skips save()'s check for a reference, which isn't relevant.
        Location.objects.filter(pk=literature.pk).update(
            data_source="literature"
        )
        content = _csv(
            LOCATION_COLUMNS,
            [
                self._location_row(
                    self.project_a, "CHANGED", id=literature.pk
                )
            ],
        )
        self.assertFalse(self._import(self.researcher, Location, content))
        literature.refresh_from_db()
        self.assertEqual(literature.identifier, "LIT")

    def test_one_refused_row_blocks_the_whole_file(self):
        content = _csv(
            LOCATION_COLUMNS,
            [
                self._location_row(self.project_a, "OK-1"),
                self._location_row(self.project_b, "BAD-1"),
            ],
        )
        self.assertFalse(self._import(self.researcher, Location, content))
        self.assertFalse(Location.objects.filter(identifier="OK-1").exists())

    def test_superuser_may_import_into_any_project(self):
        content = _csv(
            LOCATION_COLUMNS, [self._location_row(self.project_b)]
        )
        self.assertTrue(self._import(self.superuser, Location, content))
        self.assertTrue(Location.objects.filter(identifier="NEW").exists())

    def test_real_import_is_refused_as_well_as_the_preview(self):
        """The confirm step runs the import again with dry_run=False."""
        dataset = tablib.Dataset(headers=LOCATION_COLUMNS)
        dataset.append(
            [
                self.location_b.pk,
                self.project_b.pk,
                "STOLEN",
                "20",
                "45",
                "4326",
            ]
        )
        result = LocationResource().import_data(
            dataset, dry_run=False, raise_errors=False, user=self.researcher
        )
        self.assertTrue(result.has_errors())
        self.location_b.refresh_from_db()
        self.assertEqual(self.location_b.identifier, "LOC-B")

    def test_import_without_a_user_is_not_restricted(self):
        """Scripts and management commands have no request user."""
        dataset = tablib.Dataset(headers=LOCATION_COLUMNS)
        dataset.append(
            ["", self.project_b.pk, "SCRIPTED", "20", "45", "4326"]
        )
        result = LocationResource().import_data(dataset, raise_errors=True)
        self.assertFalse(result.has_errors())
        self.assertTrue(
            Location.objects.filter(identifier="SCRIPTED").exists()
        )


class NestedImportRowTests(_ImportTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.sample_a = Sample.objects.create(
            identifier="S-A", project=cls.project_a, location=cls.location_a
        )
        cls.sample_b = Sample.objects.create(
            identifier="S-B", project=cls.project_b, location=cls.location_b
        )
        cls.area_a = StudyArea.objects.create(
            label="AREA-A", project=cls.project_a
        )
        cls.area_b = StudyArea.objects.create(
            label="AREA-B", project=cls.project_b
        )

    MEASUREMENTS = (
        (
            RadiocarbonDating,
            ["sample", "lab", "lab_id", "data_quality"],
            {"lab": "Poz", "lab_id": "X-1", "data_quality": "pending"},
        ),
        (
            LuminescenceDating,
            ["sample", "laboratory_id"],
            {"laboratory_id": "X-1"},
        ),
        (GrainSize, ["sample", "method"], {"method": "L"}),
    )

    def test_measurement_in_own_project(self):
        for model, columns, values in self.MEASUREMENTS:
            with self.subTest(model=model.__name__):
                content = _csv(columns, [{"sample": "S-A", **values}])
                self.assertTrue(self._import(self.researcher, model, content))
                self.assertEqual(
                    model.objects.filter(sample=self.sample_a).count(), 1
                )

    def test_measurement_on_foreign_sample_is_refused(self):
        for model, columns, values in self.MEASUREMENTS:
            with self.subTest(model=model.__name__):
                content = _csv(columns, [{"sample": "S-B", **values}])
                self.assertFalse(
                    self._import(self.researcher, model, content)
                )
                self.assertFalse(
                    model.objects.filter(sample=self.sample_b).exists()
                )

    def test_existing_foreign_measurement_cannot_be_changed(self):
        measurement = RadiocarbonDating.objects.create(
            sample=self.sample_b, lab_id="ORIGINAL"
        )
        content = _csv(
            ["id", "sample", "lab_id"],
            [{"id": measurement.pk, "sample": "S-A", "lab_id": "CHANGED"}],
        )
        self.assertFalse(
            self._import(self.researcher, RadiocarbonDating, content)
        )
        measurement.refresh_from_db()
        self.assertEqual(measurement.lab_id, "ORIGINAL")
        self.assertEqual(measurement.sample, self.sample_b)

    def test_site_in_own_project(self):
        content = _csv(
            ["label", "study_area"],
            [{"label": "SITE", "study_area": "AREA-A"}],
        )
        self.assertTrue(self._import(self.researcher, Site, content))
        self.assertTrue(Site.objects.filter(label="SITE").exists())

    def test_site_in_foreign_project_is_refused(self):
        content = _csv(
            ["label", "study_area"],
            [{"label": "SITE", "study_area": "AREA-B"}],
        )
        self.assertFalse(self._import(self.researcher, Site, content))
        self.assertFalse(Site.objects.filter(label="SITE").exists())

    def test_resources_use_the_same_project_path_as_their_admin(self):
        for resource, admin_class in (
            (RadiocarbonDatingResource, RadiocarbonDatingAdmin),
            (LuminescenceDatingResource, LuminescenceDatingAdmin),
            (GrainSizeResource, GrainSizeAdmin),
            (SiteResource, SiteAdmin),
        ):
            with self.subTest(resource=resource.__name__):
                self.assertEqual(
                    resource.project_path, admin_class.project_path
                )


class ExportScopeTests(_ImportTestCase):
    def test_export_contains_only_accessible_rows(self):
        self.client.force_login(self.viewer)
        url = self._url(Location, "export")
        form = self.client.get(url).context["form"]
        value = next(
            v for v, label in form.fields["format"].choices if label == "csv"
        )
        data = {"format": value}
        data.update(
            {
                name: "on"
                for name in form.fields
                if name.startswith("locationresource_")
            }
        )
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("LOC-A", body)
        self.assertNotIn("LOC-B", body)
