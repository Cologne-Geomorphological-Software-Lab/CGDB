import os
from decimal import Decimal
from pathlib import Path

from django.contrib.auth.models import Group, User
from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.geos import MultiLineString, Point, Polygon
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from analysis.models import Algorithm, RawMeasurement
from field_data.models import (
    Campaign,
    Country,
    ExposureType,
    Layer,
    Location,
    Province,
    Sample,
    SampleType,
    Site,
    StudyArea,
    Tag,
    Transect,
)
from laboratory.models import Accessory, Device
from prototype.models import Project, Researcher, ResearchGroup


class AlgorithmTestCase(TestCase):
    def setUp(self):
        test_file = SimpleUploadedFile("test_files/test.txt", b"file_content", content_type="text/plain")
        Algorithm.objects.create(
            name="Dijkstra",
            version="1.0",
            description="The Dijkstra algorithm calculates the shortest paths in an edge-weighted graph.",
            file=test_file,
            programming_language="Python",
        ),

    def test_algorithm_file_upload(self):
        dijkstra = Algorithm.objects.get(name="Dijkstra")
        self.assertTrue(dijkstra.file.name.startswith("analysis/algorithms/test"))

    def test_algorithm_fields(self):
        algorithm = Algorithm.objects.get(name="Dijkstra")
        self.assertEqual(algorithm.name, "Dijkstra")
        self.assertEqual(algorithm.version, "1.0")
        self.assertEqual(algorithm.programming_language, "Python")
        self.assertEqual(
            algorithm.description,
            "The Dijkstra algorithm calculates the shortest paths in an edge-weighted graph.",
        )
        self.assertTrue(algorithm.file)


class RawMeasurementModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="testuser",
            first_name="Test",
            last_name="Researcher",
            email="test.researcher@example.com",
        )
        cls.researcher = Researcher.objects.create(user=cls.user, academic_rank="P", position="P")

        cls.auth_group = Group.objects.create(name="Test Auth Group")

        cls.research_group = ResearchGroup.objects.create(
            label="Test Research Group", head_of_group=cls.researcher, auth_group=cls.auth_group
        )

        cls.project = Project.objects.create(
            title="Test Project", label="TP001", status="ACTIVE", public=True
        )
        cls.project.principal_investigator.add(cls.researcher)
        cls.project.research_group.add(cls.research_group)

        cls.sample_content_type = ContentType.objects.get_for_model(Sample)

        cls.tag = Tag.objects.create(
            content_type=cls.sample_content_type, word="Test Tag", slug="test-tag", project=cls.project
        )

        cls.sample_type = SampleType.objects.create(word="Test Sample Type", label="TST")

        cls.country = Country.objects.create(name="Test Country", iso_code="TC")
        cls.province = Province.objects.create(name="Test Province", country=cls.country)

        cls.study_area = StudyArea.objects.create(
            label="Test Study Area",
            project=cls.project,
            province=cls.province,
            climate_koeppen="Cfb",
            ecozone_schultz="MHU",
        )

        cls.site = Site.objects.create(label="Test Site", study_area=cls.study_area)
        cls.site.tags.add(cls.tag)

        cls.campaign = Campaign.objects.create(
            label="Test Campaign",
            project=cls.project,
            date_start="2023-01-01",
            date_end="2023-01-31",
            destination_country=cls.country,
            season="SU",
        )
        cls.campaign.study_areas.add(cls.study_area)

        cls.transect = Transect.objects.create(
            identifier="Test Transect",
            study_area=cls.study_area,
            campaign=cls.campaign,
            description="Test Transect Description",
        )

        cls.exposure_type = ExposureType.objects.create(
            main_type="O",
            abbreviation="OUT",
            name_ger="Aufschluss",
            name_en="Outcrop",
        )

        cls.location = Location.objects.create(
            data_source="internal",
            campaign=cls.campaign,
            identifier="LOC001",
            project=cls.project,
            date_of_record="2023-01-15",
            easting=8.5,
            northing=50.0,
            srid=4326,
            altitude=100.0,
            study_site=cls.site,
            transect=cls.transect,
            processor=cls.researcher,
            exposure_type=cls.exposure_type,
            liner=False,
            sampling=True,
            gradient_upslope=5.0,
            gradient_downslope=3.0,
            slope_aspect=180,
            relief_description="Flat terrain",
            current_weather_conditions="SU",
            past_weather_conditions="ND",
        )
        cls.location.tags.add(cls.tag)

        cls.layer = Layer.objects.create(
            location=cls.location,
            identifier=1,
            token="TST001",
            description="Test Layer Description",
            depth_top=0.0,
            depth_bottom=10.0,
            structure="kit",
            fine_soil_field="sand",
            munsell_hue_value=5.0,
            munsell_hue="YR",
            munsell_value=6.0,
            munsell_chroma=4.0,
            calcite=2.5,
            secondary_calcite=False,
        )
        cls.layer.tags.add(cls.tag)

        cls.device = Device.objects.create(name="Test Device")
        cls.accessory = Accessory.objects.create(device=cls.device)

        cls.test_file = SimpleUploadedFile("test_raw_data.txt", b"file_content", content_type="text/plain")

        cls.sample = Sample.objects.create(
            identifier="SAMPLE001",
            project=cls.project,
            location=cls.location,
            date="2023-01-01",
            description="Test Sample",
            material="Test Material",
            depth_top=10.00,
            depth_bottom=20.00,
            type=cls.sample_type,
            layer=cls.layer,
            processor=cls.researcher,
        )
        cls.sample.tags.add(cls.tag)

    def setUp(self):
        self.raw_measurement = RawMeasurement.objects.create(
            id=1,
            project=self.project,
            device=self.device,
            accessories=self.accessory,
            researcher=self.researcher,
            file=self.test_file,
            description="Test description",
        )
        self.raw_measurement.sample.add(self.sample)

    def test_raw_measurement_creation(self):
        file = RawMeasurement.objects.get(id=1)
        self.assertEqual(self.raw_measurement.project, self.project)
        self.assertEqual(self.raw_measurement.device, self.device)
        self.assertEqual(self.raw_measurement.accessories, self.accessory)
        self.assertEqual(self.raw_measurement.researcher, self.researcher)
        self.assertTrue(file.file.name.startswith("analysis/raw_data/test_raw_data"))
        self.assertEqual(self.raw_measurement.description, "Test description")

    def test_file_upload_path(self):

        self.assertTrue(self.raw_measurement.file.name.startswith("analysis/raw_data/"))

    def test_file_content(self):
        self.assertEqual(self.raw_measurement.file.read(), b"file_content")
        self.raw_measurement.file.seek(0)

    def test_optional_fields(self):
        raw_measurement = RawMeasurement.objects.create(
            project=self.project,
            device=self.device,
            researcher=self.researcher,
            file=self.test_file,
            accessories=None,
            description=None,
        )
        self.assertIsNone(raw_measurement.accessories)
        self.assertIsNone(raw_measurement.description)

    def test_sample_relation(self):
        self.assertIn(self.sample, self.raw_measurement.sample.all())

    """
    def test_file_deletion(self):
        file_path = self.raw_measurement.file.path
        self.raw_measurement.delete()
        self.assertFalse(os.path.exists(file_path))
    """
