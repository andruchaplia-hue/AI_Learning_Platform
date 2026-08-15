import base64
import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from backend.domain.exceptions import AuthenticationError
from backend.infrastructure.config.settings import AppSettings

logger = logging.getLogger(__name__)


class JWTManager:
    """JSON Web Token manager for encoding, decoding, and validating bearer tokens."""

    def __init__(self, settings: AppSettings) -> None:
        self.secret_key = settings.jwt_secret_key
        self.algorithm = settings.jwt_algorithm
        self.expire_minutes = settings.access_token_expire_minutes

    def create_access_token(
        self, data: dict[str, Any], expires_delta: timedelta | None = None
    ) -> str:
        """Create signed JWT access token."""
        to_encode = data.copy()
        now = datetime.now(timezone.utc)
        expire = now + (expires_delta or timedelta(minutes=self.expire_minutes))
        to_encode.update({"exp": int(expire.timestamp()), "iat": int(now.timestamp())})
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def decode_token(self, token: str) -> dict[str, Any]:
        """Decode and validate a JWT access token.

        Raises:
            AuthenticationError: If token is expired, invalid or malformed.
        """
        if not token:
            raise AuthenticationError("Authentication token is missing")

        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError as exc:
            raise AuthenticationError("Authentication token has expired") from exc
        except jwt.InvalidTokenError as exc:
            raise AuthenticationError(f"Invalid authentication token: {exc}") from exc
