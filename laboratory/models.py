from django.db import models

from prototype.models import BaseModel, Researcher


class Manufacturer(models.Model):
    name = models.CharField(max_length=100)
    website = models.URLField(blank=True)

    def __str__(self) -> str:
        return self.name


class Device(models.Model):
    """Using the Method model, new laboratory methods can be added to the database without changing the logic
    of the database itself.

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
        return f"{self.name}"


class Accessory(models.Model):
    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
    )
    name = models.CharField(
        max_length=50,
    )
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Accessories"

    def __str__(self) -> str:
        return f"{self.device.name} - {self.name}"


class AccessoryParameter(models.Model):
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
        return f"{self.accessory.name} - {self.parameter_name}: {self.parameter_value}"


class Method(models.Model):
    """Using the Method model, new laboratory methods can be added to the database without changing the logic
    of the database itself.

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
        return f"{self.name}"


class Calibration(BaseModel):
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
        return f"{self.device} – {self.date}"


class Firmware(models.Model):
    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
    )
    version = models.CharField(max_length=50)
    installation_date = models.DateField()
    changelog = models.TextField(blank=True)

    def __str__(self) -> str:
        return f"{self.device.name} - {self.version}"
