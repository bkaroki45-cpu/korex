from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import User


COUNTRIES = [
    ("KE", "🇰🇪 Kenya"), ("UG", "🇺🇬 Uganda"), ("TZ", "🇹🇿 Tanzania"),
    ("RW", "🇷🇼 Rwanda"), ("NG", "🇳🇬 Nigeria"), ("ZA", "🇿🇦 South Africa"),
    ("GH", "🇬🇭 Ghana"), ("US", "🇺🇸 United States"), ("GB", "🇬🇧 United Kingdom"),
    ("CA", "🇨🇦 Canada"), ("IN", "🇮🇳 India"), ("OTHER", "🌍 Other"),
]
DIAL_CODES = [
    ("+254", "🇰🇪 +254 (Kenya)"), ("+256", "🇺🇬 +256 (Uganda)"),
    ("+255", "🇹🇿 +255 (Tanzania)"), ("+250", "🇷🇼 +250 (Rwanda)"),
    ("+234", "🇳🇬 +234 (Nigeria)"), ("+27", "🇿🇦 +27 (South Africa)"),
    ("+233", "🇬🇭 +233 (Ghana)"), ("+1", "🇺🇸 +1 (US/Canada)"),
    ("+44", "🇬🇧 +44 (United Kingdom)"), ("+91", "🇮🇳 +91 (India)"),
]


class SignUpForm(UserCreationForm):
    dial_code = forms.ChoiceField(choices=DIAL_CODES, label="Dial code")
    phone_local = forms.CharField(max_length=16, label="Phone number")
    country = forms.ChoiceField(choices=COUNTRIES)
    referral_code = forms.CharField(max_length=20, required=False, label="Referral code (optional)")
    withdrawal_address = forms.CharField(max_length=255, label="Crypto withdrawal address")
    withdrawal_network = forms.ChoiceField(choices=(), label="Withdrawal network")

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "country", "dial_code", "phone_local", "withdrawal_address", "withdrawal_network", "referral_code", "password1", "password2")
        labels = {"first_name": "First name", "last_name": "Last name", "email": "Email address"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True
        self.fields["last_name"].required = True
        self.fields["email"].widget.attrs.update({"autocomplete": "email", "placeholder": "you@gmail.com"})
        self.fields["phone_local"].widget.attrs.update({"inputmode": "tel", "placeholder": "712 345 678"})
        if self.initial.get("referral_code"):
            self.fields["referral_code"].initial = self.initial["referral_code"]
        self.fields["password1"].widget.attrs["autocomplete"] = "new-password"
        self.fields["password2"].widget.attrs["autocomplete"] = "new-password"
        from wallet.models import WithdrawalNetwork
        networks = WithdrawalNetwork.objects.filter(is_enabled=True).values_list("code", "name")
        self.fields["withdrawal_network"].choices = list(networks) or [("TRC20", "TRC20")]

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

    def clean_phone_local(self):
        value = self.cleaned_data["phone_local"].replace(" ", "").replace("-", "")
        if not value.isdigit() or len(value) < 6:
            raise forms.ValidationError("Enter a valid phone number.")
        return value

    def clean_referral_code(self):
        return self.cleaned_data["referral_code"].strip().upper()

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data["email"]
        user.phone_number = f"{self.cleaned_data['dial_code']}{self.cleaned_data['phone_local']}"
        user.country = self.cleaned_data["country"]
        user.withdrawal_address = self.cleaned_data["withdrawal_address"].strip()
        user.withdrawal_network = self.cleaned_data["withdrawal_network"]
        if commit:
            user.save()
        return user


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(label="Email address")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs["autocomplete"] = "email"
        self.fields["password"].widget.attrs["autocomplete"] = "current-password"


class WithdrawalDetailsForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("withdrawal_address", "withdrawal_network")
        labels = {"withdrawal_address": "Crypto withdrawal address", "withdrawal_network": "Network"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from wallet.models import WithdrawalNetwork
        self.fields["withdrawal_network"] = forms.ChoiceField(
            choices=list(WithdrawalNetwork.objects.filter(is_enabled=True).values_list("code", "name")) or [("TRC20", "TRC20")],
            initial=self.instance.withdrawal_network,
        )
