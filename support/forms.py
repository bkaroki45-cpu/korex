from django import forms

from .models import SupportRequest


class SupportRequestForm(forms.ModelForm):
    class Meta:
        model = SupportRequest
        fields = ("name", "email", "subject", "message")
        widgets = {
            "message": forms.Textarea(attrs={"rows": 5}),
        }
