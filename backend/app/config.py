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
#
# Falls back to the first configured CORS_ORIGINS entry (not straight to
# localhost) if FRONTEND_URL itself isn't set. CORS_ORIGINS *must* already be
# set correctly in any real deployment — the frontend can't call the API at
# all otherwise — so this fallback is far less likely to be silently wrong
# than an independent hardcoded default. (This is exactly the bug that shipped
# once already: FRONTEND_URL was undocumented and unset on Railway, so
# password reset emails linked to localhost:5173 in production — the link
# opened fine against a local dev frontend, which then validated the token
# against the wrong database and always failed with "invalid or has expired.")
_cors_origins_raw = os.environ.get("CORS_ORIGINS", "")
_first_cors_origin = next(
    (o.strip() for o in _cors_origins_raw.split(",") if o.strip()),
    "http://localhost:5173",
)
FRONTEND_URL: str = os.environ.get("FRONTEND_URL", _first_cors_origin)

if not SECRET_KEY:
    logging.warning("SECRET_KEY is not set — using an empty string is insecure in production.")

if not RESEND_API_KEY:
    logging.warning("RESEND_API_KEY is not set — emails will not be sent (fine for local dev).")

if FRONTEND_URL == "http://localhost:5173" and not os.environ.get("FRONTEND_URL"):
    logging.warning(
        "FRONTEND_URL is not set and no CORS_ORIGINS fallback was found either — "
        "defaulting to http://localhost:5173. Set FRONTEND_URL explicitly in production "
        "or links in emails (e.g. password reset) will point to the wrong place."
    )
