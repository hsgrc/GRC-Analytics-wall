from __future__ import annotations

import re
import secrets
import threading
import time
from typing import Any


SESSION_TTL_SECONDS = 30 * 60

_sessions: dict[str, dict[str, Any]] = {}
_lock = threading.RLock()


def create_session(pending_question: str) -> tuple[str, dict[str, Any]]:
    """Create an in-memory session without storing customer PII."""
    now = time.monotonic()
    token = secrets.token_urlsafe(32)

    session = {
        "created_at": now,
        "last_activity": now,
        "pending_question": pending_question.strip(),
        "verified_customer_id": None,
    }

    with _lock:
        _remove_expired_sessions(now)
        _sessions[token] = session

    return token, session


def _remove_expired_sessions(now: float) -> None:
    expired = [
        token
        for token, session in _sessions.items()
        if now - session["last_activity"] > SESSION_TTL_SECONDS
    ]

    for token in expired:
        _sessions.pop(token, None)


def get_session(token: str | None) -> dict[str, Any] | None:
    if not token:
        return None

    now = time.monotonic()

    with _lock:
        _remove_expired_sessions(now)
        session = _sessions.get(token)

        if session is not None:
            session["last_activity"] = now

        return session


def parse_mobile_number(message: str) -> str | None:
    """Accept a standalone Indian mobile number."""
    text = str(message or "").strip()

    if not re.fullmatch(r"[+\d()\s-]+", text):
        return None

    digits = re.sub(r"\D", "", text)

    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]

    if len(digits) == 10 and digits[0] in "6789":
        return digits

    return None


def parse_name_mobile(message: str) -> tuple[str, str] | None:
    """
    Parse a registered customer name and Indian mobile number
    from one message, e.g. 'Full Name, 9876543210'.
    """
    text = str(message or "").strip()

    pattern = re.compile(
        r"(?<!\d)(?:\+?91[\s-]?)?(?:0)?([6-9]\d{9})(?!\d)"
    )
    match = pattern.search(text)

    if not match:
        return None

    name = (
        text[:match.start()] + " " + text[match.end():]
    )

    name = re.sub(r"[\s,;|]+", " ", name).strip(" .:-")

    if not name or not any(char.isalpha() for char in name):
        return None

    return name, match.group(1)


def mark_session_verified(
    session: dict[str, Any],
    customer_id: str,
) -> str:
    """Mark a matched customer and return the original pending question."""
    pending_question = session.get("pending_question", "")

    session["verified_customer_id"] = str(customer_id)
    session["pending_question"] = ""

    return pending_question


def is_session_verified(session: dict[str, Any] | None) -> bool:
    return bool(
        session
        and session.get("verified_customer_id")
    )
