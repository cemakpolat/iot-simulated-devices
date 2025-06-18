# Replace your current notification_service.py with this enhanced version

import smtplib
import json
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import asyncio
import os
from typing import Dict, Any, TYPE_CHECKING, List, Tuple
import firebase_admin
from firebase_admin import credentials, messaging
from firebase_admin.exceptions import FirebaseError

from ..config import ServerConfig
from ..notifiers.webhook_notifiers import BaseWebhookNotifier, SlackWebhookNotifier, GenericWebhookNotifier

if TYPE_CHECKING:
    from ..api.websocket_handler import WebSocketManager

logger = logging.getLogger(__name__)

# Enhanced FCM Token Manager (inline - put this in a separate file if preferred)
class FCMTokenValidator:
    """Validates FCM tokens before sending notifications"""
    
    def __init__(self):
        self.validation_cache = {}
        self.cache_ttl = 300  # 5 minutes
    
    async def validate_token(self, token: str) -> Tuple[bool, str]:
        """Validate a single FCM token by sending a dry-run message"""
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
            self.validation_cache[cache_key] = ((True, "Valid"), datetime.now())
            return True, "Valid"
            
        except FirebaseError as e:
            error_msg = str(e)
            self.validation_cache[cache_key] = ((False, error_msg), datetime.now())
            return False, error_msg
        except Exception as e:
            error_msg = f"Validation error: {str(e)}"
            return False, error_msg

class EnhancedFCMTokenManager:
    """Enhanced FCM token manager with validation and better error handling"""
    
    def __init__(self):
        self.tokens: List[Dict[str, Any]] = []
        self._lock = asyncio.Lock()
        self.validator = FCMTokenValidator()
        self.last_validation = None
        self.validation_interval = 3600
    
    async def add_token(self, token: str, user_info: Dict[str, Any] = None):
        """Add a token with metadata and optional validation"""
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
                "status": "active",
                "last_validation": None,
                "validation_error": None
            }
            self.tokens.append(token_info)
            logger.info(f"FCM token registered: {token[:20]}... for user: {user_info.get('username', 'Unknown')}")
            
            # Validate in background
            asyncio.create_task(self._validate_token_background(token))
            return True
    
    async def _validate_token_background(self, token: str):
        """Validate a token in the background"""
        try:
            is_valid, error_msg = await self.validator.validate_token(token)
            
            async with self._lock:
                token_info = next((t for t in self.tokens if t["token"] == token), None)
                if token_info:
                    token_info["last_validation"] = datetime.now().isoformat()
                    if not is_valid:
                        token_info["status"] = "invalid"
                        token_info["validation_error"] = error_msg
                        logger.warning(f"Token validation failed: {token[:20]}... - {error_msg}")
                    else:
                        token_info["status"] = "active"
                        token_info["validation_error"] = None
        except Exception as e:
            logger.error(f"Background token validation error: {e}")
    
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
        """Mark a token as invalid and increment failure count"""
        async with self._lock:
            for token_info in self.tokens:
                if token_info["token"] == token:
                    token_info["failed_attempts"] = token_info.get("failed_attempts", 0) + 1
                    token_info["last_error"] = error_message
                    token_info["last_error_at"] = datetime.now().isoformat()
                    token_info["status"] = "invalid"
                    
                    if token_info["failed_attempts"] >= 3:
                        logger.warning(f"Removing FCM token after {token_info['failed_attempts']} failures: {token[:20]}...")
                        await self.remove_token(token)
                        return True
                    break
            
            logger.warning(f"FCM token marked as invalid: {token[:20]}... - {error_message}")
            return False
    
    async def get_valid_tokens(self) -> List[str]:
        """Get list of tokens that are likely to be valid"""
        async with self._lock:
            valid_tokens = []
            for token_info in self.tokens:
                if (token_info.get("status", "active") == "active" and 
                    token_info.get("failed_attempts", 0) < 3):
                    valid_tokens.append(token_info["token"])
            return valid_tokens
    
    async def get_tokens(self) -> List[str]:
        """Get all tokens (for backward compatibility)"""
        return await self.get_valid_tokens()
    
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
                    "last_validation": t.get("last_validation"),
                    "validation_error": t.get("validation_error"),
                    "is_valid": t.get("status", "active") == "active" and t.get("failed_attempts", 0) < 3
                }
                for t in self.tokens
            ]
    
    async def validate_all_tokens(self, force: bool = False):
        """Validate all tokens"""
        now = datetime.now()
        
        if not force and self.last_validation:
            time_since_last = (now - self.last_validation).total_seconds()
            if time_since_last < self.validation_interval:
                return
        
        async with self._lock:
            tokens_to_validate = [t["token"] for t in self.tokens if t.get("status") != "invalid"]
        
        if not tokens_to_validate:
            return
        
        logger.info(f"Validating {len(tokens_to_validate)} FCM tokens...")
        
        try:
            valid_count = 0
            invalid_count = 0
            
            for token in tokens_to_validate:
                is_valid, error_msg = await self.validator.validate_token(token)
                
                async with self._lock:
                    token_info = next((t for t in self.tokens if t["token"] == token), None)
                    if token_info:
                        token_info["last_validation"] = now.isoformat()
                        
                        if is_valid:
                            token_info["status"] = "active"
                            token_info["validation_error"] = None
                            token_info["failed_attempts"] = 0
                            valid_count += 1
                        else:
                            token_info["status"] = "invalid"
                            token_info["validation_error"] = error_msg
                            token_info["failed_attempts"] = token_info.get("failed_attempts", 0) + 1
                            invalid_count += 1
            
            logger.info(f"Token validation completed: {valid_count} valid, {invalid_count} invalid")
            self.last_validation = now
            
        except Exception as e:
            logger.error(f"Error during token validation: {e}")
    
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

class FCMManager:
    """Enhanced Firebase Cloud Messaging manager with better error handling"""
    def __init__(self, config: ServerConfig):
        self.config = config
        self._initialize_firebase()
    
    def _initialize_firebase(self):
        """Initialize Firebase Admin SDK"""
        try:
            if not firebase_admin._apps:
                service_account_path = getattr(self.config, 'FCM_SERVICE_ACCOUNT_PATH', None)
                logger.info(f"FCM service account path: {service_account_path}")
                if service_account_path and os.path.exists(service_account_path):
                    cred = credentials.Certificate(service_account_path)
                    firebase_admin.initialize_app(cred)
                    logger.info("Firebase initialized with service account file")
                else: 
                    logger.error("Firebase service acount key is not found!")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            logger.warning("FCM functionality will be disabled")

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

    async def send_notification(self, tokens: List[str], title: str, body: str, data: Dict[str, str] = None, token_manager: 'EnhancedFCMTokenManager' = None):
        """Send FCM notification to multiple tokens with enhanced error handling"""
        if not firebase_admin._apps:
            logger.warning("Firebase not initialized, skipping FCM notification")
            return {"successes": 0, "failures": len(tokens), "details": []}
        
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
                    "error": error_msg
                })
                
                if self._is_token_error(e):
                    logger.warning(f"Invalid FCM token detected: {token[:20]}... - {error_msg}")
                    if token_manager:
                        await token_manager.mark_token_invalid(token, error_msg)
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

class NotificationService:
    """Enhanced notification service with improved FCM token management"""
    def __init__(self, config: ServerConfig):
        self.config = config
        self.logger = logger
        
        # Email configuration
        self.email_config = {
            "smtp_server": getattr(config, 'SMTP_SERVER', None),
            "smtp_port": getattr(config, 'SMTP_PORT', 587),
            "username": getattr(config, 'EMAIL_USERNAME', None),
            "password": getattr(config, 'EMAIL_PASSWORD', None),
            "from_email": getattr(config, 'FROM_EMAIL', None)
        }

        # Initialize webhook notifiers
        self.webhook_notifiers: list[BaseWebhookNotifier] = []
        self._initialize_webhook_notifiers()
        
        # Initialize FCM components with enhanced token manager
        self.fcm_token_manager = EnhancedFCMTokenManager()
        self.fcm_manager = FCMManager(config)
        
        # Start periodic cleanup and validation tasks
        asyncio.create_task(self._periodic_maintenance())

        logger.info(f"NotificationService initialized. Webhooks: {len(self.webhook_notifiers)}, Email: {'yes' if self.email_config.get('username') else 'no'}, FCM: enabled")

    async def _periodic_maintenance(self):
        """Periodic maintenance tasks"""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                # Cleanup old tokens
                await self.fcm_token_manager.cleanup_old_tokens(max_age_days=30)
                
                # Validate tokens every few hours
                await self.fcm_token_manager.validate_all_tokens(force=False)
                
            except Exception as e:
                logger.error(f"Error in periodic maintenance: {e}")

    def _initialize_webhook_notifiers(self):
        """Initialize webhook notifiers"""
        webhook_urls = getattr(self.config, 'WEBHOOK_URLS', '')
        raw_webhook_urls = [url.strip() for url in webhook_urls.split(",") if url.strip()]
        
        for url in raw_webhook_urls:
            if "hooks.slack.com" in url:
                self.webhook_notifiers.append(SlackWebhookNotifier(url))
                self.logger.info(f"Configured Slack webhook notifier for: {url}")
            else:
                self.webhook_notifiers.append(GenericWebhookNotifier(url))
                self.logger.info(f"Configured Generic webhook notifier for: {url}")

    def set_websocket_manager(self, ws_manager: 'WebSocketManager'):
        """Sets the WebSocketManager instance for broadcasting alerts."""
        self._websocket_manager = ws_manager
        logger.info("WebSocketManager set for NotificationService.")

    async def send_alert(self, alert_type: str, message: str, data: Dict[str, Any] = None):
        """Sends an alert via all configured channels including FCM push notifications."""
        alert_payload = {
            "timestamp": datetime.now().isoformat(),
            "type": alert_type,
            "message": message,
            "data": data or {},
            "severity": self._get_severity(alert_type)
        }
        
        self.logger.info(f"Preparing alert: Type={alert_type}, Severity={alert_payload['severity']}, Message='{message}'")

        # Send email for high/critical alerts
        if alert_payload["severity"] in ["high", "critical"] and self.email_config.get("username"):
            asyncio.create_task(self._send_email_alert(alert_payload))
        
        # Send webhook notifications
        if self.webhook_notifiers:
            for notifier in self.webhook_notifiers:
                asyncio.create_task(notifier.send(alert_payload))
        
        # Send FCM push notification
        asyncio.create_task(self._send_fcm_notification(alert_payload))
        
        # Send websocket notification
        if hasattr(self, '_websocket_manager') and self._websocket_manager:
            dashboard_alert_format = {
                "type": "alert",
                "alert": alert_payload
            }
            asyncio.create_task(self._websocket_manager.broadcast(dashboard_alert_format))
            self.logger.info(f"Alert '{alert_type}' broadcasted to WebSocket clients.")
        
        self.logger.info(f"Alert '{alert_type}' triggered for dispatch.")

    async def _send_fcm_notification(self, alert: Dict[str, Any]):
        """Send FCM push notification with enhanced error handling"""
        try:
            tokens = await self.fcm_token_manager.get_valid_tokens()
            if not tokens:
                self.logger.info("No valid FCM tokens registered, skipping push notification")
                return
            
            title = f"Smart Thermostat Alert: {alert['type']}"
            body = f"{alert['message']} (Severity: {alert['severity'].upper()})"
            
            # Convert data to strings for FCM
            fcm_data = {
                "alert_type": alert['type'],
                "severity": alert['severity'],
                "timestamp": alert['timestamp'],
                "data": json.dumps(alert['data'])
            }
            
            logger.info(f"Sending FCM notification to {len(tokens)} valid tokens...")
            result = await self.fcm_manager.send_notification(
                tokens, title, body, fcm_data, self.fcm_token_manager
            )
            
            self.logger.info(f"FCM notifications result: {result['successes']} successful, {result['failures']} failed")
            
            # Log failure details for debugging
            if result['failures'] > 0:
                failed_details = [d for d in result.get('details', []) if d.get('status') == 'failed']
                for detail in failed_details[:3]:  # Log first 3 failures
                    self.logger.debug(f"FCM failure: {detail}")
            
        except Exception as e:
            self.logger.error(f"Error sending FCM notifications: {e}", exc_info=True)

    def _get_severity(self, alert_type: str) -> str:
        """Maps alert types to predefined severity levels."""
        severity_map = {
            "temperature_anomaly": "medium",
            "system_failure": "critical",
            "maintenance_required": "high",
            "energy_spike": "medium",
            "sensor_malfunction": "high",
            "connectivity_issue": "low",
            "device_command_failure": "high",
            "test_notification": "low"
        }
        return severity_map.get(alert_type, "medium")

    async def _send_email_alert(self, alert: Dict[str, Any]):
        """Send email notification"""
        try:
            if not all([self.email_config.get("username"), self.email_config.get("password"), self.email_config.get("from_email")]):
                self.logger.warning("Email credentials not fully configured. Skipping email alert dispatch.")
                return
            
            alert_email = getattr(self.config, 'ALERT_EMAIL', self.email_config.get("username"))
            
            msg = MIMEMultipart()
            msg['From'] = self.email_config["from_email"]
            msg['To'] = alert_email
            msg['Subject'] = f"Smart Thermostat Alert: {alert['type']} ({alert['severity'].upper()})"
            
            body = f"""
            Alert Type: {alert['type']}
            Severity: {alert['severity'].upper()}
            Time: {alert['timestamp']}
            
            Message: {alert['message']}
            
            Additional Data:
            {json.dumps(alert['data'], indent=2)}
            
            ---
            Smart Thermostat System Automated Alert
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._send_email_blocking, msg)
            
        except Exception as e:
            self.logger.error(f"Failed to send email alert: {e}", exc_info=True)

    def _send_email_blocking(self, msg: MIMEMultipart):
        """Blocking email send operation"""
        try:
            server = smtplib.SMTP(self.email_config["smtp_server"], self.email_config["smtp_port"])
            server.starttls()
            server.login(self.email_config["username"], self.email_config["password"])
            server.send_message(msg)
            server.quit()
            self.logger.info(f"Email alert sent successfully to {msg['To']} with subject: '{msg['Subject']}'")
        except Exception as e:
            self.logger.error(f"Blocking email send operation failed: {e}", exc_info=True)

    async def cleanup(self):
        """Cleanup resources"""
        try:
            self.logger.info("NotificationService cleanup completed")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")