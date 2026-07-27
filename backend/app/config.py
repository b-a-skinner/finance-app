import logging
import os

from dotenv import load_dotenv

load_dotenv()

SECRET_KEY: str = os.environ.get("SECRET_KEY", "")
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30 days

# Resend (transactional email) — see app/email.py. Optional: the app must start
# and function without it, just skip sending (logged) when unset.
RESEND_API_KEY: str = os.environ.get("RESEND_API_KEY", "")
EMAIL_FROM: str = "noreply@fivera.co.uk"

# Base URL of the deployed frontend — used to build links inside emails
# (e.g. password reset). Differs per environment; never hardcode it inline.
FRONTEND_URL: str = os.environ.get("FRONTEND_URL", "http://localhost:5173")

if not SECRET_KEY:
    logging.warning("SECRET_KEY is not set — using an empty string is insecure in production.")

if not RESEND_API_KEY:
    logging.warning("RESEND_API_KEY is not set — emails will not be sent (fine for local dev).")
