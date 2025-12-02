from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django.contrib.gis import forms

from .models import GrainSize


class GrainSizeForm(forms.ModelForm):
    class Meta:
        model = GrainSize
        fields = [
            "sample",
            "sample_weight",
            "method",
            "classes",
            "measured_data",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", "Submit"))
