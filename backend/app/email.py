"""
Minimal, provider-agnostic email sending — currently backed by Resend.

send_email() never raises: a broken or unreachable email provider must never
crash the request that triggered a send, and provider error detail must never
reach the end user. Failures are logged and swallowed; callers get a bool.
"""
import logging

import httpx

from app.config import EMAIL_FROM, RESEND_API_KEY

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


def send_email(to: str, subject: str, html: str) -> bool:
    """Sends an email via the configured provider. Returns True if accepted, False otherwise."""
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not set — skipping email to %s (subject: %r)", to, subject)
        return False

    try:
        response = httpx.post(
            RESEND_API_URL,
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={"from": EMAIL_FROM, "to": [to], "subject": subject, "html": html},
            timeout=10.0,
        )
        if response.status_code >= 400:
            logger.error("Email send failed (status %s) sending to %s", response.status_code, to)
            return False
        return True
    except httpx.HTTPError:
        logger.exception("Email send raised an exception sending to %s", to)
        return False
