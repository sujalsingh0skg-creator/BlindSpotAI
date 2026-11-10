"""Out-of-band password reset code delivery over authenticated SMTP."""
from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage


def reset_delivery_configured() -> bool:
    return all(os.environ.get(name, "").strip() for name in ("SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_FROM"))


def send_reset_code(address: str, code: str) -> None:
    """Deliver a one-time code directly to the account email; never print it."""
    if not reset_delivery_configured():
        raise RuntimeError("Password reset email delivery is not configured.")
    host = os.environ["SMTP_HOST"].strip()
    port = int(os.environ.get("SMTP_PORT", "587"))
    username = os.environ["SMTP_USERNAME"]
    password = os.environ["SMTP_PASSWORD"]
    message = EmailMessage()
    message["Subject"] = "BlindSpot AI password reset"
    message["From"] = os.environ["SMTP_FROM"].strip()
    message["To"] = address
    message.set_content(
        "A BlindSpot AI administrator initiated a password reset for this account.\n\n"
        f"One-time reset code: {code}\n\n"
        "Enter this code on the BlindSpot AI password reset screen within one hour. "
        "If you did not expect this message, contact the site administrator."
    )
    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=15) as server:
            server.login(username, password)
            server.send_message(message)
    else:
        with smtplib.SMTP(host, port, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(username, password)
            server.send_message(message)
