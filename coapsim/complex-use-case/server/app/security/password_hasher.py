# server/app/security/password_hasher.py
from passlib.context import CryptContext # pip install passlib[bcrypt]
import logging

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class PasswordHasher:
    @staticmethod
    def hash_password(password: str) -> str:
        """Hashes a plaintext password."""
        hashed = pwd_context.hash(password)
        logger.debug("Password hashed.")
        return hashed

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verifies a plaintext password against a hashed one."""
        verified = pwd_context.verify(plain_password, hashed_password)
        logger.debug(f"Password verification: {verified}")
        return verified