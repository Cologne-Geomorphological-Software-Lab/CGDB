from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.db import models
from django.contrib.gis.geos import Point
from django.core.exceptions import ValidationError
from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
    StepValueValidator,
)

from prototype.models import BaseModel, Project, Researcher



class Country(models.Model):
    """Simplified Country model for basic country information."""

    name = models.CharField(
        max_length=100, blank=True, null=True, help_text="Country name"
    )
    iso_code = models.CharField(
        max_length=3,
        unique=True,
        blank=True,
        null=True,
        help_text="ISO 3166-1 alpha-3 code",
    )
    geometry = models.MultiPolygonField(
        blank=True, null=True, help_text="Country borders"
    )

    def __str__(self):
        return self.name or f"Country {self.id}"


class Province(models.Model):
    """Simplified Province model for administrative divisions."""

    name = models.CharField(
        max_length=100,
        help_text="Province/state name",
        blank=True,
        null=True,
    )
    country = models.ForeignKey(
        Country,
        blank=True,
        null=True,
        on_delete=models.RESTRICT,
        help_text="Country this province belongs to",
    )
    geometry = models.MultiPolygonField(
        blank=True, null=True, help_text="Province borders"
    )

    def __str__(self):
        return self.name or f"Province {self.id}"


class Tag(BaseModel):
    """Represents a Tag model that is associated with a content type and optionally a project.

    Attributes:
        content_type (ForeignKey): A foreign key to the ContentType model, indicating the type of content this tag is associated with.
        word (CharField): The word or name of the tag, with a maximum length of 255 characters.
        slug (SlugField): A unique slug for the tag, with a maximum length of 255 characters. Can be blank or null.
        project (ForeignKey): An optional foreign key to the Project model, indicating the project this tag is associated with. Can be blank or null.

    Methods:
        __str__(): Returns a string representation of the tag in the format "word (content_type.name)".
        __repr__(): Returns a detailed string representation of the tag in the format "<Tag: word, content_type>".
    """

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
    )

    word = models.CharField(max_length=255)
    slug = models.SlugField(
        max_length=255,
        unique=True,
        blank=True,
        null=True,
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="tags",
        blank=True,
        null=True,
    )

    def __str__(self):
        return f"{self.word} ({self.content_type.name})"

    def __repr__(self):
        return f"<Tag: {self.word}, {self.content_type}>"


class SampleType(BaseModel):
    """SampleType model represents a type of sample with a unique identifier and label.

    Attributes:
        word (CharField): A short, unique identifier for the sample type.
        label (CharField): A short, abbreviated label.
        created_at (DateTimeField): The creation timestamp, automatically set.

    Methods:
        __str__(): Returns the unique word identifier of the sample type.
    """

    word = models.CharField(
        max_length=35,
        help_text="A short, unique identifier for the sample type.",
    )
    label = models.CharField(
        max_length=5,
        help_text="A short, abbreviated label.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="The creation timestamp, automatically set.",
    )

    def __str__(self):
        """
        Returns:
            str: The unique word identifier of the sample type.
        """
        return self.word


'''
class SampleLabel(models.Model):
    """
    Enables a sample system for field documentation.
    word (varchar): The unique identifier for the study area.
    """

    word = models.CharField(max_length=35)
    slug = models.CharField(max_length=250)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.word
'''


class StudyArea(BaseModel):
    """Model representing a study area with various attributes such as label, project, province, geometry, and
    climate classifications.

    Attributes:
        label (CharField): A short label for the study area.
        project (ForeignKey): A reference to the associated project.
        province (ForeignKey): A reference to the associated province, can be blank or null.
        geometry (PolygonField): The geometric representation of the study area, can be blank or null.
        climate_koeppen (CharField): The climate classification based on the Koppen system, can be blank or null.
        ecozone_schultz (CharField): The ecozone classification based on the Schultz system, can be blank or null.

    Choices:
        CHOICES_KOEPPEN: A list of tuples representing the Koppen climate classification system.
        CHOICES_SCHULTZ: A list of tuples representing the Schultz ecozone classification system.

    Meta:
        verbose_name_plural (str): The plural name for the model.

    Methods:
        __str__: Returns the string representation of the study area, which is its label.
    """

    label = models.CharField(max_length=20)
    project = models.ForeignKey(
        Project,
        on_delete=models.RESTRICT,
    )
    province = models.ForeignKey(
        Province,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    geometry = models.PolygonField(
        blank=True,
        null=True,
    )
    CHOICES_KOEPPEN = [
        (
            "A: Tropical climates",
            (
                ("Af", "Tropical rainforest climate"),
                ("Aw", "Tropical savanna climate with dry-winter characteristics"),
                ("As", "Tropical savanna climate with dry-summer characteristics"),
                ("Am", "Tropical monsoon climate"),
            ),
        ),
        (
            "B: Dry climates",
            (
                ("BWh", "Hot arid climate"),
                ("BWc", "Cold arid climate"),
                ("BSh", "Hot semi-arid climate"),
                ("BSc", "Cold semi-arid climate"),
            ),
        ),
        (
            "C: Temperate climates",
            (
                ("Csa", "Mediterranean hot summer climate"),
                ("Csb", "Mediterranean warm/cool summer climate"),
                ("Csc", "Mediterranean cold summer climate"),
                ("Cfa", "Humid subtropical climate"),
                ("Cfb", "Oceanic climate"),
                ("Cfc", "Subpolar oceanic climate"),
                ("Cwa", "Dry-winter humid subtropical climate"),
                ("Cwb", "Dry-winter subtropical highland climate"),
                ("Cwc", "Dry-winter subpolar oceanic climate"),
            ),
        ),
        (
            "D: Continental climates",
            (
                ("Dfa", "Hot-summer humid continental climate"),
                ("Dfb", "Warm-summer humid continental climate"),
                ("Dfc", "Subarctic climate"),
                ("Dfd", "Extremely cold subarctic climate"),
                ("Dwa", "Monsoon-influenced hot-summer humid continental climate"),
                ("Dwb", "Monsoon-influenced warm-summer humid continental climate"),
                ("Dwc", "Monsoon-influenced subarctic climate"),
                ("Dwd", "Monsoon-influenced extremely cold subarctic climate"),
                (
                    "Dsa",
                    "Mediterranean-influenced hot-summer humid continental climate",
                ),
                (
                    "Dsb",
                    "Mediterranean-influenced warm-summer humid continental climate",
                ),
                ("Dsc", "Mediterranean-influenced subarctic climate"),
                ("Dsd", "Mediterranean-influenced extremely cold subarctic climate"),
            ),
        ),
        (
            "E: Polar and alpine climates",
            (
                ("ET", "Tundra climate"),
                ("EF", "Ice cap climate"),
            ),
        ),
    ]
    climate_koeppen = models.CharField(
        max_length=3,
        choices=CHOICES_KOEPPEN,
        blank=True,
        null=True,
    )
    CHOICES_SCHULTZ = [
        ("TYR", "Tropics with year-round rain"),
        ("TSR", "Tropics with summer rain"),
        ("TSD", "Dry Tropics and subtropics"),
        ("SYR", "Subtropics with year-round rain"),
        ("SWR", "Subtropics with winter rain (Mediterranean climate)"),
        ("MHU", "Humid mid-latitudes"),
        ("MDR", "Dry mid-latitudes"),
        ("BOR", "Boreal zone"),
        ("POS", "Polar-subpolar zone"),
    ]
    ecozone_schultz = models.CharField(
        max_length=3,
        choices=CHOICES_SCHULTZ,
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name_plural = "Study area"

    def __str__(self):
        return str(self.label)


class Site(BaseModel):
    """Represents a Site model.

    Attributes:
        label (CharField): The label of the site, with a maximum length of 30 characters.
        study_area (ForeignKey): A foreign key to the StudyArea model, with a cascade delete option.
        tags (ManyToManyField): A many-to-many relationship with the Tag model.
    Methods:
        __str__(): Returns the string representation of the site, which is its label.
    """

    label = models.CharField(max_length=30)
    study_area = models.ForeignKey(
        StudyArea,
        on_delete=models.CASCADE,
    )
    tags = models.ManyToManyField(Tag)

    def __str__(self):
        return str(self.label)


class Campaign(BaseModel):
    label = models.CharField(
        max_length=20,
        unique=True,
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.RESTRICT,
    )
    date_start = models.DateField(
        verbose_name="Starting date",
        blank=True,
        null=True,
    )
    date_end = models.DateField(
        verbose_name="Ending date",
        blank=True,
        null=True,
    )
    destination_country = models.ForeignKey(
        Country,
        verbose_name="Country of destination",
        on_delete=models.RESTRICT,
        blank=True,
        null=True,
    )
    study_areas = models.ManyToManyField(
        StudyArea,
        blank=True,
    )
    CHOICES_SEASON = [
        (
            "Temperate climates",
            (
                ("SP", "Spring"),
                ("SU", "Summer"),
                ("AU", "Autumn"),
                ("WI", "Winter"),
            ),
        ),
        (
            "Monsoonal climates",
            (
                ("WS", "Wet season"),
                ("DS", "Dry season"),
            ),
        ),
        (
            "Equatorial climates",
            (("NS", "No significant seasonality for plant growth"),),
        ),
    ]
    season = models.CharField(
        max_length=2,
        choices=CHOICES_SEASON,
        blank=True,
        null=True,
    )

    def __str__(self):
        return str(self.label)


class Transect(BaseModel):
    """Represents a transect within a study area, used to structure profiles according to their spatial
    location.

    Attributes:
        identifier (CharField): A unique identifier for the transect.
        study_area (ForeignKey): A reference to the associated study area.
        campaign (ForeignKey): A reference to the associated field campaign, can be null or blank.
        description (CharField): A brief description of the transect.
        multiline (MultiLineStringField): Spatial data representing the transect, can be null or blank.

    Methods:
        __str__(): Returns the string representation of the transect, which is its identifier.
    """

    identifier = models.CharField(max_length=40)
    study_area = models.ForeignKey(
        StudyArea,
        on_delete=models.RESTRICT,
    )
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.RESTRICT,
        blank=True,
        null=True,
    )
    description = models.CharField(max_length=250)
    multiline = models.MultiLineStringField(
        blank=True,
        null=True,
    )

    def __str__(self):
        return str(self.identifier)


class ExposureType(BaseModel):
    """Model representing different types of geological exposures.

    Attributes:
        CHOICES_MAIN_TYPE (list of tuple): Choices for the main type of exposure.
        main_type (CharField): The main type of exposure, chosen from CHOICES_MAIN_TYPE.
        abbreviation (CharField): Abbreviation for the exposure type.
        name_ger (CharField): German name for the exposure type.
        name_en (CharField): English name for the exposure type.

    Methods:
        __str__(): Returns a string representation of the exposure type in the format "main_type: name_en (abbreviation)".
    """

    CHOICES_MAIN_TYPE = [
        ("B", "Borehole"),
        ("E", "Excavation"),
        ("O", "Outcrop"),
    ]
    main_type = models.CharField(
        choices=CHOICES_MAIN_TYPE,
        max_length=10,
    )
    abbreviation = models.CharField(max_length=5)
    name_ger = models.CharField(
        max_length=100,
    )
    name_en = models.CharField(
        max_length=100,
    )

    def __str__(self):
        return f"{self.main_type}: {self.name_en} ({self.abbreviation})"


class Location(BaseModel):
    """Location model represents a specific geographical location that can be associated with either
    a project (internal data) or a reference (literature data).

    Attributes:
        data_source (CharField): Source type - 'internal' for project data, 'literature' for published data.
        campaign (ForeignKey): Reference to the associated Campaign (mainly for internal data).
        identifier (CharField): Unique identifier for the location.
        project (ForeignKey): Reference to the associated Project (for internal data).
        reference (ForeignKey): Reference to the associated Reference/Paper (for literature data).
        date_of_record (DateField): Date when the record was created.
        easting (FloatField): Easting coordinate in decimal degrees.
        northing (FloatField): Northing coordinate in decimal degrees.
        srid (IntegerField): Spatial Reference System Identifier (default is 4326).
        location (PointField): Geographical point representing the location.
        altitude (FloatField): Altitude in meters above sea level.
        study_site (ForeignKey): Reference to the associated Site.
        transect (ForeignKey): Reference to the associated Transect.
        processor (ForeignKey): Reference to the Researcher who processed the location.
        exposure_type (ForeignKey): Reference to the associated ExposureType.
        liner (BooleanField): Indicates if the location was drilled using a closed liner.
        sampling (BooleanField): Indicates if samples were taken at the location.
        gradient_upslope (FloatField): Gradient upslope value.
        gradient_downslope (FloatField): Gradient downslope value.
        slope_aspect (IntegerField): Slope aspect with validators for range 0-360.
        relief_description (TextField): Qualitative description of the relief.
        current_weather_conditions (CharField): Current weather conditions with choices.
        past_weather_conditions (CharField): Past weather conditions with choices.
        tags (ManyToManyField): Tags associated with the location.

    Business Logic:
        - data_source='internal': Must have project, should have campaign
        - data_source='literature': Must have reference, project/campaign optional

    Meta:
        unique_together (tuple): Ensures unique combination of campaign and identifier.
        verbose_name_plural (str): Plural name for the model.

    Methods:
        __str__: Returns the string representation of the location identifier.
        save: Overrides the save method to set the location point based on easting and northing.
    """

    DATA_SOURCE_CHOICES = [
        ("internal", "Internal Project Data"),
        ("literature", "Literature Data"),
    ]

    data_source = models.CharField(
        max_length=10,
        choices=DATA_SOURCE_CHOICES,
        default="internal",
        help_text="Source of the location data",
    )

    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.RESTRICT,
        blank=True,
        null=True,
        db_index=True,
    )
    identifier = models.CharField(
        max_length=80,
        help_text="Add a unique identifier to your location.",
        db_index=True,
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.RESTRICT,
        db_index=True,
        blank=True,
        null=True,
        help_text="Project for internal data",
    )

    reference = models.ForeignKey(
        "bibliography.Reference",
        on_delete=models.RESTRICT,
        blank=True,
        null=True,
        help_text="Reference/Paper for literature data",
    )
    date_of_record = models.DateField(
        auto_now=False,
        auto_now_add=False,
        blank=True,
        null=True,
    )
    easting = models.FloatField(
        blank=True,
        null=True,
        help_text="in decimal degrees.",
    )
    northing = models.FloatField(
        blank=True,
        null=True,
        help_text="in decimal degrees.",
    )
    srid = models.IntegerField(
        default=4326,
        help_text="EPSG code",
    )
    location = models.PointField(
        srid=4326,
        blank=True,
        null=True,
    )
    altitude = models.FloatField(
        blank=True,
        null=True,
        help_text="in meters above sea level",
    )
    study_site = models.ForeignKey(
        Site,
        on_delete=models.RESTRICT,
        blank=True,
        null=True,
    )
    transect = models.ForeignKey(
        Transect,
        on_delete=models.RESTRICT,
        blank=True,
        null=True,
    )
    processor = models.ForeignKey(
        Researcher,
        on_delete=models.RESTRICT,
        blank=True,
        null=True,
    )
    exposure_type = models.ForeignKey(
        ExposureType,
        on_delete=models.RESTRICT,
        blank=True,
        null=True,
    )
    liner = models.BooleanField(
        default=False,
        help_text="Was the location drilled using a closed liner?",
    )
    sampling = models.BooleanField(
        default=False,
        help_text="Were samples taken at the location?",
    )
    gradient_upslope = models.FloatField(
        blank=True,
        null=True,
    )
    gradient_downslope = models.FloatField(
        blank=True,
        null=True,
    )
    slope_aspect = models.IntegerField(
        validators=[
            MaxValueValidator(360),
            MinValueValidator(0),
        ],
        blank=True,
        null=True,
    )
    relief_description = models.TextField(
        blank=True,
        null=True,
        help_text="Qualitative description of the relief.",
    )

    CHOICES_CURRENTWEATHER = [
        ("SU", "Sunny/clear"),
        ("PC", "Partly cloudy"),
        ("OV", "Overcast"),
        ("RA", "Rain"),
        ("SL", "Sleet"),
        ("SN", "Snow"),
    ]
    current_weather_conditions = models.CharField(
        max_length=2,
        choices=CHOICES_CURRENTWEATHER,
        blank=True,
        null=True,
    )

    CHOICES_PASTWEATHER = [
        ("NM", "No rain the last month"),
        ("NW", "No rain in the last week"),
        ("ND", "No rain the last 24 hours"),
        ("RD", "Rain but no heavy rain the last 24 hours"),
        ("RH", "Heavy rain for some days or excessive rain in the last 24 hours"),
        ("RE", "Extremely rainy or snow melting"),
    ]

    past_weather_conditions = models.CharField(
        max_length=2,
        choices=CHOICES_PASTWEATHER,
        blank=True,
        null=True,
    )
    tags = models.ManyToManyField(
        Tag,
        blank=True,
    )

    class Meta:
        unique_together = (
            "campaign",
            "identifier",
        )
        verbose_name_plural = "Location"

    def __str__(self):
        return f"{self.identifier}"

    def clean(self):
        """Validate the data_source logic for project/reference assignment."""
        if self.data_source == "internal":
            if not self.project:
                raise ValidationError(
                    "Internal data source requires a project assignment."
                )
            if self.reference:
                raise ValidationError(
                    "Internal data source cannot have a reference assignment."
                )
        elif self.data_source == "literature":
            if not self.reference:
                raise ValidationError(
                    "Literature data source requires a reference assignment."
                )


    def save(self, *args, **kwargs):
        if self.easting is not None and self.northing is not None:
            self.location = Point(
                self.easting,
                self.northing,
                srid=self.srid,
            )
        else:
            self.location = None
        super(Location, self).save(*args, **kwargs)


class Layer(BaseModel):
    """Layer model representing a geological layer with various attributes.

    Attributes:
        location (ForeignKey): Reference to the Location model.
        identifier (IntegerField): Unique identifier for the layer.
        token (CharField): Optional token with a maximum length of 7 characters.
        description (CharField): Optional description with a maximum length of 500 characters.
        depth_top (FloatField): Optional top depth of the layer.
        depth_bottom (FloatField): Optional bottom depth of the layer.
        thickness (FloatField): Optional thickness of the layer, calculated as the difference between depth_bottom and depth_top.
        structure (CharField): Optional structure type of the layer, chosen from predefined choices.
        fine_soil_field (CharField): Optional fine soil field with a maximum length of 6 characters.
        munsell_hue_value (FloatField): Optional Munsell hue value with validators for range and step.
        munsell_hue (CharField): Optional Munsell hue, chosen from predefined choices.
        munsell_value (FloatField): Optional Munsell value with validators for range and step.
        munsell_chroma (FloatField): Optional Munsell chroma with validators for range and step.
        calcite (FloatField): Optional calcite content with validators for range and step.
        secondary_calcite (BooleanField): Optional boolean indicating the presence of secondary calcite.
        tags (ManyToManyField): Many-to-many relationship with the Tag model.

    Methods:
        _thickness(): Calculates and returns the thickness of the layer.
        save(*args, **kwargs): Overrides the save method to calculate thickness before saving.
    """

    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
    )
    identifier = models.IntegerField()
    token = models.CharField(
        max_length=7,
        blank=True,
        null=True,
    )
    description = models.CharField(
        max_length=500,
        blank=True,
        null=True,
    )
    depth_top = models.FloatField(
        blank=True,
        null=True,
    )
    depth_bottom = models.FloatField(
        blank=True,
        null=True,
    )

    @property
    def thickness(self):
        """Calculates layer thickness from depth_top and depth_bottom."""
        if self.depth_top is not None and self.depth_bottom is not None:
            return self.depth_bottom - self.depth_top
        return None

    structure_choices = [
        ("ein", "Single grain structure"),
        ("kit", "Cemented structure"),
        ("koh", "Coherent structure"),
        ("ris", "Fissured structure"),
        ("sau", "Columnar structure"),
        ("shi", "Layered structure"),
        ("kru", "Crumb structure"),
        ("sub", "Subangular blocky structure"),
        ("pol", "Angular blocky structure"),
        ("pri", "Prismatic structure"),
        ("pla", "Platy structure"),
    ]
    structure = models.CharField(
        max_length=3,
        blank=True,
        null=True,
        choices=structure_choices,
    )

    fine_soil_field = models.CharField(
        max_length=6,
        blank=True,
        null=True,
        verbose_name="Fine soil",
        help_text="Finger test for soil texture",
    )

    hue_choices = [
        ("R", "R"),
        ("Y", "Y"),
        ("B", "B"),
        ("P", "P"),
        ("YR", "YR"),
        ("GY", "GY"),
        ("BG", "BG"),
        ("PB", "PB"),
        ("RP", "RP"),
    ]
    munsell_hue_value = models.FloatField(
        blank=True,
        null=True,
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(10),
            StepValueValidator(0.5),
        ],
    )
    munsell_hue = models.CharField(
        max_length=2,
        blank=True,
        null=True,
        choices=hue_choices,
    )
    munsell_value = models.FloatField(
        blank=True,
        null=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(10),
            StepValueValidator(0.5),
        ],
    )
    munsell_chroma = models.FloatField(
        blank=True,
        null=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(12),
            StepValueValidator(0.5),
        ],
    )
    calcite = models.FloatField(
        blank=True,
        null=True,
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(10),
            StepValueValidator(0.5),
        ],
    )
    secondary_calcite = models.BooleanField(
        default=False,
        blank=True,
        null=True,
    )
    tags = models.ManyToManyField(
        Tag,
    )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def __str__(self):
        return str(f"{self.location}-{self.identifier}")


class Sample(BaseModel):
    """Model representing a Sample that belongs to a Project.

    Attributes:
        identifier (CharField): Unique identifier for the sample.
        project (ForeignKey): Reference to the project this sample belongs to.
        date (DateField): Date when the sample was taken.
        location (ForeignKey): Reference to the location where the sample was taken.
        processor (ForeignKey): Reference to the Researcher member who processed the sample.
        parent (ForeignKey): Reference to the parent sample, if any.
        description (CharField): Description of the sample.
        material (CharField): Material of the sample.
        layer (ForeignKey): Reference to the layer where the sample was found.
        depth_top (DecimalField): Depth at the top of the sample (in cm). For literature data with only midpoint, use same value as depth_bottom.
        depth_bottom (DecimalField): Depth at the bottom of the sample (in cm). For literature data with only midpoint, use same value as depth_top.
        depth_mid (property): Midpoint depth of the sample, automatically calculated from top and bottom values.
        type (ForeignKey): Reference to the type of sample.
        tags (ManyToManyField): Tags associated with the sample.

    Business Logic:
        - Sample needs either a project OR a location (or both)
        - If both are set, they must be consistent
        - Location provides project context automatically

    Methods:
        clean(): Validates the project assignment logic.
        save(*args, **kwargs): Automatically assigns project based on location if not set.
    """

    identifier = models.CharField(max_length=40, unique=True)
    igsn = models.CharField(max_length=100, blank=True, null=True)
    project = models.ForeignKey(
        Project,
        on_delete=models.RESTRICT,
        blank=True,
        null=True,
    )

    date = models.DateField(blank=True, null=True)
    location = models.ForeignKey(
        Location,
        on_delete=models.RESTRICT,
        blank=True,
        null=True,
    )

    processor = models.ForeignKey(
        Researcher,
        on_delete=models.RESTRICT,
        blank=True,
        null=True,
    )
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="children",
        on_delete=models.RESTRICT,
    )

    description = models.CharField(
        max_length=40,
        blank=True,
        null=True,
    )
    material = models.CharField(
        max_length=40,
        blank=True,
        null=True,
    )
    layer = models.ForeignKey(
        Layer,
        on_delete=models.RESTRICT,
        blank=True,
        null=True,
    )
    weight = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
    )
    depth_top = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Top depth in cm. For literature data with only midpoint depth, enter the same value in both top and bottom fields.",
    )

    depth_bottom = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Bottom depth in cm. For literature data with only midpoint depth, enter the same value in both top and bottom fields.",
    )

    @property
    def depth_mid(self):
        """Calculate the midpoint depth of the sample."""
        if self.depth_top is not None and self.depth_bottom is not None:
            return (self.depth_top + self.depth_bottom) / 2
        return None

    type = models.ForeignKey(
        SampleType,
        blank=True,
        null=True,
        on_delete=models.RESTRICT,
    )
    tags = models.ManyToManyField(
        Tag,
        blank=True,
    )

    def clean(self):
        if self.pk:
            if not self.project and not self.location:
                raise ValidationError(
                    "Sample must have either a project or a location."
                )


            if self.project and self.location and self.location.project:
                if self.location.project != self.project:
                    raise ValidationError("Sample project must match location project.")

    def save(self, *args, **kwargs):

        if self.location and self.location.project and not self.project:
            self.project = self.location.project

        if not self.pk:
            if not self.project and not self.location:
                raise ValidationError(
                    "Sample must have either a project or a location."
                )

        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.identifier)
