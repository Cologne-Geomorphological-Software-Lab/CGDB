"""Every upload of the CGDB apps lives in protected storage.

Field photos, raw measurement files, processed data, algorithms, micro-XRF
element maps and raster scenes belong to projects (or, for algorithms, to
the role-managed catalogue). Under MEDIA_ROOT a web server serving /media/
could hand them to anyone; in protected storage they reach a browser only
through the permission-checked view (prototype.protected_media).
"""

from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import FileField
from django.test import TestCase
from guardian.shortcuts import assign_perm

from analysis.models import MicroXRFElementMap, MicroXRFMeasurement, RawMeasurement
from field_data.models import FieldPhoto, Layer, Location, Sample
from laboratory.models import Device
from prototype.models import Project, Researcher
from prototype.protected_media import RULES
from prototype.storage import ProtectedFileSystemStorage
from prototype.tests.roles import give_role

_CGDB_APPS = [
    "prototype",
    "field_data",
    "analysis",
    "bibliography",
    "laboratory",
    "orchestration",
    "geodata",
    "raster_data",
]


class EveryUploadIsProtectedTest(TestCase):
    def test_every_file_field_uses_protected_storage_and_has_a_rule(self):
        problems = []
        for label in _CGDB_APPS:
            for model in apps.get_app_config(label).get_models():
                for field in model._meta.get_fields():
                    if not isinstance(field, FileField):
                        continue
                    where = f"{model._meta.label}.{field.name}"
                    if not isinstance(field.storage, ProtectedFileSystemStorage):
                        problems.append(f"{where}: not in protected storage")
                    rule = RULES.get(str(field.upload_to))
                    if rule is None:
                        problems.append(f"{where}: no rule for {field.upload_to!r}")
                    elif (rule.model, rule.field) != (
                        model._meta.label,
                        field.name,
                    ):
                        problems.append(f"{where}: rule points at {rule.model}")
        self.assertEqual(problems, [])


class ProtectedUploadAccessTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.project = Project.objects.create(title="P", label="P")
        cls.other = Project.objects.create(title="O", label="O")
        cls.location = Location.objects.create(
            identifier="PU-1", project=cls.project, data_source="internal"
        )
        cls.layer = Layer.objects.create(location=cls.location, identifier=1)
        cls.member = give_role(
            User.objects.create_user(
                username="pu_member", password="pw", is_staff=True
            ),
            "Viewer",
        )
        assign_perm("view_project", cls.member, cls.project)
        cls.outsider = give_role(
            User.objects.create_user(
                username="pu_outsider", password="pw", is_staff=True
            ),
            "Viewer",
        )
        assign_perm("view_project", cls.outsider, cls.other)

    def _assert_member_only(self, field_file):
        path = Path(field_file.path)
        self.assertTrue(
            path.is_relative_to(Path(settings.PROTECTED_MEDIA_ROOT).resolve())
        )
        url = field_file.url
        self.assertTrue(url.startswith("/files/"), url)
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(self.member)
        response = self.client.get(url)
        response.close()  # release the file handle (Windows locks open files)
        self.assertEqual(response.status_code, 200)

    def test_photo_of_a_location(self):
        photo = FieldPhoto.objects.create(
            content_object=self.location,
            file=SimpleUploadedFile("loc.jpg", b"jpeg"),
        )
        self._assert_member_only(photo.file)

    def test_photo_of_a_layer(self):
        photo = FieldPhoto.objects.create(
            content_object=self.layer,
            file=SimpleUploadedFile("layer.jpg", b"jpeg"),
        )
        self._assert_member_only(photo.file)

    def test_raw_measurement_file(self):
        raw = RawMeasurement.objects.create(
            project=self.project,
            device=Device.objects.create(name="PU device"),
            researcher=Researcher.objects.create(academic_rank="D", position="WiMa"),
            file=SimpleUploadedFile("raw.bin", b"raw"),
        )
        self._assert_member_only(raw.file)

    def test_micro_xrf_raster_path_points_into_protected_storage(self):
        sample = Sample.objects.create(
            identifier="PU-S", project=self.project, location=self.location
        )
        measurement = MicroXRFMeasurement.objects.create(sample=sample)
        element_map = MicroXRFElementMap.objects.create(
            measurement=measurement,
            element="Fe",
            raster_file=SimpleUploadedFile("fe.tif", b"tif"),
        )
        self.assertEqual(
            element_map.get_raster_path(), Path(element_map.raster_file.path)
        )
        self._assert_member_only(element_map.raster_file)
