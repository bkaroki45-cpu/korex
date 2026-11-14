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
    def test_existing_user_can_sign_in_without_an_email_code(self, send_code):
        response = self.client.post(reverse("login"), {"username": self.user.email, "password": self.password})
        self.assertRedirects(response, reverse("dashboard"))
        send_code.assert_not_called()

    def test_issued_email_is_professional_and_contains_code(self):
        from django.core import mail
        from .email_verification import issue_code
        issue_code(self.user)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Your CloudD 1 verification code", mail.outbox[0].subject)
        self.assertIn("expires in 10 minutes", mail.outbox[0].body)

    def test_welcome_email_is_sent_after_successful_signup(self):
        from django.core import mail
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse("signup"), {
                "first_name": "New", "last_name": "Member", "email": "new@example.com", "country": "KE",
                "dial_code": "+254", "phone_local": "712345678", "password1": "VeryStrongPassword123!", "password2": "VeryStrongPassword123!",
            })
        self.assertRedirects(response, reverse("email_verification"))
        self.assertTrue(any(email.subject == "Welcome to CLOUDD 1" for email in mail.outbox))

    def test_authentication_pages_are_not_cacheable(self):
        response = self.client.get(reverse("login"))
        self.assertIn("no-store", response["Cache-Control"])

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
