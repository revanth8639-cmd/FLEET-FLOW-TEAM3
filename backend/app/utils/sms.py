"""Optional Twilio SMS delivery for account notifications."""

import base64
import re
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.core.config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER


def send_sms(receiver_phone: str | None, message: str) -> bool:
    """Send an SMS when Twilio is configured; otherwise leave delivery disabled."""
    if not receiver_phone:
        return False
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER]):
        print("[SMS NOT CONFIGURED] Role-change SMS was not sent")
        return False

    normalized_phone = re.sub(r"[\s()-]", "", receiver_phone)
    # FleetFlow's existing forms collect Indian 10-digit mobile numbers.
    if re.fullmatch(r"\d{10}", normalized_phone):
        normalized_phone = f"+91{normalized_phone}"
    if not re.fullmatch(r"\+\d{8,15}", normalized_phone):
        print("[SMS NOT SENT] The user's phone number must include a valid country code")
        return False

    credentials = base64.b64encode(f"{TWILIO_ACCOUNT_SID}:{TWILIO_AUTH_TOKEN}".encode()).decode()
    request = Request(
        f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json",
        data=urlencode({"To": normalized_phone, "From": TWILIO_FROM_NUMBER, "Body": message}).encode(),
        headers={"Authorization": f"Basic {credentials}", "Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=10):
            return True
    except (URLError, ValueError) as error:
        print("SMS ERROR:", error)
        return False
