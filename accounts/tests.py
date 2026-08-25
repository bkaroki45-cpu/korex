from django.test import TestCase
from django.urls import reverse

from .models import User
from referrals.models import ReferralProfile


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
        self.assertTrue(user.referral_code)
        self.assertEqual(user.referral_code, user.referral_profile.referral_code)
        self.assertTrue(hasattr(user, "wallet"))

    def test_user_can_log_in_with_email_and_password(self):
        User.objects.create_user(username="ada@gmail.com", email="ada@gmail.com", password="VeryStrongPassword123!")
        response = self.client.post(reverse("login"), {"username": "ada@gmail.com", "password": "VeryStrongPassword123!"})
        self.assertRedirects(response, reverse("dashboard"))

    def test_multiple_people_can_register_with_different_email_addresses(self):
        for first_name, email in (("Ada", "ada@example.com"), ("Grace", "grace@example.com")):
            response = self.client.post(reverse("signup"), {
                "first_name": first_name, "last_name": "Member", "email": email,
                "country": "KE", "dial_code": "+254", "phone_local": "712345678",
                "password1": "VeryStrongPassword123!", "password2": "VeryStrongPassword123!",
            })
            self.assertRedirects(response, reverse("dashboard"))
            self.client.post(reverse("logout"))
        self.assertEqual(User.objects.filter(email__in=["ada@example.com", "grace@example.com"]).count(), 2)

    def test_logout_ends_the_authenticated_session(self):
        user = User.objects.create_user(username="member@example.com", email="member@example.com", password="VeryStrongPassword123!")
        self.client.force_login(user)
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_invitation_link_redirects_to_locked_registration_code(self):
        referrer = User.objects.create_user(username="referrer@example.com", email="referrer@example.com", password="StrongPassword123!")
        code = ReferralProfile.objects.get(user=referrer).referral_code
        response = self.client.get(reverse("referrals:join", kwargs={"code": code}))
        self.assertRedirects(response, f"{reverse('signup')}?ref={code}")
        registration = self.client.get(response.url)
        self.assertContains(registration, 'name="referrer_code"')
        self.assertContains(registration, 'disabled')

    def test_invitation_link_signs_out_an_existing_session_for_registration(self):
        referrer = User.objects.create_user(username="referrer2@example.com", email="referrer2@example.com", password="StrongPassword123!")
        visitor = User.objects.create_user(username="visitor@example.com", email="visitor@example.com", password="StrongPassword123!")
        self.client.force_login(visitor)
        code = ReferralProfile.objects.get(user=referrer).referral_code
        response = self.client.get(reverse("referrals:join", kwargs={"code": code}))
        self.assertRedirects(response, f"{reverse('signup')}?ref={code}")
        self.assertNotIn("_auth_user_id", self.client.session)
        registration = self.client.get(response.url)
        self.assertContains(registration, 'name="referrer_code"')
        self.assertContains(registration, 'disabled')
