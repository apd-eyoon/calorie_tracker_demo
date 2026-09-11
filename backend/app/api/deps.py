"""Shared FastAPI dependencies (DB session + authenticated user)."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db import queries
from app.db.session import get_db
from app.models.user import User

# auto_error=False lets us raise a consistent 401 (with WWW-Authenticate) for
# both "missing" and "invalid" credentials.
bearer_scheme = HTTPBearer(auto_error=False)

CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Validate the ``Authorization: Bearer <jwt>`` header and load the user."""
    if credentials is None or not credentials.credentials:
        raise CREDENTIALS_EXCEPTION
    if (credentials.scheme or "").lower() != "bearer":
        raise CREDENTIALS_EXCEPTION

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise CREDENTIALS_EXCEPTION

    subject = payload.get("sub") or payload.get("user_id")
    if not subject:
        raise CREDENTIALS_EXCEPTION

    try:
        user_id = uuid.UUID(str(subject))
    except (ValueError, AttributeError, TypeError):
        raise CREDENTIALS_EXCEPTION

    user = queries.get_user_by_id(db, user_id)
    if user is None:
        raise CREDENTIALS_EXCEPTION
    return user


__all__ = ["get_db", "get_current_user", "bearer_scheme"]
