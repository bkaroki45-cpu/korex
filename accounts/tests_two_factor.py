import time

from django.test import TestCase, override_settings
from django.urls import reverse

from .models import RecoveryCode, TwoFactorSettings
from .totp import _code, decrypt_secret, generate_recovery_codes, generate_secret, encrypt_secret


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class TwoFactorAuthenticationTests(TestCase):
    def setUp(self):
        self.user = self._create_user("totp@example.com")

    def _create_user(self, email):
        from .models import User
        return User.objects.create_user(username=email, email=email, password="A-safe-password-123")

    def _enable_two_factor(self, user=None):
        user = user or self.user
        secret = generate_secret()
        settings = TwoFactorSettings.objects.create(user=user, encrypted_secret=encrypt_secret(secret), is_enabled=True)
        codes = generate_recovery_codes(settings)
        return settings, secret, codes

    def test_setup_requires_valid_authenticator_code_and_stores_encrypted_secret(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("two_factor_setup"))
        secret = self.client.session["two_factor_enrollment_secret"]
        self.assertContains(response, secret)
        response = self.client.post(reverse("two_factor_setup"), {"code": _code(secret, 0)})
        self.assertEqual(response.status_code, 200)
        response = self.client.post(reverse("two_factor_setup"), {"code": _code(secret, int(time.time() // 30))})
        self.assertRedirects(response, reverse("two_factor_recovery_codes"))
        settings = TwoFactorSettings.objects.get(user=self.user)
        self.assertTrue(settings.is_enabled)
        self.assertNotEqual(settings.encrypted_secret, secret)
        self.assertEqual(decrypt_secret(settings.encrypted_secret), secret)
        self.assertEqual(settings.recovery_codes.count(), 10)

    def test_login_requires_totp_after_password(self):
        _, secret, _ = self._enable_two_factor()
        response = self.client.post(reverse("login"), {"username": self.user.email, "password": "A-safe-password-123"})
        self.assertRedirects(response, reverse("two_factor_verify"))
        response = self.client.post(reverse("two_factor_verify"), {"code": _code(secret, int(time.time() // 30))})
        self.assertRedirects(response, reverse("dashboard"))

    def test_recovery_code_is_one_time_and_forces_reenrollment(self):
        settings, _, codes = self._enable_two_factor()
        self.client.post(reverse("login"), {"username": self.user.email, "password": "A-safe-password-123"})
        response = self.client.post(reverse("two_factor_recovery_login"), {"code": codes[0]})
        self.assertRedirects(response, reverse("two_factor_setup"))
        self.assertTrue(RecoveryCode.objects.get(two_factor=settings, used_at__isnull=False))
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(response, reverse("two_factor_setup"))

    def test_recovery_code_cannot_be_reused(self):
        settings, _, codes = self._enable_two_factor()
        from .totp import use_recovery_code
        self.assertTrue(use_recovery_code(settings, codes[0]))
        self.assertFalse(use_recovery_code(settings, codes[0]))
