# app/infrastructure/external/fcm_client.py
"""Firebase Cloud Messaging client."""

import json
import logging
import os
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timedelta

import firebase_admin
from firebase_admin import credentials, messaging
from firebase_admin.exceptions import FirebaseError

from ...core.config import get_settings
from ...core.exceptions import ConfigurationError, ExternalServiceError

logger = logging.getLogger(__name__)
settings = get_settings()


class FCMTokenValidator:
    """Validates FCM tokens before sending notifications."""
    
    def __init__(self):
        self.validation_cache = {}
        self.cache_ttl = 300  # 5 minutes
    
    async def validate_token(self, token: str) -> Tuple[bool, str]:
        """Validate a single FCM token by sending a dry-run message."""
        cache_key = token
        if cache_key in self.validation_cache:
            cached_result, timestamp = self.validation_cache[cache_key]
            if (datetime.now() - timestamp).total_seconds() < self.cache_ttl:
                return cached_result
        
        try:
            if not firebase_admin._apps:
                return False, "Firebase not initialized"
            
            message = messaging.Message(
                notification=messaging.Notification(
                    title="Token Validation",
                    body="This is a validation test"
                ),
                token=token
            )
            
            messaging.send(message, dry_run=True)
            result = (True, "Valid")
            self.validation_cache[cache_key] = (result, datetime.now())
            return result
            
        except FirebaseError as e:
            error_msg = str(e)
            result = (False, error_msg)
            self.validation_cache[cache_key] = (result, datetime.now())
            return result
        except Exception as e:
            error_msg = f"Validation error: {str(e)}"
            return False, error_msg
    
    async def validate_tokens_batch(self, tokens: List[str]) -> Dict[str, Tuple[bool, str]]:
        """Validate multiple tokens in batch."""
        results = {}
        for token in tokens:
            is_valid, error_msg = await self.validate_token(token)
            results[token] = (is_valid, error_msg)
        return results


class FCMClient:
    """Firebase Cloud Messaging client for push notifications."""
    
    def __init__(self):
        self.config = settings.fcm_config
        self.validator = FCMTokenValidator()
        self._initialized = False
    
    async def initialize(self):
        """Initialize Firebase Admin SDK."""
        try:
            if not firebase_admin._apps:
                service_account_path = self.config.get("service_account_path")
                
                if service_account_path and os.path.exists(service_account_path):
                    # Initialize with service account file
                    cred = credentials.Certificate(service_account_path)
                    firebase_admin.initialize_app(cred)
                    logger.info("Firebase initialized with service account file")
                elif all([
                    self.config.get("project_id"),
                    self.config.get("private_key"),
                    self.config.get("client_email")
                ]):
                    # Initialize with environment variables
                    service_account_info = {
                        "type": "service_account",
                        "project_id": self.config["project_id"],
                        "private_key_id": self.config["private_key_id"],
                        "private_key": self.config["private_key"].replace('\\n', '\n'),
                        "client_email": self.config["client_email"],
                        "client_id": self.config["client_id"],
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs"
                    }
                    cred = credentials.Certificate(service_account_info)
                    firebase_admin.initialize_app(cred)
                    logger.info("Firebase initialized with environment variables")
                else:
                    raise ConfigurationError("FCM configuration incomplete")
            
            self._initialized = True
            logger.info("FCM client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize FCM client: {e}")
            raise ConfigurationError(f"FCM initialization failed: {str(e)}")
    
    def _is_token_error(self, error: Exception) -> bool:
        """Check if the error is related to invalid token."""
        error_str = str(error).lower()
        token_error_indicators = [
            "requested entity was not found",
            "registration token is not a valid fcm registration token",
            "the registration token is not valid",
            "registration token expired",
            "invalid token",
            "invalid registration token"
        ]
        return any(indicator in error_str for indicator in token_error_indicators)
    
    async def send_notification(self, tokens: List[str], title: str, body: str, 
                              data: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Send FCM notification to multiple tokens."""
        if not self._initialized:
            raise ExternalServiceError("FCM client not initialized")
        
        if not firebase_admin._apps:
            raise ExternalServiceError("Firebase not initialized")
        
        successes = 0
        failures = 0
        details = []
        
        for token in tokens:
            try:
                message = messaging.Message(
                    notification=messaging.Notification(
                        title=title,
                        body=body
                    ),
                    data=data or {},
                    token=token
                )
                
                response = messaging.send(message)
                successes += 1
                details.append({
                    "token": token[:20] + "...",
                    "status": "success",
                    "response": response
                })
                logger.debug(f"FCM notification sent successfully to {token[:20]}...")
                
            except FirebaseError as e:
                failures += 1
                error_msg = str(e)
                details.append({
                    "token": token[:20] + "...",
                    "status": "failed",
                    "error": error_msg,
                    "is_token_error": self._is_token_error(e)
                })
                
                if self._is_token_error(e):
                    logger.warning(f"Invalid FCM token: {token[:20]}... - {error_msg}")
                else:
                    logger.error(f"FCM service error: {error_msg}")
                
            except Exception as e:
                failures += 1
                error_msg = str(e)
                details.append({
                    "token": token[:20] + "...",
                    "status": "failed",
                    "error": error_msg,
                    "is_token_error": False
                })
                logger.error(f"Unexpected FCM error: {error_msg}")
        
        return {
            "successes": successes,
            "failures": failures,
            "total": len(tokens),
            "details": details
        }
    
    async def send_multicast(self, tokens: List[str], title: str, body: str,
                           data: Optional[Dict[str, str]] = None) -> messaging.BatchResponse:
        """Send notification to multiple tokens using multicast."""
        if not self._initialized:
            raise ExternalServiceError("FCM client not initialized")
        
        message = messaging.MulticastMessage(
            notification=messaging.Notification(
                title=title,
                body=body
            ),
            data=data or {},
            tokens=tokens
        )
        
        try:
            response = messaging.send_multicast(message)
            logger.info(f"Multicast sent: {response.success_count} successful, {response.failure_count} failed")
            return response
        except Exception as e:
            logger.error(f"Multicast send failed: {e}")
            raise ExternalServiceError(f"Multicast notification failed: {str(e)}")


