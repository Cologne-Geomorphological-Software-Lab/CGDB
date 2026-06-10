"""Models for laboratory equipment, methods, and calibration records."""

from django.db import models

from prototype.models import BaseModel, Researcher


class Manufacturer(models.Model):
    """A laboratory equipment manufacturer."""

    name = models.CharField(max_length=100)
    website = models.URLField(blank=True)

    def __str__(self) -> str:
        """Return the manufacturer name."""
        return self.name


class Device(models.Model):
    """A laboratory device used to perform measurements.

    A unique model:`DataType` must be assigned to the model so that when data is entered into
    :model:`results` the data is assigned to the correct attribute. The physical unit is specified in the unit
    attribute.
    """

    name = models.CharField(max_length=40)
    description = models.CharField(
        max_length=150,
        blank=True,
    )
    token = models.CharField(
        max_length=5,
        blank=True,
    )
    manufacturer = models.ForeignKey(
        Manufacturer,
        on_delete=models.RESTRICT,
        blank=True,
        null=True,
    )

    def __str__(self) -> str:
        """Return the device name."""
        return f"{self.name}"


class Accessory(models.Model):
    """An accessory or attachment belonging to a device."""

    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
    )
    name = models.CharField(
        max_length=50,
    )
    description = models.TextField(blank=True)

    class Meta:
        """Meta options for Accessory."""

        verbose_name_plural = "Accessories"

    def __str__(self) -> str:
        """Return the device and accessory name."""
        return f"{self.device.name} - {self.name}"


class AccessoryParameter(models.Model):
    """A named parameter value recorded for an accessory under a specific method."""

    method = models.CharField(
        max_length=50,
    )
    accessory = models.ForeignKey(
        Accessory,
        on_delete=models.CASCADE,
    )
    parameter_name = models.CharField(max_length=50)
    parameter_value = models.CharField(max_length=100)
    parameter_unit = models.CharField(
        max_length=5,
        blank=True,
    )

    def __str__(self) -> str:
        """Return the accessory name with its parameter and value."""
        return f"{self.accessory.name} - {self.parameter_name}: {self.parameter_value}"


class Method(models.Model):
    """A laboratory analytical method that can be added without changing application logic.

    A unique model:`DataType` must be assigned to the model so that when data is entered into
    :model:`results` the data is assigned to the correct attribute. The physical unit is specified in the unit
    attribute.
    """

    name = models.CharField(max_length=40)
    description = models.CharField(
        max_length=40,
        blank=True,
    )
    token = models.CharField(
        max_length=5,
        blank=True,
    )
    device = models.ForeignKey(
        Device,
        on_delete=models.RESTRICT,
        blank=True,
        null=True,
    )
    CATEGORY_CHOICES = [
        ("CHEM", "Geochemical"),
        ("PHY", "Geophysical"),
        ("CHRO", "Chronological"),
    ]
    category = models.CharField(
        max_length=4,
        choices=CATEGORY_CHOICES,
        default="CHEM",
    )
    LABORATORY_CHOICES = [
        ("PHY", "Phy.-Geo. Laboratory"),
        ("CLL", "Cologne Luminescence Laboratory"),
        ("EX", "External"),
    ]
    laboratory = models.CharField(
        max_length=4,
        choices=LABORATORY_CHOICES,
        blank=True,
    )
    available = models.BooleanField(default=True)

    def __str__(self) -> str:
        """Return the method name."""
        return f"{self.name}"


class Calibration(BaseModel):
    """A calibration event for a device, linked to a researcher and date."""

    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
    )
    date = models.DateField()
    researcher = models.ForeignKey(
        Researcher,
        on_delete=models.RESTRICT,
        null=True,
    )
    remarks = models.TextField(blank=True)

    def __str__(self) -> str:
        """Return the device and calibration date."""
        return f"{self.device} – {self.date}"


class Firmware(models.Model):
    """A firmware version installed on a device."""

    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
    )
    version = models.CharField(max_length=50)
    installation_date = models.DateField()
    changelog = models.TextField(blank=True)

    def __str__(self) -> str:
        """Return the device name and firmware version."""
        return f"{self.device.name} - {self.version}"
