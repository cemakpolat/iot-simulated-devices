"""Firebase Cloud Messaging notifier implementation - Fixed version based on working code"""
import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple, Optional
from .base_notifier import BaseNotifier

logger = logging.getLogger(__name__)


class FCMTokenManager:
    """Simple FCM token manager based on working EnhancedFCMTokenManager"""
    
    def __init__(self):
        self.tokens: List[Dict[str, Any]] = []
        self._lock = asyncio.Lock()
    
    async def add_token(self, token: str, user_info: Dict[str, Any] = None):
        """Add a token with metadata"""
        async with self._lock:
            existing_token = next((t for t in self.tokens if t["token"] == token), None)
            if existing_token:
                existing_token.update({
                    "last_seen": datetime.now().isoformat(),
                    "user_info": user_info or {},
                    "failed_attempts": 0,
                    "status": "active"
                })
                logger.info(f"FCM token updated: {token[:20]}... for user: {user_info.get('username', 'Unknown')}")
                return False
            
            token_info = {
                "token": token,
                "added_at": datetime.now().isoformat(),
                "last_seen": datetime.now().isoformat(),
                "user_info": user_info or {},
                "failed_attempts": 0,
                "status": "active"
            }
            self.tokens.append(token_info)
            logger.info(f"FCM token registered: {token[:20]}... for user: {user_info.get('username', 'Unknown')}")
            return True
    
    async def remove_token(self, token: str):
        """Remove a specific token"""
        async with self._lock:
            initial_count = len(self.tokens)
            self.tokens = [t for t in self.tokens if t["token"] != token]
            removed = len(self.tokens) < initial_count
            if removed:
                logger.info(f"FCM token removed: {token[:20]}...")
            return removed
    
    async def mark_token_invalid(self, token: str, error_message: str = ""):
        """Simple version: immediately remove tokens for any Firebase error"""
        async with self._lock:
            initial_count = len(self.tokens)
            
            # Remove any token that matches
            self.tokens = [t for t in self.tokens if t["token"] != token]
            
            removed = len(self.tokens) < initial_count
            
            if removed:
                logger.warning(f"🗑️ REMOVED FCM token: {token[:20]}... - {error_message}")
                logger.info(f"   Tokens remaining: {len(self.tokens)}")
            else:
                logger.warning(f"❌ Token not found for removal: {token[:20]}...")
            
            return removed
    
    async def get_valid_tokens(self) -> List[str]:
        """Get list of tokens that are likely to be valid"""
        async with self._lock:
            valid_tokens = []
            for token_info in self.tokens:
                if (token_info.get("status", "active") == "active" and 
                    token_info.get("failed_attempts", 0) < 3):
                    valid_tokens.append(token_info["token"])
            return valid_tokens
    
    async def get_token_info(self) -> List[Dict[str, Any]]:
        """Get detailed token information"""
        async with self._lock:
            return [
                {
                    "token": t["token"][:20] + "...",
                    "added_at": t["added_at"],
                    "last_seen": t["last_seen"],
                    "user_info": t["user_info"],
                    "failed_attempts": t.get("failed_attempts", 0),
                    "status": t.get("status", "unknown"),
                    "is_valid": t.get("status", "active") == "active" and t.get("failed_attempts", 0) < 3
                }
                for t in self.tokens
            ]
    
    async def cleanup_old_tokens(self, max_age_days: int = 30):
        """Remove tokens older than specified days"""
        async with self._lock:
            cutoff_date = datetime.now() - timedelta(days=max_age_days)
            initial_count = len(self.tokens)
            
            self.tokens = [
                t for t in self.tokens 
                if datetime.fromisoformat(t["added_at"].replace('Z', '+00:00').replace('+00:00', '')) > cutoff_date
            ]
            
            removed_count = initial_count - len(self.tokens)
            if removed_count > 0:
                logger.info(f"Cleaned up {removed_count} old FCM tokens (older than {max_age_days} days)")

    async def get_statistics(self) -> Dict[str, Any]:
        """Get token statistics"""
        async with self._lock:
            total = len(self.tokens)
            if total == 0:
                return {"total": 0, "active": 0, "invalid": 0, "recent": 0}
            
            active = sum(1 for t in self.tokens if t.get("status", "active") == "active")
            invalid = sum(1 for t in self.tokens if t.get("status") == "invalid")
            
            yesterday = datetime.now() - timedelta(days=1)
            recent = sum(
                1 for t in self.tokens 
                if datetime.fromisoformat(t["added_at"].replace('Z', '+00:00').replace('+00:00', '')) > yesterday
            )
            
            return {
                "total": total,
                "active": active,
                "invalid": invalid,
                "recent": recent,
                "validation_rate": f"{(active/total)*100:.1f}%" if total > 0 else "0%"
            }


class FCMNotifier(BaseNotifier):
    """Firebase Cloud Messaging notifier - Fixed version following working pattern"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.fcm_token_manager = FCMTokenManager()
        self.firebase_app = None
        self.service_account_path = config.get('fcm_service_account_path')
        self.is_initialized = False
        
        # Initialize Firebase immediately in constructor (like working code)
        self._initialize_firebase_sync()

    def _initialize_firebase_sync(self):
        """Initialize Firebase Admin SDK synchronously in constructor"""
        try:
            import firebase_admin
            from firebase_admin import credentials
            
            if not self.service_account_path:
                logger.warning("FCM service account path not configured")
                return
                
            if not os.path.exists(self.service_account_path):
                logger.error(f"FCM service account file not found: {self.service_account_path}")
                return
            
            logger.info(f"Initializing Firebase with service account file: {self.service_account_path}")
            
            if not firebase_admin._apps:
                cred = credentials.Certificate(self.service_account_path)
                self.firebase_app = firebase_admin.initialize_app(cred)
                logger.info("Firebase initialized with service account file")
            else:
                self.firebase_app = firebase_admin.get_app()
                logger.info("Using existing Firebase Admin SDK instance")
            
            self.is_initialized = True
                
        except ImportError:
            logger.error("firebase-admin package not installed")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}", exc_info=True)

    async def initialize(self) -> bool:
        """Initialize method for compatibility with base class"""
        # Firebase is already initialized in constructor
        return self.is_initialized

    def _is_token_error(self, error: Exception) -> bool:
        """Check if the error is related to invalid token"""
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

    async def send(self, alert_type: str, message: str, data: Dict[str, Any] = None) -> bool:
        """Send FCM notification to all registered tokens - Following working pattern"""
        if not self.enabled:
            logger.debug("FCM notifier is disabled")
            return False
            
        if not self.is_initialized:
            logger.warning("Firebase not initialized, skipping FCM notification")
            return False
            
        try:
            import firebase_admin
           
            
            if not firebase_admin._apps:
                logger.warning("Firebase apps not found, skipping FCM notification")
                return False
            
            tokens = await self.fcm_token_manager.get_valid_tokens()
            if not tokens:
                logger.info("No valid FCM tokens registered, skipping push notification")
                return False
            
            title = f"Smart Thermostat Alert: {alert_type.replace('_', ' ').title()}"
            body = message
            
            # Convert data to strings for FCM
            fcm_data = {
                "alert_type": alert_type,
                "timestamp": str(datetime.now().timestamp()),
                **(data or {})
            }
            
            # Convert all data values to strings (FCM requirement)
            fcm_data = {k: str(v) for k, v in fcm_data.items()}
            
            # Send to tokens one by one (like working code)
            result = await self._send_to_tokens_individually(tokens, title, body, fcm_data)
            
            logger.info(f"FCM notifications result: {result['successes']} successful, {result['failures']} failed")
            return result['successes'] > 0
            
        except Exception as e:
            logger.error(f"Error sending FCM notifications: {e}", exc_info=True)
            return False

    async def _send_to_tokens_individually(self, tokens: List[str], title: str, body: str, data: Dict[str, str]) -> Dict[str, Any]:
        """Send FCM notification to tokens one by one (following working pattern)"""
        successes = 0
        failures = 0
        details = []
        
        try:
            from firebase_admin import messaging
            from firebase_admin.exceptions import FirebaseError
            
            for token in tokens:
                try:
                    message = messaging.Message(
                        notification=messaging.Notification(
                            title=title,
                            body=body
                        ),
                        data=data,
                        token=token,
                        android=messaging.AndroidConfig(
                            priority='high',
                            notification=messaging.AndroidNotification(
                                icon='smart_thermostat_icon',
                                color='#FF6B35'
                            )
                        ),
                        apns=messaging.APNSConfig(
                            headers={'apns-priority': '10'},
                            payload=messaging.APNSPayload(
                                aps=messaging.Aps(badge=1, sound='default')
                            )
                        )
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
                        "error": error_msg
                    })
                    
                    if self._is_token_error(e):
                        logger.warning(f"Invalid FCM token detected: {token[:20]}... - {error_msg}")
                        await self.fcm_token_manager.mark_token_invalid(token, error_msg)
                    else:
                        logger.error(f"FCM service error for token {token[:20]}...: {error_msg}")
                    
                except Exception as e:
                    failures += 1
                    error_msg = str(e)
                    details.append({
                        "token": token[:20] + "...",
                        "status": "failed",
                        "error": error_msg
                    })
                    logger.error(f"Unexpected error sending FCM notification to {token[:20]}...: {error_msg}")
            
            return {
                "successes": successes,
                "failures": failures,
                "details": details
            }
            
        except Exception as e:
            logger.error(f"Error in individual token notification: {e}")
            return {
                "successes": 0,
                "failures": len(tokens),
                "details": [{"error": str(e)}]
            }

    async def add_token(self, token: str, user_info: Dict[str, Any] = None):
        """Add FCM token"""
        result = await self.fcm_token_manager.add_token(token, user_info)
        logger.info(f"FCM token add result: {result} for token {token[:20]}...")
        return result
    
    async def get_tokens(self) -> List[str]:
        """Get all tokens (for backward compatibility)"""
        return await self.fcm_token_manager.get_valid_tokens()

    async def get_valid_tokens(self) -> List[str]:
        """Get list of valid tokens"""
        return await self.fcm_token_manager.get_valid_tokens()
    
    async def remove_token(self, token: str):
        """Remove FCM token"""
        return await self.fcm_token_manager.remove_token(token)
    
    async def get_token_statistics(self) -> Dict[str, Any]:
        """Get token statistics"""
        stats = await self.fcm_token_manager.get_statistics()
        stats['is_initialized'] = self.is_initialized
        return stats
    
    async def get_token_info(self) -> List[Dict[str, Any]]:
        """Get detailed token information"""
        return await self.fcm_token_manager.get_token_info()
    
    async def validate_all_tokens(self, force: bool = False):
        """Validate all tokens - simplified version"""
        # For now, just log that validation was requested
        # The working code doesn't have complex validation
        tokens = await self.fcm_token_manager.get_valid_tokens()
        logger.info(f"Token validation requested for {len(tokens)} tokens")
    
    async def cleanup_old_tokens(self, max_age_days: int = 30):
        """Remove old tokens"""
        await self.fcm_token_manager.cleanup_old_tokens(max_age_days)
    
    async def cleanup(self):
        """Cleanup FCM resources"""
        try:
            import firebase_admin
            if self.firebase_app:
                firebase_admin.delete_app(self.firebase_app)
                logger.info("Firebase Admin SDK cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up FCM: {e}")