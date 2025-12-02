from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Layout, Row, Submit
from django.contrib.gis import forms

from .models import Campaign, Layer, Location, Project, Sample, Site, StudyArea, Tag


class CampaignForm(forms.ModelForm):
    class Meta:
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
                }
            ),
            "date_start": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "date_end": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "destination_country": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "season": forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        project_id = kwargs.pop("project_id", None)
        super().__init__(*args, **kwargs)
        self.fields["project"].widget.attrs["readonly"] = True

        if project_id is not None:
            try:
                project = Project.objects.get(id=project_id)
                self.initial["project"] = project
            except Project.DoesNotExist:
                pass
        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", "Submit"))


class LocationForm(forms.ModelForm):
    class Meta:
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["processor"].widget.attrs["readonly"] = True
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.add_input(Submit("submit", "Save Location"))


class StudyAreaForm(forms.ModelForm):
    class Meta:
        model = StudyArea
        fields = [
            "label",
            "project",
            "province",
            "climate_koeppen",
            "ecozone_schultz",
            "geometry",
        ]
        widgets = {"area": forms.OSMWidget(attrs={"map_width": 800, "map_height": 500})}

    def __init__(self, *args, **kwargs):
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
    class Meta:
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
            "depth_mid",
        ]

        widgets = {
            "location": forms.HiddenInput(
                attrs={
                    "class": "form-control",
                    "readonly": "readonly",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        location = kwargs.pop("location", None)
        super().__init__(*args, **kwargs)
        if location:
            self.initial["location"] = location
            self.fields["location"].widget.attrs["readonly"] = True
        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", "Submit"))


class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ["word", "slug", "project", "content_type"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", "Submit"))


class LayerForm(forms.ModelForm):
    class Meta:
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", "Submit"))
