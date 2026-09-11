"""Password hashing (bcrypt via passlib) and JWT creation/validation."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# bcrypt has a hard 72-byte input limit; passlib raises on longer secrets in
# newer backends, so we truncate defensively before hashing/verifying.
_BCRYPT_MAX_BYTES = 72

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _prepare(password: str) -> str:
    encoded = password.encode("utf-8")
    if len(encoded) <= _BCRYPT_MAX_BYTES:
        return password
    return encoded[:_BCRYPT_MAX_BYTES].decode("utf-8", "ignore")


def hash_password(password: str) -> str:
    """Return a bcrypt hash for ``password``."""
    return pwd_context.hash(_prepare(password))


def verify_password(password: str, password_hash: str) -> bool:
    """Constant-time verification of a plaintext password against its hash."""
    try:
        return pwd_context.verify(_prepare(password), password_hash)
    except Exception:  # malformed hash, unknown scheme, ...
        return False


def create_access_token(
    user_id: uuid.UUID | str,
    *,
    expires_minutes: Optional[int] = None,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """Issue a signed JWT whose ``sub`` claim carries the user id."""
    now = datetime.now(timezone.utc)
    minutes = (
        settings.jwt_expires_minutes if expires_minutes is None else expires_minutes
    )
    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "user_id": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=minutes)).timestamp()),
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode & verify a JWT. Returns ``None`` when the token is not valid."""
    try:
        return jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except JWTError:
        return None


def token_expires_in_seconds(expires_minutes: Optional[int] = None) -> int:
    minutes = (
        settings.jwt_expires_minutes if expires_minutes is None else expires_minutes
    )
    return minutes * 60
