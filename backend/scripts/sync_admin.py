#!/usr/bin/env python3
"""Apply BOOTSTRAP_ADMIN_EMAIL / BOOTSTRAP_ADMIN_PASSWORD to a live database.

The startup bootstrap deliberately runs only when the users table is empty, so
it can never resurrect a deliberately deleted account. The consequence catches
people out: editing those two values in `.env` and restarting does nothing at
all once an admin exists, and you are left signing in with credentials you
believe you have already changed.

This closes that gap explicitly rather than by weakening the startup rule.

    cd backend && PYTHONPATH=. python scripts/sync_admin.py

Creates the account if the address is new, resets the password if it already
exists, and always prints what it did. Never prints the password itself.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pydantic import ValidationError  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.core import security  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.db.models import User, UserRole  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.schemas.auth import LoginRequest  # noqa: E402


def main() -> int:
    email = settings.bootstrap_admin_email
    password = settings.bootstrap_admin_password

    if not (email and password):
        print(
            "BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD are not both set "
            "in backend/.env — nothing to apply.",
            file=sys.stderr,
        )
        return 1

    # Same validation the login endpoint applies. Without it you can write an
    # address the ORM accepts but /auth/login rejects — an account that exists
    # and can never be used. Reserved TLDs like .local and .test do this.
    try:
        LoginRequest(email=email, password=password)
    except ValidationError as exc:
        detail = exc.errors()[0].get("msg", "")
        print(f"refusing to apply: {email!r} — {detail}", file=sys.stderr)
        return 1

    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            db.add(
                User(
                    email=email,
                    hashed_password=security.hash_password(password),
                    full_name="Administrator",
                    role=UserRole.ADMIN,
                    is_active=True,
                )
            )
            db.commit()
            print(f"created admin {email}")
        else:
            user.hashed_password = security.hash_password(password)
            # A password reset on a disabled or demoted account is almost
            # always an attempt to regain access, so restore both.
            user.role = UserRole.ADMIN
            user.is_active = True
            db.commit()
            print(f"updated password for {email}")

        others = [
            u.email
            for u in db.scalars(
                select(User).where(User.role == UserRole.ADMIN, User.email != email)
            )
        ]
        if others:
            print(
                "\nother admin accounts still exist and still have their old "
                "passwords:\n  " + "\n  ".join(others)
            )
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
