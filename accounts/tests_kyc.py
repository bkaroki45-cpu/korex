import hashlib
import hmac
import json
import time

from django.test import TestCase, override_settings
from django.urls import reverse

from .kyc import canonical_json
from .models import DiditWebhookEvent, KYCVerification, User


@override_settings(DIDIT_WEBHOOK_SECRET="test-webhook-secret")
class DiditWebhookTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="kyc@example.com", username="kyc-user", password="password123")
        self.verification = KYCVerification.objects.create(user=self.user, didit_session_id="session-1", vendor_data=str(self.user.pk))

    def signed_post(self, payload, timestamp=None):
        timestamp = timestamp or str(int(time.time()))
        signature = hmac.new(b"test-webhook-secret", canonical_json(payload).encode(), hashlib.sha256).hexdigest()
        return self.client.post(reverse("didit_webhook"), data=json.dumps(payload), content_type="application/json", headers={"X-Signature-V2": signature, "X-Timestamp": timestamp})

    def test_approved_webhook_verifies_user_and_is_idempotent(self):
        payload = {"event_id": "event-approved", "webhook_type": "status.updated", "session_id": "session-1", "vendor_data": str(self.user.pk), "status": "Approved", "decision": {"id_verifications": [], "liveness_checks": []}}
        self.assertEqual(self.signed_post(payload).status_code, 200)
        self.verification.refresh_from_db(); self.user.refresh_from_db()
        self.assertEqual(self.verification.status, KYCVerification.Status.VERIFIED)
        self.assertTrue(self.user.is_verified)
        self.assertEqual(self.signed_post(payload).status_code, 200)
        self.assertEqual(DiditWebhookEvent.objects.count(), 1)

    def test_invalid_signature_and_stale_timestamp_are_rejected(self):
        payload = {"event_id": "event-rejected", "webhook_type": "status.updated", "session_id": "session-1", "status": "Approved"}
        response = self.client.post(reverse("didit_webhook"), data=json.dumps(payload), content_type="application/json", headers={"X-Signature-V2": "invalid", "X-Timestamp": str(int(time.time()))})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.signed_post(payload, str(int(time.time()) - 301)).status_code, 401)
        self.verification.refresh_from_db()
        self.assertEqual(self.verification.status, KYCVerification.Status.NOT_STARTED)
