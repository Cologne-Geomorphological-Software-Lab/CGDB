"""Django forms for creating and editing field_data records."""

from __future__ import annotations

from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Column, Fieldset, Layout, Row, Submit
from django.contrib.gis import forms

from .models import Campaign, Layer, Location, Project, Sample, StudyArea, Tag


class CampaignForm(forms.ModelForm):
    """Form for creating and editing a Campaign."""

    class Meta:
        """Form metadata for CampaignForm."""

        model = Campaign
        fields = [
            "label",
            "project",
            "date_start",
            "date_end",
            "destination_country",
            "season",
        ]

        widgets = {
            "label": forms.TextInput(attrs={"class": "form-control"}),
            "project": forms.HiddenInput(
                attrs={
                    "class": "form-control",
                    "readonly": "readonly",
                },
            ),
            "date_start": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                },
            ),
            "date_end": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                },
            ),
            "destination_country": forms.Select(
                attrs={
                    "class": "form-control",
                },
            ),
            "season": forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Initialise the form, pre-populating the project field from project_id."""
        project_id = kwargs.pop("project_id", None)
        super().__init__(*args, **kwargs)
        self.fields["project"].widget.attrs["readonly"] = True

        if project_id is not None:
            try:
                project = Project.objects.get(id=project_id)
                self.initial["project"] = project
            except Project.DoesNotExist:
                pass  # It is acceptable if no matching Project exists; field will be left unset
        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", "Submit"))


class LocationForm(forms.ModelForm):
    """Form for creating and editing a Location."""

    class Meta:
        """Form metadata for LocationForm."""

        model = Location
        fields = [
            "project",
            "campaign",
            "identifier",
            "date_of_record",
            "easting",
            "northing",
            "srid",
            "altitude",
            "study_site",
            "processor",
            "exposure_type",
            "liner",
            "sampling",
            "gradient_upslope",
            "gradient_downslope",
            "slope_aspect",
            "relief_description",
            "current_weather_conditions",
            "past_weather_conditions",
            "tags",
        ]
        widgets = {
            "project": forms.HiddenInput(),
            "date_of_record": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Initialise the form and configure the crispy-forms helper."""
        super().__init__(*args, **kwargs)

        self.fields["processor"].widget.attrs["readonly"] = True
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            "project",
            Fieldset(
                "Identification",
                "identifier",
                "campaign",
                "processor",
                "date_of_record",
            ),
            Fieldset(
                "Coordinates",
                Row(
                    Column("easting", css_class="form-group col-md-4"),
                    Column("northing", css_class="form-group col-md-4"),
                    Column("srid", css_class="form-group col-md-2"),
                    Column("altitude", css_class="form-group col-md-2"),
                ),
            ),
            Fieldset(
                "Field setting",
                "study_site",
                Row(
                    Column("exposure_type", css_class="form-group col-md-4"),
                    Column("liner", css_class="form-group col-md-4"),
                    Column("sampling", css_class="form-group col-md-4"),
                ),
            ),
            Fieldset(
                "Environment",
                Row(
                    Column(
                        "gradient_upslope", css_class="form-group col-md-3"
                    ),
                    Column(
                        "gradient_downslope", css_class="form-group col-md-3"
                    ),
                    Column("slope_aspect", css_class="form-group col-md-3"),
                    Column(
                        "relief_description", css_class="form-group col-md-3"
                    ),
                ),
                "current_weather_conditions",
                "past_weather_conditions",
            ),
            "tags",
            Submit("submit", "Save Location"),
        )


class StudyAreaForm(forms.ModelForm):
    """Form for creating and editing a StudyArea."""

    class Meta:
        """Form metadata for StudyAreaForm."""

        model = StudyArea
        fields = [
            "label",
            "project",
            "province",
            "climate_koeppen",
            "ecozone_schultz",
            "geometry",
        ]
        widgets = {
            "area": forms.OSMWidget(
                attrs={"map_width": 800, "map_height": 500},
            ),
        }

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Initialise the form with a crispy-forms layout including a map widget."""
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            "label",
            "project",
            "province",
            "climate_koeppen",
            "ecozone_schultz",
            Row(Column("area", css_class="form-group col-md-6 my-3")),
            Submit("submit", "Submit"),
        )


class SampleForm(forms.ModelForm):
    """Form for creating and editing a Sample."""

    class Meta:
        """Form metadata for SampleForm."""

        model = Sample
        fields = [
            "identifier",
            "location",
            "processor",
            "parent",
            "description",
            "material",
            "layer",
            "depth_top",
            "depth_bottom",
        ]

        widgets = {
            "location": forms.HiddenInput(
                attrs={
                    "class": "form-control",
                    "readonly": "readonly",
                },
            ),
        }

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Initialise the form, pre-populating the location field when provided."""
        location = kwargs.pop("location", None)
        super().__init__(*args, **kwargs)
        if location:
            self.initial["location"] = location
            self.fields["location"].widget.attrs["readonly"] = True
        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", "Submit"))

    def clean(self) -> dict:
        """Validate that depth_bottom is not less than depth_top."""
        cleaned_data: dict = super().clean() or {}
        depth_top = cleaned_data.get("depth_top")
        depth_bottom = cleaned_data.get("depth_bottom")
        if (
            depth_top is not None
            and depth_bottom is not None
            and depth_bottom < depth_top
        ):
            msg = "Bottom depth must be greater than or equal to top depth."
            raise forms.ValidationError(msg)
        return cleaned_data


class TagForm(forms.ModelForm):
    """Form for creating and editing a Tag."""

    class Meta:
        """Form metadata for TagForm."""

        model = Tag
        fields = ["word", "slug", "project", "content_type"]

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Initialise the form and configure the crispy-forms helper."""
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", "Submit"))


class LayerForm(forms.ModelForm):
    """Form for creating and editing a Layer."""

    class Meta:
        """Form metadata for LayerForm."""

        model = Layer
        fields = [
            "location",
            "identifier",
            "token",
            "description",
            "depth_top",
            "depth_bottom",
            "structure",
            "fine_soil_field",
            "munsell_hue_value",
            "munsell_hue",
            "munsell_value",
            "munsell_chroma",
            "calcite",
            "secondary_calcite",
            "tags",
        ]

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Initialise the form and configure the crispy-forms helper."""
        super().__init__(*args, **kwargs)
        self.fields[
            "munsell_hue_value"
        ].help_text = "Numeric prefix of the hue page (0–10, step 0.5); e.g. 7.5 for 7.5YR."
        self.fields["munsell_hue"].help_text = "Hue letter code; e.g. YR."
        self.fields[
            "munsell_value"
        ].help_text = "Lightness value (0–10, step 0.5); e.g. 4."
        self.fields[
            "munsell_chroma"
        ].help_text = "Chroma/saturation (0–12, step 0.5); e.g. 6."
        self.helper = FormHelper()
        self.helper.layout = Layout(
            "location",
            Fieldset(
                "Identification",
                Row(
                    Column("identifier", css_class="form-group col-md-6"),
                    Column("token", css_class="form-group col-md-6"),
                ),
                "description",
            ),
            Fieldset(
                "Depth",
                Row(
                    Column("depth_top", css_class="form-group col-md-6"),
                    Column("depth_bottom", css_class="form-group col-md-6"),
                ),
            ),
            Fieldset(
                "Properties",
                Row(
                    Column("structure", css_class="form-group col-md-6"),
                    Column("fine_soil_field", css_class="form-group col-md-6"),
                ),
                Row(
                    Column("calcite", css_class="form-group col-md-6"),
                    Column(
                        "secondary_calcite", css_class="form-group col-md-6"
                    ),
                ),
            ),
            Fieldset(
                "Munsell Color",
                HTML(
                    '<p class="text-muted small mb-3">'
                    "Munsell notation: e.g. 7.5YR 4/6 → hue_value=7.5, hue=YR, value=4, chroma=6. "
                    "Step size for all numeric fields: 0.5."
                    "</p>"
                ),
                Row(
                    Column(
                        "munsell_hue_value", css_class="form-group col-md-3"
                    ),
                    Column("munsell_hue", css_class="form-group col-md-3"),
                    Column("munsell_value", css_class="form-group col-md-3"),
                    Column("munsell_chroma", css_class="form-group col-md-3"),
                ),
            ),
            "tags",
            Submit("submit", "Submit"),
        )
