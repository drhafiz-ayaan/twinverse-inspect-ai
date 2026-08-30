"""Password hashing and JWT issuance.

bcrypt for passwords, HS256 for tokens. Both are boring, well-understood
choices; this is not the place to be interesting.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings

ALGORITHM = "HS256"


def hash_password(plain: str) -> str:
    """bcrypt has a hard 72-byte input limit and silently truncates beyond it.

    Truncating turns a long passphrase into a shorter effective secret without
    telling anyone, so over-long input is rejected rather than quietly cut.
    """
    raw = plain.encode("utf-8")
    if len(raw) > 72:
        raise ValueError("password must be at most 72 bytes")
    return bcrypt.hashpw(raw, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        # A malformed stored hash must fail closed, not raise into a 500 that
        # distinguishes "corrupt record" from "wrong password".
        return False


def create_access_token(subject: uuid.UUID, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(subject),
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
        "typ": "access",
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """Return the claims, or None for anything not a valid access token.

    Signature, expiry and token type are all checked here so callers cannot
    forget one.
    """
    try:
        claims = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
    if claims.get("typ") != "access":
        return None
    return claims
