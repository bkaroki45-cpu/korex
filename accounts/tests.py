from django.test import TestCase
from django.urls import reverse

from .models import User


class AuthenticationFlowTests(TestCase):
    def test_signup_creates_user_wallet_and_redirects_to_dashboard(self):
        response = self.client.post(reverse("signup"), {
            "first_name": "Ada", "last_name": "Lovelace", "email": "ada@gmail.com",
            "country": "KE", "dial_code": "+254", "phone_local": "712345678",
            "password1": "VeryStrongPassword123!", "password2": "VeryStrongPassword123!",
        })
        self.assertRedirects(response, reverse("dashboard"))
        user = User.objects.get(email="ada@gmail.com")
        self.assertEqual(user.phone_number, "+254712345678")
        self.assertTrue(user.account_id.startswith("CDD-"))
        self.assertTrue(hasattr(user, "wallet"))

    def test_user_can_log_in_with_email_and_password(self):
        User.objects.create_user(username="ada@gmail.com", email="ada@gmail.com", password="VeryStrongPassword123!")
        response = self.client.post(reverse("login"), {"username": "ada@gmail.com", "password": "VeryStrongPassword123!"})
        self.assertRedirects(response, reverse("dashboard"))
