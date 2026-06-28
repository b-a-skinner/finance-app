import os

from dotenv import load_dotenv

load_dotenv()

SECRET_KEY: str = os.environ.get("SECRET_KEY", "")
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30 days
