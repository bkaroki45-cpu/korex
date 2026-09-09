from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.hashers import make_password
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import EmailVerificationCode, TrustedDevice, User


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    EMAIL_HOST_USER="brevo-user", EMAIL_HOST_PASSWORD="brevo-key", DEFAULT_FROM_EMAIL="no-reply@example.com",
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
)
class EmailVerificationTests(TestCase):
    password = "A-safe-password-123"

    def setUp(self):
        self.user = User.objects.create_user(username="email@example.com", email="email@example.com", password=self.password)

    def _pending_code(self, code="123456", expired=False):
        return EmailVerificationCode.objects.create(user=self.user, code_hash=make_password(code), expires_at=timezone.now() - timedelta(seconds=1) if expired else timezone.now() + timedelta(minutes=10))

    @patch("accounts.views.issue_code")
    def test_untrusted_existing_user_must_verify_email_before_dashboard(self, send_code):
        response = self.client.post(reverse("login"), {"username": self.user.email, "password": self.password})
        self.assertRedirects(response, reverse("email_verification"))
        send_code.assert_called_once_with(self.user)
        self._pending_code()
        response = self.client.post(reverse("email_verification"), {"code": "123456"})
        self.assertRedirects(response, reverse("dashboard"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_verified)
        self.assertEqual(TrustedDevice.objects.filter(user=self.user).count(), 1)
        self.assertIn("cloudd1_trusted_device", response.cookies)

    @patch("accounts.views.issue_code")
    def test_trusted_device_skips_email_code(self, send_code):
        from .email_verification import create_trusted_device
        _, token = create_trusted_device(self.user, RequestFactory().get("/"))
        self.client.cookies["cloudd1_trusted_device"] = token
        response = self.client.post(reverse("login"), {"username": self.user.email, "password": self.password})
        self.assertRedirects(response, reverse("dashboard"))
        send_code.assert_not_called()

    def test_wrong_expired_and_resend_codes_cannot_work(self):
        self.client.post(reverse("login"), {"username": self.user.email, "password": self.password})
        self._pending_code("111111", expired=True)
        response = self.client.post(reverse("email_verification"), {"code": "111111"})
        self.assertEqual(response.status_code, 200)
        EmailVerificationCode.objects.filter(user=self.user).delete()
        old = self._pending_code("222222")
        EmailVerificationCode.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(minutes=2))
        response = self.client.post(reverse("resend_email_verification"))
        self.assertRedirects(response, reverse("email_verification"))
        old.refresh_from_db()
        self.assertIsNotNone(old.used_at)

    def test_issued_email_is_professional_and_contains_code(self):
        from django.core import mail
        from .email_verification import issue_code
        issue_code(self.user)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("CloudD 1 security verification code", mail.outbox[0].subject)
        self.assertIn("expires in 10 minutes", mail.outbox[0].body)
