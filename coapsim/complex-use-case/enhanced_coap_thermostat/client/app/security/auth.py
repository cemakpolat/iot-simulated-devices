# client/app/security/auth.py
import os
import logging
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)

class SecurityManager:
    """Manages PSK and Certificate-based security for CoAP DTLS."""
    def __init__(self, config):
        self.config = config
        self.psk_identity = self.config.PSK_IDENTITY.encode('utf-8')
        self.psk_key = self.config.PSK_KEY.encode('utf-8')
        logger.info(f"SecurityManager initialized with PSK Identity: {self.config.PSK_IDENTITY}")

    def get_psk_credentials(self, identity):
        """Returns PSK key for a given identity."""
        if identity == self.psk_identity:
            logger.debug(f"PSK provided for identity: {identity.decode()}")
            return self.psk_key
        logger.warning(f"Unknown PSK identity requested: {identity.decode()}")
        return None

    def generate_or_load_keys(self, private_key_path="certs/private_key.pem", public_key_path="certs/public_key.pem"):
        """Generates or loads RSA private and public keys. (Primarily for certificate-based DTLS)"""
        if os.path.exists(private_key_path) and os.path.exists(public_key_path):
            logger.info("Loading existing RSA keys.")
            with open(private_key_path, "rb") as f:
                private_key = serialization.load_pem_private_key(f.read(), password=None, backend=default_backend())
            with open(public_key_path, "rb") as f:
                public_key = serialization.load_pem_public_key(f.read(), backend=default_backend())
        else:
            logger.info("Generating new RSA keys.")
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            public_key = private_key.public_key()

            # Save keys
            os.makedirs(os.path.dirname(private_key_path), exist_ok=True)
            with open(private_key_path, "wb") as f:
                f.write(private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))
            with open(public_key_path, "wb") as f:
                f.write(public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                ))
        return private_key, public_key

    # Certificate handling functions would be added here if using X.509 certs for DTLS.
    # For PSK, the `get_psk_credentials` is the key.