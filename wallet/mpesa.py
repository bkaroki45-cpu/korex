import base64
import json
from datetime import datetime
from decimal import Decimal, ROUND_UP
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.cache import cache

USDT_KES_URL = "https://api.coingecko.com/api/v3/simple/price?ids=tether&vs_currencies=kes"
MINIMUM_MPESA_USDT = Decimal("500")


class MpesaError(ValueError):
    pass


def configured():
    return all((settings.MPESA_CONSUMER_KEY, settings.MPESA_CONSUMER_SECRET, settings.MPESA_PASSKEY, settings.MPESA_SHORTCODE))


def normalize_phone(value):
    digits = "".join(character for character in value if character.isdigit())
    if digits.startswith("0"):
        digits = "254" + digits[1:]
    elif digits.startswith(("7", "1")):
        digits = "254" + digits
    if len(digits) != 12 or not digits.startswith("254"):
        raise MpesaError("Enter a valid Kenyan M-Pesa phone number.")
    return digits


def _request(url, payload=None, headers=None):
    request = Request(url, data=payload, headers=headers or {}, method="POST" if payload else "GET")
    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read())
    except (HTTPError, URLError, ValueError) as error:
        raise MpesaError("M-Pesa is temporarily unavailable. Please try again.") from error


def access_token():
    cached = cache.get("mpesa_access_token")
    if cached:
        return cached
    credential = base64.b64encode(f"{settings.MPESA_CONSUMER_KEY}:{settings.MPESA_CONSUMER_SECRET}".encode()).decode()
    response = _request(f"{settings.MPESA_BASE_URL}/oauth/v1/generate?grant_type=client_credentials", headers={"Authorization": f"Basic {credential}"})
    token = response.get("access_token")
    if not token:
        raise MpesaError("M-Pesa authorization failed. Please try again later.")
    cache.set("mpesa_access_token", token, max(int(response.get("expires_in", 3599)) - 60, 60))
    return token


def _stk_credentials():
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password = base64.b64encode(f"{settings.MPESA_SHORTCODE}{settings.MPESA_PASSKEY}{timestamp}".encode()).decode()
    return timestamp, password


def initiate_stk_push(amount, phone, reference):
    if not configured():
        raise MpesaError("M-Pesa sandbox is not configured yet.")
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password = base64.b64encode(f"{settings.MPESA_SHORTCODE}{settings.MPESA_PASSKEY}{timestamp}".encode()).decode()
    payload = json.dumps({"BusinessShortCode": settings.MPESA_SHORTCODE, "Password": password, "Timestamp": timestamp, "TransactionType": "CustomerPayBillOnline", "Amount": int(amount), "PartyA": phone, "PartyB": settings.MPESA_SHORTCODE, "PhoneNumber": phone, "CallBackURL": settings.MPESA_CALLBACK_URL, "AccountReference": reference, "TransactionDesc": "CLOUDD 1 sandbox deposit"}).encode()
    response = _request(f"{settings.MPESA_BASE_URL}/mpesa/stkpush/v1/processrequest", payload, {"Authorization": f"Bearer {access_token()}", "Content-Type": "application/json"})
    if response.get("ResponseCode") != "0" or not response.get("CheckoutRequestID"):
        raise MpesaError(response.get("errorMessage") or response.get("ResponseDescription") or "M-Pesa could not start the prompt.")
    return response

def current_usdt_kes_rate():
    cached = cache.get("mpesa_usdt_kes_rate")
    if cached:
        return Decimal(cached)
    response = _request(USDT_KES_URL, headers={"Accept": "application/json", "User-Agent": "CLOUDD1-Payments/1.0"})
    try:
        rate = Decimal(str(response["tether"]["kes"]))
    except (KeyError, TypeError, ValueError) as error:
        raise MpesaError("Current USDT pricing is unavailable. Please try again.") from error
    if rate <= 0:
        raise MpesaError("Current USDT pricing is unavailable. Please try again.")
    cache.set("mpesa_usdt_kes_rate", str(rate), 30)
    return rate


def quote_usdt_purchase(value):
    try:
        usdt_amount = Decimal(str(value)).quantize(Decimal("0.00000001"))
    except Exception as error:
        raise MpesaError("Enter a valid USDT amount.") from error
    if usdt_amount < MINIMUM_MPESA_USDT:
        raise MpesaError("Minimum M-Pesa deposit is 500 USDT.")
    rate = current_usdt_kes_rate()
    amount_kes = (usdt_amount * rate).quantize(Decimal("1"), rounding=ROUND_UP)
    return usdt_amount, rate, amount_kes

def query_stk_status(checkout_request_id):
    """Confirm a callback with Safaricom before crediting a wallet."""
    timestamp, password = _stk_credentials()
    payload = json.dumps({
        "BusinessShortCode": settings.MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "CheckoutRequestID": checkout_request_id,
    }).encode()
    return _request(
        f"{settings.MPESA_BASE_URL}/mpesa/stkpushquery/v1/query", payload,
        {"Authorization": f"Bearer {access_token()}", "Content-Type": "application/json"},
    )