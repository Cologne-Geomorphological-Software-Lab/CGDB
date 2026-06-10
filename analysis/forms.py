"""Forms for the analysis app."""

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django.contrib.gis import forms

from .models import GrainSize


class GrainSizeForm(forms.ModelForm):
    """ModelForm for manually creating a GrainSize record."""

    class Meta:
        """Form metadata."""

        model = GrainSize
        fields = [
            "sample",
            "sample_weight",
            "method",
            "classes",
            "measured_data",
        ]

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Attach a crispy-forms helper with a Submit button."""
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", "Submit"))
