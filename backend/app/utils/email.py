import smtplib
from email.mime.text import MIMEText

from app.core.config import MAIL_USERNAME, MAIL_PASSWORD, MAIL_FROM


def send_email(receiver_email: str, subject: str, body: str) -> bool:
    """Send an email using the configured SMTP account."""
    if not all([MAIL_USERNAME, MAIL_PASSWORD, MAIL_FROM]):
        print(f"[EMAIL NOT CONFIGURED] Could not email {receiver_email}")
        return False

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = MAIL_FROM
    msg["To"] = receiver_email
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587, timeout=10)
        server.starttls()
        server.login(MAIL_USERNAME, MAIL_PASSWORD)
        server.send_message(msg)
        return True
    except Exception as error:
        print("EMAIL ERROR:", error)
        return False
    finally:
        if "server" in locals():
            server.quit()


def send_otp_email(receiver_email: str, otp: str) -> bool:
    """Send OTP when SMTP is configured; otherwise keep local signup usable."""
    if not all([MAIL_USERNAME, MAIL_PASSWORD, MAIL_FROM]):
        print(f"[DEV OTP] {receiver_email}: {otp}")
        return False
    return send_email(receiver_email, "FleetFlow - Email Verification OTP", f"""
Hello,

Your FleetFlow verification OTP is: {otp}

This OTP is valid for 2 minutes.

Do not share this OTP with anyone.

Regards,
FleetFlow Team
""")
