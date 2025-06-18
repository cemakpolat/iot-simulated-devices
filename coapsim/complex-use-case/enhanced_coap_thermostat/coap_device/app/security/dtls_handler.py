# client/app/security/dtls_handler.py
import asyncio
import logging

logger = logging.getLogger(__name__)

class DTLSSecurityHandler:
    """Handles DTLS credentials for aiocoap context."""
    def __init__(self, config, security_manager):
        self.config = config
        self.security_manager = security_manager
        self.credentials_loaded = False

    def get_dtls_credentials(self):
        """Returns aiocoap DTLS credentials dictionary for context."""
        if not self.config.ENABLE_DTLS:
            logger.info("DTLS is disabled for client device server.")
            return None

        if not self.credentials_loaded:
            logger.info("Loading DTLS PSK credentials for client device server.")
            
            identity = self.security_manager.psk_identity # ensure it's str, not bytes
            key = self.security_manager.psk_key

            # Create credentials dictionary in the format expected by aiocoap
            credentials = {
                #"coaps://*": {
                ":client": {
                    "dtls": {
                       "psk":  key,
                        "client-identity": identity,

                    }
                }
            }
            
            self.credentials_loaded = True
            self.creds = credentials
            logger.info("DTLS PSK credentials loaded successfully for client device server.")
        
        return self.creds

    def apply_credentials_to_context(self, context):
        """Apply DTLS credentials to an aiocoap context."""
        if not self.config.ENABLE_DTLS:
            return
            
        credentials = self.get_dtls_credentials()
        if credentials:
            # Load credentials into the context's client_credentials store
              
            context.server_credentials.load_from_dict(credentials)
            logger.info("DTLS credentials applied to context.")