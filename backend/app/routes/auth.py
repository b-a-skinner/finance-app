import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, FRONTEND_URL, SECRET_KEY
from app.database import get_db
from app.email import send_email
from app.models import PasswordResetToken, User
from app.security import hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

# tokenUrl tells Swagger UI (and OAuth2 clients) where to POST credentials to get a token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

RESET_TOKEN_TTL = timedelta(hours=1)

# The generic response for /forgot-password — identical regardless of whether the
# email is registered. Never change this to differ based on lookup results.
FORGOT_PASSWORD_MESSAGE = "If an account exists for that email, we've sent a reset link."

# ---------------------------------------------------------------------------
# Basic in-process rate limiting for /forgot-password.
# Not distributed — resets on process restart and doesn't share state across
# multiple instances. That's an acceptable trade-off for a "basic" throttle on
# a single-service deployment; a shared store (e.g. Redis) would be needed to
# do this properly across multiple instances.
# ---------------------------------------------------------------------------
_rate_limit_hits: dict[str, list[datetime]] = {}
RATE_LIMIT_WINDOW = timedelta(minutes=15)
RATE_LIMIT_MAX_ATTEMPTS = 5


def _rate_limited(key: str) -> bool:
    now = datetime.now(timezone.utc)
    hits = _rate_limit_hits.setdefault(key, [])
    hits[:] = [t for t in hits if now - t < RATE_LIMIT_WINDOW]
    if len(hits) >= RATE_LIMIT_MAX_ATTEMPTS:
        return True
    hits.append(now)
    return False


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: str
    password: str


class RegisterResponse(BaseModel):
    message: str
    user_id: int


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class ForgotPasswordRequest(BaseModel):
    email: str


class MessageResponse(BaseModel):
    message: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        # Full-precision unix timestamp (not the auto-converted datetime form
        # jose uses for "exp") so a reset a moment after login is still
        # distinguishable from the token that was just issued.
        "iat": now.timestamp(),
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _validate_new_password(password: str) -> str | None:
    if len(password) < 8:
        return "Password must be at least 8 characters."
    return None


def _aware(dt: datetime) -> datetime:
    """SQLite can round-trip DateTime(timezone=True) columns as naive — normalize to UTC."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _reset_email_html(reset_link: str) -> str:
    return f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 480px; margin: 0 auto; color: #111827; line-height: 1.5;">
      <p style="font-size: 1.1rem; font-weight: 700; margin-bottom: 1.5rem;">fivera</p>
      <p>We received a request to reset your password.</p>
      <p style="margin: 1.5rem 0;">
        <a href="{reset_link}" style="background: #1a3a5c; color: #ffffff; padding: 0.75rem 1.25rem; border-radius: 8px; text-decoration: none; display: inline-block;">
          Reset your password
        </a>
      </p>
      <p style="color: #6b7280; font-size: 0.9rem;">
        This link expires in 1 hour. If you didn't request this, you can safely ignore this
        email — your password won't be changed.
      </p>
    </div>
    """


def _send_reset_email(email: str, raw_token: str) -> None:
    reset_link = f"{FRONTEND_URL}/reset-password?token={raw_token}"
    send_email(to=email, subject="Reset your fivera password", html=_reset_email_html(reset_link))


# ---------------------------------------------------------------------------
# Dependency — use this in any route that requires a logged-in user
# ---------------------------------------------------------------------------

def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Session = Depends(get_db),
) -> User:
    """
    Decodes the Bearer token from the Authorization header and returns the User it belongs to.
    Raises HTTP 401 if the token is missing, expired, invalid, or was issued before
    the user's most recent password reset.
    """
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
        issued_at = payload.get("iat")
    except (JWTError, KeyError, ValueError):
        raise unauthorized

    user = db.query(User).filter_by(id=user_id).first()
    if user is None:
        raise unauthorized

    # Soft-revoke tokens issued before the user's most recent password reset.
    # There's no server-side session/blacklist store with the current stateless
    # JWT design, so this is how a reset invalidates existing sessions.
    if user.token_valid_after is not None and issued_at is not None:
        if issued_at < _aware(user.token_valid_after).timestamp():
            raise unauthorized

    return user


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter_by(email=body.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    user = User(email=body.email, password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return RegisterResponse(message="User created successfully", user_id=user.id)


@router.post("/login", response_model=TokenResponse)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db),
):
    # OAuth2PasswordRequestForm uses the field name `username` — we treat it as email
    user = db.query(User).filter_by(email=form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(
        access_token=_create_access_token(user.id),
        token_type="bearer",
    )


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(
    body: ForgotPasswordRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Always returns the same response regardless of whether the email is
    registered — never reveals which emails exist (same principle as
    get_owned_or_404 for resource ownership).
    """
    client_host = request.client.host if request.client else "unknown"
    email_key = f"email:{body.email.strip().lower()}"
    ip_key = f"ip:{client_host}"
    if _rate_limited(email_key) or _rate_limited(ip_key):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests. Please try again later.")

    user = db.query(User).filter_by(email=body.email.strip()).first()
    if user is not None:
        now = datetime.now(timezone.utc)

        # Invalidate any previous unused tokens for this user.
        db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        ).update({"used_at": now}, synchronize_session=False)

        raw_token = secrets.token_urlsafe(32)
        db.add(PasswordResetToken(
            user_id=user.id,
            token_hash=_hash_token(raw_token),
            expires_at=now + RESET_TOKEN_TTL,
        ))
        db.commit()

        # Sent after the response goes out — a slow or unreachable email
        # provider never delays or fails the request itself.
        background_tasks.add_task(_send_reset_email, user.email, raw_token)

    return MessageResponse(message=FORGOT_PASSWORD_MESSAGE)


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)):
    password_error = _validate_new_password(body.new_password)
    if password_error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=password_error)

    invalid = HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This reset link is invalid or has expired.")

    token_row = db.query(PasswordResetToken).filter_by(token_hash=_hash_token(body.token)).first()
    now = datetime.now(timezone.utc)
    if token_row is None or token_row.used_at is not None or _aware(token_row.expires_at) < now:
        raise invalid

    user = db.query(User).filter_by(id=token_row.user_id).first()
    if user is None:
        raise invalid

    user.password_hash = hash_password(body.new_password)
    user.token_valid_after = now  # soft-invalidate existing JWT sessions

    token_row.used_at = now
    # Invalidate any other outstanding tokens for this user too.
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.id != token_row.id,
        PasswordResetToken.used_at.is_(None),
    ).update({"used_at": now}, synchronize_session=False)

    db.commit()
    return MessageResponse(message="Your password has been reset. You can now sign in with your new password.")
