import hashlib
import logging
import secrets

import bcrypt

from backend.domain.exceptions import ValidationError

logger = logging.getLogger(__name__)


class PasswordHasher:
    """Secure password hashing service using bcrypt."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a plain text password using bcrypt.

        Raises:
            ValidationError: If password is empty.
        """
        if not password:
            raise ValueError("Password cannot be empty")

        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify plain password against hashed password.

        Supports both bcrypt hashes and legacy pbkdf2 hashes for
        backward compatibility with any passwords stored before bcrypt was in use.
        """
        if not plain_password or not hashed_password:
            return False

        try:
            # Legacy PBKDF2 hashes created before bcrypt was available
            if hashed_password.startswith("pbkdf2:"):
                parts = hashed_password.split(":")
                if len(parts) != 3:
                    return False
                salt = parts[1]
                expected_key = parts[2]
                key = hashlib.pbkdf2_hmac(
                    "sha256",
                    plain_password.encode("utf-8"),
                    salt.encode("utf-8"),
                    100000,
                )
                return secrets.compare_digest(key.hex(), expected_key)

            return bcrypt.checkpw(
                plain_password.encode("utf-8"), hashed_password.encode("utf-8")
            )
        except Exception as exc:
            logger.warning(f"Password verification error: {exc}")
            return False
