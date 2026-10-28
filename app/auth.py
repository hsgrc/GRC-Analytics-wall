from __future__ import annotations

import os
import re
from dataclasses import dataclass

import jwt
from fastapi import HTTPException, Request


@dataclass(frozen=True)
class WebsiteIdentity:
    """Identity verified from a signed website-issued access token."""

    user_id: str
    mobile: str


def _normalize_indian_mobile(value: object) -> str | None:
    digits = re.sub(r"\D", "", str(value or ""))

    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]

    if len(digits) != 10 or digits[0] not in "6789":
        return None

    return digits


def get_authenticated_website_user(request: Request) -> WebsiteIdentity:
    """
    Verify a short-lived RS256 token issued by the trusted website backend.

    Expected signed claims:
      sub          Website's stable user ID
      phone_number User's verified, registered Indian mobile number
      iss          Configured website token issuer
      aud          Configured chatbot audience
      iat, exp     Token issue and expiry timestamps

    The website's private signing key must never be stored in this chatbot.
    """
    authorization = request.headers.get("Authorization", "")
    scheme, _, token = authorization.partition(" ")

    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(
            status_code=401,
            detail="Please sign in through the GetRightCover website.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    public_key = os.getenv("WEBSITE_JWT_PUBLIC_KEY", "").replace("\\n", "\n")
    issuer = os.getenv("WEBSITE_JWT_ISSUER", "").strip()
    audience = os.getenv("WEBSITE_JWT_AUDIENCE", "").strip()

    if not public_key.strip() or not issuer or not audience:
        raise HTTPException(
            status_code=503,
            detail="Website authentication is not configured.",
        )

    try:
        claims = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            issuer=issuer,
            audience=audience,
            options={
                "require": [
                    "sub",
                    "phone_number",
                    "iat",
                    "exp",
                    "iss",
                    "aud",
                ]
            },
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=401,
            detail="Your website session has expired. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=401,
            detail="Invalid website login token. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user_id = str(claims.get("sub") or "").strip()
    mobile = _normalize_indian_mobile(claims.get("phone_number"))

    issued_at = claims.get("iat")
    expires_at = claims.get("exp")

    if (
        not user_id
        or not mobile
        or not isinstance(issued_at, (int, float))
        or not isinstance(expires_at, (int, float))
        or expires_at <= issued_at
        or expires_at - issued_at > 3600
    ):
        raise HTTPException(
            status_code=401,
            detail="The website login token has invalid identity claims.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return WebsiteIdentity(user_id=user_id, mobile=mobile)
