"""Synthetic demo data for trying CGDB (see load_demo_data and compose.demo.yml).

Everything here is invented: a fictional study area with locations, layers,
samples and analyses, two demo accounts and a few rectangular landform
regions. Nothing is derived from real measurements or from the Murphy
landform dataset.

The data is created once, inside one transaction, and only when the demo
project does not exist yet; accounts and their permissions are refreshed on
every run. reset_demo_data() removes what create_demo_data() made, except
shared lookup rows (sample type, pollen taxa, parameters, method), which may
also be used by other data.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.contrib.gis.geos import (
    LineString,
    MultiLineString,
    MultiPolygon,
    Polygon,
)
from django.db import transaction

from analysis.models import (
    CLASSES,
    Counting,
    GenericMeasurement,
    GrainSize,
    LuminescenceDating,
    Parameter,
    Pollen,
    PollenCount,
    RadiocarbonDating,
)
from bibliography.models import Author, Reference
from field_data.models import (
    Campaign,
    Layer,
    Location,
    Sample,
    SampleType,
    StudyArea,
    Transect,
)
from geodata.models import Landform
from laboratory.models import Method
from prototype.access import sync_member_permissions
from prototype.models import Project, Researcher, ResearchGroup
from prototype.permissions import create_permission_groups

PROJECT_LABEL = "DEMO"
PI_USERNAME = "demo_pi"
VIEWER_USERNAME = "demo_viewer"
LANDFORM_SOURCE = "CGDB demo"
LITERATURE_IDENTIFIER = "DEMO-LIT-1"
REFERENCE_TITLE = "A fictional study of the CGDB demo valley"
GROUP_LABEL = "CGDB demo group"
AUTHOR_NAME = ("Example", "Erika")

# Fictional study area: a small box in the Lower Rhine Embayment.
_LON_MIN, _LON_MAX = 6.60, 6.80
_LAT_MIN, _LAT_MAX = 50.80, 50.90
_LOCATION_COUNT = 8
_LAYERS = ((0.0, 0.3), (0.3, 0.8), (0.8, 1.5))  # depth in m
_SEED = 279

_POLLEN_TAXA = (
    ("Pinus", "PIN"),
    ("Betula", "BET"),
    ("Quercus", "QUE"),
    ("Corylus", "COR"),
    ("Poaceae", "POA"),
    ("Artemisia", "ART"),
)
_PARAMETERS = (
    ("Calcium", "Ca"),
    ("Iron", "Fe"),
    ("Potassium", "K"),
    ("Zirconium", "Zr"),
)

# Rectangular stand-ins for landform regions, one per continent, so the map
# legend colours can be seen. (lon_min, lat_min, lon_max, lat_max)
_LANDFORM_BOXES = (
    ("Europe", (5.0, 49.0, 9.0, 52.0)),
    ("Africa", (10.0, 5.0, 20.0, 15.0)),
    ("Asia", (80.0, 30.0, 90.0, 40.0)),
    ("North America", (-105.0, 35.0, -95.0, 45.0)),
    ("South America", (-65.0, -20.0, -55.0, -10.0)),
    ("Oceania", (130.0, -30.0, 140.0, -20.0)),
)


@dataclass
class DemoResult:
    """What a run created or found."""

    created: bool
    counts: dict[str, int] = field(default_factory=dict)


def _dec(value: float) -> Decimal:
    return Decimal(str(round(value, 3)))


def _ensure_user(username: str, password: str, role: str) -> User:
    user, _ = User.objects.get_or_create(
        username=username,
        defaults={"first_name": "Demo", "last_name": role},
    )
    user.is_staff = True
    user.is_active = True
    user.set_password(password)
    user.save()
    user.groups.add(Group.objects.get(name=role))
    return user


def _ensure_accounts(password: str) -> tuple[User, User]:
    create_permission_groups()
    pi = _ensure_user(PI_USERNAME, password, "Principal Investigator")
    viewer = _ensure_user(VIEWER_USERNAME, password, "Viewer")
    return pi, viewer


def _create_project(pi: User, viewer: User) -> Project:
    researcher, _ = Researcher.objects.get_or_create(
        user=pi, defaults={"academic_rank": "D", "position": "WiMa"}
    )
    group, _ = ResearchGroup.objects.get_or_create(
        label=GROUP_LABEL, defaults={"head_of_group": researcher}
    )
    project = Project.objects.create(
        title="CGDB demo project",
        label=PROJECT_LABEL,
        description="Synthetic data for trying CGDB. Not real measurements.",
    )
    project.principal_investigator.add(researcher)
    project.research_group.add(group)
    project.members.add(pi, viewer)
    return project


def _box(
    lon_min: float, lat_min: float, lon_max: float, lat_max: float
) -> Polygon:
    return Polygon(
        (
            (lon_min, lat_min),
            (lon_max, lat_min),
            (lon_max, lat_max),
            (lon_min, lat_max),
            (lon_min, lat_min),
        ),
        srid=4326,
    )


def _create_field_frame(project: Project) -> tuple[Campaign, Transect]:
    area = StudyArea.objects.create(
        label="Demo valley",
        project=project,
        geometry=_box(_LON_MIN, _LAT_MIN, _LON_MAX, _LAT_MAX),
    )
    campaign = Campaign.objects.create(label="DEMO-2026", project=project)
    campaign.study_areas.add(area)
    line = LineString(
        (
            (_LON_MIN + 0.02, _LAT_MIN + 0.02),
            (_LON_MAX - 0.02, _LAT_MAX - 0.02),
        ),
        srid=4326,
    )
    transect = Transect.objects.create(
        identifier="DEMO-T1",
        study_area=area,
        campaign=campaign,
        description="Valley cross-section (synthetic)",
        multiline=MultiLineString(line, srid=4326),
    )
    return campaign, transect


def _grain_size_distribution(
    rng: random.Random, mode_um: float
) -> list[float]:
    """Return a log-normal volume distribution over CLASSES, in percent."""
    sigma = rng.uniform(0.8, 1.3)
    log_mode = math.log(mode_um)
    weights = [
        math.exp(-((math.log(c) - log_mode) ** 2) / (2 * sigma**2))
        for c in CLASSES
    ]
    total = sum(weights)
    return [round(100 * w / total, 4) for w in weights]


def _add_analyses(
    rng: random.Random, sample: Sample, layer_index: int
) -> None:
    # Finer material near the surface, coarser at depth.
    mode_um = (25.0, 80.0, 300.0)[layer_index] * rng.uniform(0.7, 1.4)
    GrainSize.objects.create(
        sample=sample,
        method="L",
        classes=list(CLASSES),
        measured_data=_grain_size_distribution(rng, mode_um),
    )
    if layer_index == len(_LAYERS) - 1:
        age = rng.uniform(8.0, 25.0)
        LuminescenceDating.objects.create(
            sample=sample,
            mineral="Quartz",
            dating_approach="Burial dating",
            luminescence_age=_dec(age),
            age_error=_dec(age * rng.uniform(0.05, 0.1)),
            data_quality="accepted",
        )
    if layer_index == 0:
        RadiocarbonDating.objects.create(
            sample=sample,
            lab="Other",
            lab_id=f"DEMO-14C-{sample.pk}",
            age=_dec(rng.uniform(0.5, 4.0)),
            data_quality="pending",
        )


def _add_pollen(rng: random.Random, sample: Sample) -> None:
    counting = Counting.objects.create(sample=sample, type="Absolute numbers")
    for name, token in _POLLEN_TAXA:
        pollen, _ = Pollen.objects.get_or_create(
            name=name, defaults={"token": token}
        )
        PollenCount.objects.create(
            counting=counting, pollen=pollen, number=rng.randint(5, 180)
        )


def _add_geochemistry(
    rng: random.Random, sample: Sample, method: Method
) -> None:
    for name, token in _PARAMETERS:
        parameter, _ = Parameter.objects.get_or_create(
            name=name, defaults={"token": token, "unit": "mg/kg"}
        )
        value = rng.uniform(200.0, 30000.0)
        GenericMeasurement.objects.create(
            sample=sample,
            method=method,
            parameter=parameter,
            value=round(value, 1),
            error=round(value * 0.03, 1),
        )


def _create_locations(rng: random.Random, project: Project) -> None:
    campaign, transect = _create_field_frame(project)
    sample_type, _ = SampleType.objects.get_or_create(
        word="Sediment", defaults={"label": "SED"}
    )
    method, _ = Method.objects.get_or_create(
        name="XRF (demo)", defaults={"category": "CHEM", "token": "XRF"}
    )
    for n in range(1, _LOCATION_COUNT + 1):
        location = Location.objects.create(
            identifier=f"DEMO-{n:02d}",
            project=project,
            campaign=campaign,
            transect=transect if n % 2 else None,
            easting=round(rng.uniform(_LON_MIN + 0.01, _LON_MAX - 0.01), 5),
            northing=round(rng.uniform(_LAT_MIN + 0.01, _LAT_MAX - 0.01), 5),
            altitude=round(rng.uniform(45.0, 120.0), 1),
        )
        for index, (top, bottom) in enumerate(_LAYERS):
            layer = Layer.objects.create(
                location=location,
                identifier=index + 1,
                depth_top=top,
                depth_bottom=bottom,
            )
            sample = Sample.objects.create(
                identifier=f"{location.identifier}-{index + 1}",
                project=project,
                location=location,
                layer=layer,
                type=sample_type,
                depth_top=_dec(top),
                depth_bottom=_dec(bottom),
                material="Silt and sand (synthetic)",
            )
            _add_analyses(rng, sample, index)
            if n <= 2:  # noqa: PLR2004
                _add_pollen(rng, sample)
            if index == 0:
                _add_geochemistry(rng, sample, method)


def _create_literature_location() -> None:
    author, _ = Author.objects.get_or_create(
        last_name=AUTHOR_NAME[0], first_name=AUTHOR_NAME[1]
    )
    reference, _ = Reference.objects.get_or_create(
        title=REFERENCE_TITLE,
        defaults={
            "lead_author": author,
            "abstract": "Invented reference for the CGDB demo.",
            "type": "Paper",
            "year": 2026,
        },
    )
    if not Location.objects.filter(identifier=LITERATURE_IDENTIFIER).exists():
        Location.objects.create(
            identifier=LITERATURE_IDENTIFIER,
            data_source="literature",
            reference=reference,
            easting=6.75,
            northing=50.83,
        )


def _create_landforms() -> None:
    if Landform.objects.filter(source=LANDFORM_SOURCE).exists():
        return
    for continent, bounds in _LANDFORM_BOXES:
        Landform.objects.create(
            geometry=MultiPolygon(_box(*bounds), srid=4326),
            name_str=f"Demo region ({continent})",
            continent=continent,
            murphy_code="DEMO",
            source=LANDFORM_SOURCE,
        )


def demo_counts() -> dict[str, int]:
    """Return the number of demo records per kind."""
    samples = Sample.objects.filter(project__label=PROJECT_LABEL)
    return {
        "locations": Location.objects.filter(
            project__label=PROJECT_LABEL
        ).count(),
        "samples": samples.count(),
        "grain_size": GrainSize.objects.filter(sample__in=samples).count(),
        "luminescence": LuminescenceDating.objects.filter(
            sample__in=samples
        ).count(),
        "radiocarbon": RadiocarbonDating.objects.filter(
            sample__in=samples
        ).count(),
        "pollen_counts": PollenCount.objects.filter(
            counting__sample__in=samples
        ).count(),
        "geochemistry": GenericMeasurement.objects.filter(
            sample__in=samples
        ).count(),
        "landforms": Landform.objects.filter(source=LANDFORM_SOURCE).count(),
    }


def create_demo_data(password: str) -> DemoResult:
    """Create the demo data if it is missing, and refresh the demo accounts."""
    with transaction.atomic():
        pi, viewer = _ensure_accounts(password)
        project = Project.objects.filter(label=PROJECT_LABEL).first()
        created = project is None
        if project is None:
            project = _create_project(pi, viewer)
            _create_locations(random.Random(_SEED), project)  # noqa: S311  # nosec B311 — seeded RNG for reproducible synthetic data, not security
        _create_literature_location()
        _create_landforms()
        sync_member_permissions(project)
    return DemoResult(created=created, counts=demo_counts())


def reset_demo_data() -> None:
    """Delete the demo project with its data, the demo accounts and landforms."""
    with transaction.atomic():
        samples = Sample.objects.filter(project__label=PROJECT_LABEL)
        PollenCount.objects.filter(counting__sample__in=samples).delete()
        for model in (
            Counting,
            GenericMeasurement,
            GrainSize,
            LuminescenceDating,
            RadiocarbonDating,
        ):
            model.objects.filter(sample__in=samples).delete()
        samples.delete()
        Layer.objects.filter(location__project__label=PROJECT_LABEL).delete()
        Location.objects.filter(project__label=PROJECT_LABEL).delete()
        Location.objects.filter(identifier=LITERATURE_IDENTIFIER).delete()
        Transect.objects.filter(
            study_area__project__label=PROJECT_LABEL
        ).delete()
        Campaign.objects.filter(project__label=PROJECT_LABEL).delete()
        StudyArea.objects.filter(project__label=PROJECT_LABEL).delete()
        Project.objects.filter(label=PROJECT_LABEL).delete()
        Reference.objects.filter(title=REFERENCE_TITLE).delete()
        Author.objects.filter(
            last_name=AUTHOR_NAME[0], first_name=AUTHOR_NAME[1]
        ).delete()
        ResearchGroup.objects.filter(label=GROUP_LABEL).delete()
        Researcher.objects.filter(
            user__username__in=(PI_USERNAME, VIEWER_USERNAME)
        ).delete()
        User.objects.filter(
            username__in=(PI_USERNAME, VIEWER_USERNAME)
        ).delete()
        Landform.objects.filter(source=LANDFORM_SOURCE).delete()
