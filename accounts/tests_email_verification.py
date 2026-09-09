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
        EmailVerificationCode.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(minutes=11))
        response = self.client.post(reverse("resend_email_verification"))
        self.assertRedirects(response, reverse("email_verification"))
        old.refresh_from_db()
        self.assertIsNotNone(old.used_at)

    def test_issued_email_is_professional_and_contains_code(self):
        from django.core import mail
        from .email_verification import issue_code
        issue_code(self.user)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Your CloudD 1 verification code", mail.outbox[0].subject)
        self.assertIn("expires in 10 minutes", mail.outbox[0].body)

    def test_password_reset_uses_a_separate_code_and_changes_password(self):
        from .email_verification import issue_code
        issue_code(self.user, EmailVerificationCode.Purpose.PASSWORD_RESET)
        reset_code = EmailVerificationCode.objects.get(user=self.user, purpose=EmailVerificationCode.Purpose.PASSWORD_RESET)
        # Test the full code entry path without exposing the random code in mail logs.
        reset_code.code_hash = make_password("654321")
        reset_code.save(update_fields=["code_hash"])
        response = self.client.post(reverse("password_reset_request"), {"email": self.user.email})
        self.assertRedirects(response, reverse("password_reset_confirm"))
        # The request issues a fresh code, which is substituted with a known test value.
        reset_code = EmailVerificationCode.objects.filter(user=self.user, purpose=EmailVerificationCode.Purpose.PASSWORD_RESET, used_at__isnull=True).latest("created_at")
        reset_code.code_hash = make_password("654321")
        reset_code.save(update_fields=["code_hash"])
        response = self.client.post(reverse("password_reset_confirm"), {"code": "654321", "new_password1": "New-safe-password-123", "new_password2": "New-safe-password-123"})
        self.assertRedirects(response, reverse("login"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("New-safe-password-123"))

    @patch("accounts.views.issue_code")
    def test_password_reset_resend_is_locked_until_code_expires(self, issue):
        self.client.post(reverse("password_reset_request"), {"email": self.user.email})
        EmailVerificationCode.objects.create(user=self.user, purpose=EmailVerificationCode.Purpose.PASSWORD_RESET, code_hash=make_password("123456"), expires_at=timezone.now() + timedelta(minutes=10))
        response = self.client.post(reverse("resend_password_reset_code"))
        self.assertRedirects(response, reverse("password_reset_confirm"))
        issue.assert_called_once_with(self.user, EmailVerificationCode.Purpose.PASSWORD_RESET)
