import logging
import os

from dotenv import load_dotenv

load_dotenv()

SECRET_KEY: str = os.environ.get("SECRET_KEY", "")
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30 days

if not SECRET_KEY:
    logging.warning("SECRET_KEY is not set — using an empty string is insecure in production.")
