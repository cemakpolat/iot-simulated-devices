"""Simplified notification service based on working code pattern"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, TYPE_CHECKING

from ..config import ServerConfig
from ..notifiers.webhook_notifier import TeamsWebhookNotifier, SlackWebhookNotifier, GenericWebhookNotifier
from ..notifiers.email_notifier import EmailNotifier
from ..notifiers.fcm_notifier import FCMNotifier
from ..notifiers.websocket_notifier import WebSocketNotifier

if TYPE_CHECKING:
    from ..api.websocket_handler import WebSocketManager

logger = logging.getLogger(__name__)


class NotificationService:
    """Simplified notification service based on working code pattern"""
    
    def __init__(self, config: ServerConfig):
        self.config = config
        self.logger = logger
        self.notifiers: List[Any] = []
        
        # Store specific notifiers for direct access
        self.email_notifier = None
        self.fcm_notifier = None
        self.websocket_notifier = None
        self.webhook_notifiers = []
        
        # Debug FCM configuration
        self._debug_fcm_configuration()
        
        # Initialize all notifiers
        self._initialize_notifiers()
        
        # Start periodic maintenance tasks
        asyncio.create_task(self._periodic_maintenance())

        logger.info(f"NotificationService initialized with {len(self.notifiers)} notifiers")

    def _debug_fcm_configuration(self):
        """Debug FCM configuration"""
        logger.info("🔍 FCM Configuration Debug:")
        logger.info("=" * 50)
        
        # Check environment variables
        import os
        fcm_env_vars = [
            'FCM_SERVICE_ACCOUNT_PATH',
            'FCM_PROJECT_ID',
        ]
        
        for var in fcm_env_vars:
            value = os.getenv(var)
            if var == 'FCM_SERVICE_ACCOUNT_PATH':
                logger.info(f"  {var}: {value}")
                if value and os.path.exists(value):
                    logger.info(f"    ✅ File exists (size: {os.path.getsize(value)} bytes)")
                elif value:
                    logger.warning(f"    ❌ File not found at: {value}")
                else:
                    logger.warning(f"    ❌ Environment variable not set")
            else:
                logger.info(f"  {var}: {'✅ Set' if value else '❌ Not set'}")

    def _initialize_notifiers(self):
        """Initialize all configured notifiers"""
        
        # Initialize Email Notifier
        if self._is_email_configured():
            email_config = {
                'smtp_server': getattr(self.config, 'SMTP_SERVER', 'smtp.gmail.com'),
                'smtp_port': getattr(self.config, 'SMTP_PORT', 587),
                'email_username': getattr(self.config, 'EMAIL_USERNAME', None),
                'email_password': getattr(self.config, 'EMAIL_PASSWORD', None),
                'from_email': getattr(self.config, 'FROM_EMAIL', None),
                'recipients': [getattr(self.config, 'ALERT_EMAIL', getattr(self.config, 'EMAIL_USERNAME', None))]
            }
            self.email_notifier = EmailNotifier(email_config)
            self.notifiers.append(self.email_notifier)
            asyncio.create_task(self._initialize_notifier_safe(self.email_notifier, "Email"))
        else:
            logger.info("⚠️ Email notifier not configured (missing credentials)")
        
        # Initialize Webhook Notifiers
        self._initialize_webhook_notifiers()
        
        # Initialize FCM Notifier with simplified configuration
        if self._is_fcm_configured():
            fcm_path = self._get_fcm_service_account_path()
            
            if fcm_path:
                fcm_config = {
                    'fcm_service_account_path': fcm_path
                }
                logger.info(f"🔥 Creating FCM notifier with path: {fcm_path}")
                self.fcm_notifier = FCMNotifier(fcm_config)
                self.notifiers.append(self.fcm_notifier)
                # Note: FCM initializes synchronously in constructor now
                logger.info("✅ FCM notifier created and initialized")
            else:
                logger.error("❌ FCM service account path could not be determined")
        else:
            logger.info("⚠️ FCM notifier not configured (missing service account)")
        
        # Initialize WebSocket Notifier
        websocket_config = {}
        self.websocket_notifier = WebSocketNotifier(websocket_config)
        self.notifiers.append(self.websocket_notifier)
        asyncio.create_task(self._initialize_notifier_safe(self.websocket_notifier, "WebSocket"))

    def _get_fcm_service_account_path(self) -> str:
        """Get FCM service account path from multiple sources"""
        import os
        # Try different sources in order of preference
        sources = [
            # 1. Environment variable
            os.getenv('FCM_SERVICE_ACCOUNT_PATH'),
            # 2. Config object
            getattr(self.config, 'FCM_SERVICE_ACCOUNT_PATH', None),
            # 3. Default path
            '/app/firebase-service-account-key.json',
        ]
        
        for source in sources:
            if source and os.path.exists(source):
                logger.info(f"✅ Found FCM service account at: {source}")
                return source
        
        logger.error("❌ FCM service account file not found in any location")
        return None

    async def _initialize_notifier_safe(self, notifier, notifier_name: str):
        """Safely initialize a notifier with error handling"""
        try:
            logger.info(f"🔧 Initializing {notifier_name} notifier...")
            success = await notifier.initialize()
            if success:
                logger.info(f"✅ {notifier_name} notifier initialized successfully")
            else:
                logger.warning(f"⚠️ {notifier_name} notifier initialization returned False")
                    
        except Exception as e:
            logger.error(f"❌ {notifier_name} notifier initialization failed: {e}", exc_info=True)

    def _is_email_configured(self) -> bool:
        """Check if email is properly configured"""
        return all([
            getattr(self.config, 'EMAIL_USERNAME', None),
            getattr(self.config, 'EMAIL_PASSWORD', None),
            getattr(self.config, 'SMTP_SERVER', None)
        ])

    def _is_fcm_configured(self) -> bool:
        """Check if FCM is properly configured"""
        fcm_path = self._get_fcm_service_account_path()
        return fcm_path is not None

    def _initialize_webhook_notifiers(self):
        """Initialize webhook notifiers"""
        webhook_urls = getattr(self.config, 'WEBHOOK_URLS', '')
        if webhook_urls:
            raw_webhook_urls = [url.strip() for url in webhook_urls.split(",") if url.strip()]
            
            for url in raw_webhook_urls:
                notifier = None
                notifier_type = ""
                
                if "hooks.slack.com" in url:
                    notifier = SlackWebhookNotifier(url)
                    notifier_type = "Slack"
                elif "outlook.office.com" in url or "teams.microsoft.com" in url:
                    notifier = TeamsWebhookNotifier(url)
                    notifier_type = "Teams"
                else:
                    notifier = GenericWebhookNotifier(url)
                    notifier_type = "Generic"
                
                if notifier:
                    self.webhook_notifiers.append(notifier)
                    self.notifiers.append(notifier)
                    
                    # Initialize the webhook notifier asynchronously
                    asyncio.create_task(self._initialize_notifier_safe(notifier, f"{notifier_type} Webhook"))
                    
                    self.logger.info(f"🔧 {notifier_type} webhook notifier configured: {url}")
        else:
            logger.info("⚠️ No webhook URLs configured")

    async def _periodic_maintenance(self):
        """Periodic maintenance tasks for FCM and other notifiers"""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                # FCM specific maintenance
                if self.fcm_notifier:
                    await self.fcm_notifier.cleanup_old_tokens(max_age_days=30)
                
            except Exception as e:
                logger.error(f"Error in periodic maintenance: {e}")

    def set_websocket_manager(self, ws_manager: 'WebSocketManager'):
        """Sets the WebSocketManager instance for broadcasting alerts."""
        self._websocket_manager = ws_manager
        
        # Also set it for the websocket notifier if it needs direct access
        if self.websocket_notifier and hasattr(ws_manager, 'broadcast'):
            self.websocket_notifier._websocket_manager = ws_manager
            
        logger.info("WebSocketManager set for NotificationService.")

    async def send_alert(self, alert_type: str, message: str, data: Dict[str, Any] = None):
        """Sends an alert via all configured notifiers - Following working pattern"""
        alert_payload = {
            "timestamp": datetime.now().isoformat(),
            "type": alert_type,
            "message": message,
            "data": data or {},
            "severity": self._get_severity(alert_type)
        }
        
        self.logger.info(f"📢 Sending alert: Type={alert_type}, Severity={alert_payload['severity']}, Message='{message}'")

        # Track successful/failed notifications
        results = {"successful": [], "failed": []}
        notification_tasks = []

        # 1. Send via Email Notifier
        if self.email_notifier:
            task = asyncio.create_task(
                self._send_email_notification(alert_type, message, data, results)
            )
            notification_tasks.append(task)

        # 2. Send via Webhook Notifiers (Slack, Teams, etc.)
        for webhook_notifier in self.webhook_notifiers:
            task = asyncio.create_task(
                self._send_webhook_notification(webhook_notifier, alert_type, message, data, results)
            )
            notification_tasks.append(task)

        # 3. Send via FCM Notifier (simplified approach)
        if self.fcm_notifier:
            task = asyncio.create_task(
                self._send_fcm_notification(alert_type, message, data, results)
            )
            notification_tasks.append(task)

        # 4. Send via WebSocket
        if hasattr(self, '_websocket_manager') and self._websocket_manager:
            task = asyncio.create_task(
                self._send_websocket_notification(alert_payload, results)
            )
            notification_tasks.append(task)

        # Wait for all notifications to complete
        if notification_tasks:
            await asyncio.gather(*notification_tasks, return_exceptions=True)

        # Log summary
        total_notifiers = len(self.notifiers)
        successful_count = len(results["successful"])
        failed_count = len(results["failed"])
        
        self.logger.info(f"📊 Alert '{alert_type}' sent: {successful_count}/{total_notifiers} successful")
        if results["failed"]:
            self.logger.warning(f"❌ Failed notifiers: {', '.join(results['failed'])}")

    async def _send_email_notification(self, alert_type: str, message: str, data: Dict[str, Any], results: Dict):
        """Send email notification"""
        try:
            success = await self.email_notifier.send(alert_type, message, data)
            if success:
                results["successful"].append("Email")
                self.logger.info("✅ Email notification sent successfully")
            else:
                results["failed"].append("Email")
                self.logger.warning("❌ Email notification failed")
        except Exception as e:
            results["failed"].append("Email")
            self.logger.error(f"❌ Email notification error: {e}")


    async def _send_fcm_notification(self, alert_type: str, message: str, data: Dict[str, Any], results: Dict):
        """Send FCM notification - let FCM notifier handle token checks"""
        try:
            # Skip token check, let the FCM notifier handle it
            success = await self.fcm_notifier.send(alert_type, message, data)
            if success:
                results["successful"].append("FCM")
                self.logger.info("✅ FCM notification sent successfully")
            else:
                results["failed"].append("FCM")
                self.logger.warning("❌ FCM notification failed")
                
        except Exception as e:
            results["failed"].append("FCM")
            self.logger.error(f"❌ FCM notification error: {e}", exc_info=True)

    async def _send_webhook_notification(self, webhook_notifier, alert_type: str, message: str, data: Dict[str, Any], results: Dict):
        """Send webhook notification"""
        notifier_name = webhook_notifier.__class__.__name__
        try:
            success = await webhook_notifier.send(alert_type, message, data)
            if success:
                results["successful"].append(notifier_name)
                self.logger.info(f"✅ {notifier_name} notification sent successfully")
            else:
                results["failed"].append(notifier_name)
                self.logger.warning(f"❌ {notifier_name} notification failed")
        except Exception as e:
            results["failed"].append(notifier_name)
            self.logger.error(f"❌ {notifier_name} notification error: {e}")

    async def _send_websocket_notification(self, alert_payload: Dict, results: Dict):
        """Send WebSocket notification"""
        try:
            dashboard_alert_format = {
                "type": "alert",
                "alert": alert_payload
            }
            await self._websocket_manager.broadcast(dashboard_alert_format)
            results["successful"].append("WebSocket")
            self.logger.info("✅ WebSocket notification sent successfully")
        except Exception as e:
            results["failed"].append("WebSocket")
            self.logger.error(f"❌ WebSocket notification error: {e}")

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

    # FCM-specific methods (delegated to FCM notifier)
    async def add_fcm_token(self, token: str, user_info: Dict[str, Any] = None):
        """Add FCM token (delegated to FCM notifier)"""
        if self.fcm_notifier:
            result = await self.fcm_notifier.add_token(token, user_info)
            logger.info(f"FCM token added: {token[:20]}... - Result: {result}")
            return result
        else:
            logger.warning("FCM notifier not configured, cannot add token")
            return False

    async def remove_fcm_token(self, token: str):
        """Remove FCM token (delegated to FCM notifier)"""
        if self.fcm_notifier:
            return await self.fcm_notifier.remove_token(token)
        else:
            logger.warning("FCM notifier not configured, cannot remove token")
            return False

    async def get_fcm_token_statistics(self) -> Dict[str, Any]:
        """Get FCM token statistics (delegated to FCM notifier)"""
        if self.fcm_notifier:
            return await self.fcm_notifier.get_token_statistics()
        else:
            return {"total": 0, "active": 0, "invalid": 0, "recent": 0, "validation_rate": "0%", "is_initialized": False}

    async def get_fcm_token_info(self) -> List[Dict[str, Any]]:
        """Get detailed FCM token information (delegated to FCM notifier)"""
        if self.fcm_notifier:
            return await self.fcm_notifier.get_token_info()
        else:
            return []

    async def validate_fcm_tokens(self, force: bool = False):
        """Validate all FCM tokens (delegated to FCM notifier)"""
        if self.fcm_notifier:
            await self.fcm_notifier.validate_all_tokens(force)

    # Test methods for debugging
    async def test_all_notifications(self):
        """Test all configured notification methods"""
        test_message = f"Test notification from Smart Thermostat AI - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        logger.info("🧪 Testing all notification methods...")
        await self.send_alert("test_notification", test_message, {
            "test": True,
            "timestamp": datetime.now().isoformat()
        })

    async def get_notifier_status(self) -> Dict[str, Any]:
        """Get status of all notifiers"""
        webhook_status = []
        for webhook in self.webhook_notifiers:
            webhook_status.append({
                "type": webhook.__class__.__name__,
                "initialized": hasattr(webhook, 'session') and webhook.session is not None,
                "url": getattr(webhook, 'webhook_url', 'unknown')[:50] + "..." if len(getattr(webhook, 'webhook_url', '')) > 50 else getattr(webhook, 'webhook_url', 'unknown')
            })

        # Get FCM status
        fcm_status = {}
        if self.fcm_notifier:
            fcm_status = await self.fcm_notifier.get_token_statistics()

        return {
            "email_configured": self.email_notifier is not None,
            "fcm_configured": self.fcm_notifier is not None,
            "fcm_status": fcm_status,
            "websocket_configured": self.websocket_notifier is not None,
            "webhook_count": len(self.webhook_notifiers),
            "total_notifiers": len(self.notifiers),
            "webhook_details": webhook_status
        }

    async def cleanup(self):
        """Cleanup all notifier resources"""
        try:
            cleanup_tasks = []
            for notifier in self.notifiers:
                if hasattr(notifier, 'cleanup'):
                    cleanup_tasks.append(asyncio.create_task(notifier.cleanup()))
            
            if cleanup_tasks:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            
            self.logger.info("NotificationService cleanup completed")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")