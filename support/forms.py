from django import forms

from .models import SupportRequest
from .security import clean_support_text


class SupportRequestForm(forms.ModelForm):
    website = forms.CharField(required=False, widget=forms.HiddenInput, label="")

    class Meta:
        model = SupportRequest
        fields = ("name", "email", "subject", "message")
        widgets = {
            "message": forms.Textarea(attrs={"rows": 5, "maxlength": 1500}),
        }

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("We could not send that request. Please try again.")
        return ""

    def _clean_text_field(self, field, minimum):
        try:
            value = clean_support_text(self.cleaned_data.get(field, ""))
        except ValueError as error:
            raise forms.ValidationError(str(error)) from error
        if len(value) < minimum:
            raise forms.ValidationError("Please provide a little more detail.")
        return value

    def clean_name(self):
        return self._clean_text_field("name", 2)

    def clean_subject(self):
        return self._clean_text_field("subject", 3)

    def clean_message(self):
        return self._clean_text_field("message", 8)