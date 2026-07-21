"""Tests for field_data models.

Covers: Location (clean, save, PointField), Sample (clean, save, auto-project, depth_mid),
Layer (thickness), Campaign (unique constraints).
"""

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from bibliography.models import Author, Reference
from field_data.models import Campaign, Layer, Location, Sample
from prototype.models import Project

# ---------------------------------------------------------------------------
# Shared fixture – one DB-hit for the entire module via setUpTestData
# ---------------------------------------------------------------------------


class _BaseSetup(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="fd_user", password="pw")

        cls.project = Project.objects.create(
            title="Project A", label="PA01", status="ACTIVE"
        )
        cls.project2 = Project.objects.create(
            title="Project B", label="PB01", status="ACTIVE"
        )

        cls.author = Author.objects.create(last_name="Doe", first_name="Jane")
        cls.reference = Reference.objects.create(
            title="A Test Reference",
            abstract="Abstract.",
            type="Paper",
            lead_author=cls.author,
        )

        # A valid internal location used as a shared fixture
        cls.internal_location = Location.objects.create(
            identifier="BASE_INTERNAL",
            data_source="internal",
            project=cls.project,
        )


# ===========================================================================
# Location.clean()
# ===========================================================================


class LocationCleanTest(_BaseSetup):
    """Unit-level validation tests for Location.clean()."""

    def _make_location(self, **kwargs: object):
        """Returns an unsaved Location – does NOT call save() or clean()."""
        defaults: dict[str, object] = {"identifier": "TEMP"}
        defaults.update(kwargs)
        return Location(**defaults)

    # --- internal data source ---

    def test_internal_without_project_raises(self):
        loc = self._make_location(data_source="internal")
        with self.assertRaises(ValidationError) as cm:
            loc.clean()
        self.assertIn("project", str(cm.exception).lower())

    def test_internal_with_project_passes(self):
        loc = self._make_location(data_source="internal", project=self.project)
        loc.clean()  # Must not raise

    def test_internal_with_reference_raises(self):
        loc = self._make_location(
            data_source="internal",
            project=self.project,
            reference=self.reference,
        )
        with self.assertRaises(ValidationError) as cm:
            loc.clean()
        self.assertIn("reference", str(cm.exception).lower())

    # --- literature data source ---

    def test_literature_without_reference_raises(self):
        loc = self._make_location(data_source="literature")
        with self.assertRaises(ValidationError) as cm:
            loc.clean()
        self.assertIn("reference", str(cm.exception).lower())

    def test_literature_with_reference_passes(self):
        loc = self._make_location(
            data_source="literature", reference=self.reference
        )
        loc.clean()  # Must not raise

    def test_literature_without_project_passes(self):
        """Literature locations do not require a project."""
        loc = self._make_location(
            data_source="literature", reference=self.reference
        )
        loc.clean()  # Must not raise


# ===========================================================================
# Location.save()
# ===========================================================================


class LocationSaveTest(_BaseSetup):
    """Integration tests for Location.save() side-effects."""

    def test_point_created_from_easting_northing(self):
        loc = Location.objects.create(
            identifier="POINT01",
            data_source="internal",
            project=self.project,
            easting=7.4653,
            northing=51.5136,
            srid=4326,
        )
        assert loc.location is not None
        self.assertAlmostEqual(loc.location.x, 7.4653, places=4)
        self.assertAlmostEqual(loc.location.y, 51.5136, places=4)

    def test_no_point_when_easting_missing(self):
        loc = Location.objects.create(
            identifier="POINT02",
            data_source="internal",
            project=self.project,
            northing=51.5136,
        )
        self.assertIsNone(loc.location)

    def test_no_point_when_northing_missing(self):
        loc = Location.objects.create(
            identifier="POINT03",
            data_source="internal",
            project=self.project,
            easting=7.4653,
        )
        self.assertIsNone(loc.location)

    def test_no_point_when_both_coordinates_missing(self):
        loc = Location.objects.create(
            identifier="POINT04",
            data_source="internal",
            project=self.project,
        )
        self.assertIsNone(loc.location)

    def test_save_enforces_clean_no_project(self):
        """save() calls clean(); creating internal location without project raises."""
        with self.assertRaises(ValidationError):
            Location.objects.create(
                identifier="INVALID01",
                data_source="internal",
                # no project
            )

    def test_save_enforces_clean_internal_with_reference(self):
        """save() rejects internal location that also carries a reference."""
        with self.assertRaises(ValidationError):
            Location.objects.create(
                identifier="INVALID02",
                data_source="internal",
                project=self.project,
                reference=self.reference,
            )

    def test_point_srid_stored_correctly(self):
        loc = Location.objects.create(
            identifier="SRID01",
            data_source="internal",
            project=self.project,
            easting=7.0,
            northing=50.0,
            srid=4326,
        )
        self.assertEqual(loc.srid, 4326)

    def test_point_updated_on_coordinate_change(self):
        """Updating coordinates and re-saving creates a new Point."""
        loc = Location.objects.create(
            identifier="UPDATE01",
            data_source="internal",
            project=self.project,
            easting=7.0,
            northing=50.0,
        )
        loc.easting = 8.0
        loc.northing = 51.0
        loc.save()
        assert loc.location is not None
        self.assertAlmostEqual(loc.location.x, 8.0)
        self.assertAlmostEqual(loc.location.y, 51.0)


# ===========================================================================
# Sample.clean()
# ===========================================================================


class SampleCleanTest(_BaseSetup):
    """Unit-level validation tests for Sample.clean()."""

    def _make_sample(self, **kwargs: object):
        defaults: dict[str, object] = {"identifier": "TEMP_S"}
        defaults.update(kwargs)
        return Sample(**defaults)

    def test_no_project_no_location_raises(self):
        sample = self._make_sample()
        with self.assertRaises(ValidationError) as cm:
            sample.clean()
        self.assertIn("project", str(cm.exception).lower())

    def test_project_location_mismatch_raises(self):
        sample = self._make_sample(
            project=self.project2,  # Different project
            location=self.internal_location,  # Belongs to project
        )
        with self.assertRaises(ValidationError) as cm:
            sample.clean()
        self.assertIn("match", str(cm.exception).lower())

    def test_matching_project_location_passes(self):
        sample = self._make_sample(
            project=self.project,
            location=self.internal_location,
        )
        sample.clean()  # Must not raise

    def test_only_project_passes(self):
        sample = self._make_sample(project=self.project)
        sample.clean()  # Must not raise

    def test_only_location_passes(self):
        sample = self._make_sample(location=self.internal_location)
        sample.clean()  # Must not raise

    def test_location_without_project_is_valid(self):
        """Location might have no project; sample with only location is still valid."""
        sample = self._make_sample(location=self.internal_location)
        sample.clean()  # Must not raise


# ===========================================================================
# Sample.save()
# ===========================================================================


class SampleSaveTest(_BaseSetup):
    """Integration tests for Sample.save() behavior."""

    def test_project_auto_assigned_from_location(self):
        sample = Sample.objects.create(
            identifier="AUTO01",
            location=self.internal_location,
        )
        self.assertEqual(sample.project, self.project)

    def test_explicit_matching_project_not_overridden(self):
        sample = Sample.objects.create(
            identifier="AUTO02",
            project=self.project,
            location=self.internal_location,
        )
        self.assertEqual(sample.project, self.project)

    def test_no_project_no_location_raises(self):
        with self.assertRaises(ValidationError):
            Sample.objects.create(identifier="AUTO03")

    def test_mismatched_project_raises(self):
        with self.assertRaises(ValidationError):
            Sample.objects.create(
                identifier="AUTO04",
                project=self.project2,
                location=self.internal_location,
            )

    def test_str_returns_identifier(self):
        sample = Sample.objects.create(
            identifier="STR01", project=self.project
        )
        self.assertEqual(str(sample), "STR01")

    def test_identifier_is_unique(self):
        Sample.objects.create(identifier="UNIQ01", project=self.project)
        with self.assertRaises(IntegrityError):
            Sample.objects.create(identifier="UNIQ01", project=self.project)


# ===========================================================================
# Sample.depth_mid property
# ===========================================================================


class SampleDepthMidTest(_BaseSetup):
    """Tests for the Sample.depth_mid computed property."""

    def test_depth_mid_integer_values(self):
        s = Sample.objects.create(
            identifier="DM01",
            project=self.project,
            depth_top=10,
            depth_bottom=30,
        )
        self.assertEqual(s.depth_mid, 20)

    def test_depth_mid_decimal_values(self):
        s = Sample.objects.create(
            identifier="DM02",
            project=self.project,
            depth_top=5,
            depth_bottom=16,
        )
        assert s.depth_mid is not None
        self.assertAlmostEqual(float(s.depth_mid), 10.5)

    def test_depth_mid_none_without_top(self):
        s = Sample.objects.create(
            identifier="DM03", project=self.project, depth_bottom=20
        )
        self.assertIsNone(s.depth_mid)

    def test_depth_mid_none_without_bottom(self):
        s = Sample.objects.create(
            identifier="DM04", project=self.project, depth_top=10
        )
        self.assertIsNone(s.depth_mid)

    def test_depth_mid_none_when_both_absent(self):
        s = Sample.objects.create(identifier="DM05", project=self.project)
        self.assertIsNone(s.depth_mid)

    def test_depth_mid_zero_values(self):
        s = Sample.objects.create(
            identifier="DM06",
            project=self.project,
            depth_top=0,
            depth_bottom=0,
        )
        self.assertEqual(s.depth_mid, 0)


# ===========================================================================
# Layer.thickness property
# ===========================================================================


class LayerThicknessTest(_BaseSetup):
    """Tests for the Layer.thickness computed property."""

    def test_thickness_positive(self):
        layer = Layer.objects.create(
            location=self.internal_location,
            identifier=1,
            depth_top=5.0,
            depth_bottom=25.0,
        )
        assert layer.thickness is not None
        self.assertAlmostEqual(layer.thickness, 20.0)

    def test_thickness_small_interval(self):
        layer = Layer.objects.create(
            location=self.internal_location,
            identifier=2,
            depth_top=0.0,
            depth_bottom=0.5,
        )
        assert layer.thickness is not None
        self.assertAlmostEqual(layer.thickness, 0.5)

    def test_thickness_none_without_top(self):
        layer = Layer.objects.create(
            location=self.internal_location, identifier=3, depth_bottom=25.0
        )
        self.assertIsNone(layer.thickness)

    def test_thickness_none_without_bottom(self):
        layer = Layer.objects.create(
            location=self.internal_location, identifier=4, depth_top=5.0
        )
        self.assertIsNone(layer.thickness)

    def test_thickness_none_when_both_absent(self):
        layer = Layer.objects.create(
            location=self.internal_location, identifier=5
        )
        self.assertIsNone(layer.thickness)


# ===========================================================================
# Campaign
# ===========================================================================


class CampaignTest(_BaseSetup):
    """Tests for the Campaign model."""

    def test_basic_creation(self):
        campaign = Campaign.objects.create(
            label="CAMP2024A",
            project=self.project,
            date_start="2024-06-01",
            date_end="2024-08-31",
        )
        self.assertEqual(campaign.label, "CAMP2024A")
        self.assertEqual(campaign.project, self.project)

    def test_label_uniqueness_enforced(self):
        Campaign.objects.create(label="CAMP_UNIQ01", project=self.project)
        with self.assertRaises(IntegrityError):
            Campaign.objects.create(label="CAMP_UNIQ01", project=self.project2)

    def test_str_contains_label(self):
        campaign = Campaign.objects.create(
            label="CAMP_STR01", project=self.project
        )
        self.assertIn("CAMP_STR01", str(campaign))

    def test_location_unique_per_campaign(self):
        """Two locations in the same campaign cannot share an identifier."""
        campaign = Campaign.objects.create(
            label="CAMP_DUP01", project=self.project
        )
        Location.objects.create(
            identifier="DUP_LOC",
            data_source="internal",
            project=self.project,
            campaign=campaign,
        )
        with self.assertRaises(IntegrityError):
            Location.objects.create(
                identifier="DUP_LOC",
                data_source="internal",
                project=self.project,
                campaign=campaign,
            )

    def test_same_identifier_allowed_in_different_campaigns(self):
        """Same location identifier is valid across different campaigns."""
        campaign_a = Campaign.objects.create(
            label="CAMP_A01", project=self.project
        )
        campaign_b = Campaign.objects.create(
            label="CAMP_B01", project=self.project
        )
        Location.objects.create(
            identifier="SHARED_ID",
            data_source="internal",
            project=self.project,
            campaign=campaign_a,
        )
        loc_b = Location.objects.create(
            identifier="SHARED_ID",
            data_source="internal",
            project=self.project,
            campaign=campaign_b,
        )
        self.assertIsNotNone(loc_b.pk)


# ===========================================================================
# FieldPhoto
# ===========================================================================


class FieldPhotoTest(_BaseSetup):
    """Tests for the generic FieldPhoto model on Location and Layer."""

    @staticmethod
    def _make_file(name: str = "profile.jpg"):
        from django.core.files.uploadedfile import SimpleUploadedFile

        return SimpleUploadedFile(name, b"fake-image-bytes")

    def test_attach_photo_to_location(self):
        photo = self.internal_location.field_photos.create(
            file=self._make_file(),
            caption="North profile wall",
        )
        self.assertEqual(photo.content_object, self.internal_location)
        self.assertEqual(self.internal_location.field_photos.count(), 1)

    def test_attach_photo_to_layer(self):
        layer = Layer.objects.create(
            location=self.internal_location, identifier=1
        )
        photo = layer.field_photos.create(file=self._make_file("sketch.png"))
        self.assertEqual(photo.content_object, layer)
        self.assertEqual(layer.field_photos.count(), 1)

    def test_deleting_location_deletes_photos(self):
        from field_data.models import FieldPhoto

        location = Location.objects.create(
            identifier="PHOTO_LOC",
            data_source="internal",
            project=self.project,
        )
        location.field_photos.create(file=self._make_file())
        location.delete()
        self.assertEqual(FieldPhoto.objects.count(), 0)

    def test_str_returns_caption_or_file_name(self):
        photo = self.internal_location.field_photos.create(
            file=self._make_file(),
            caption="Stratigraphy overview",
        )
        self.assertEqual(str(photo), "Stratigraphy overview")

        uncaptioned = self.internal_location.field_photos.create(
            file=self._make_file("notes.pdf"),
        )
        self.assertIn("notes", str(uncaptioned))
