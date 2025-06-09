import smtplib
import json
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import asyncio 
import aiohttp # For making async HTTP requests (webhooks)
import os 
from typing import Dict, Any, TYPE_CHECKING

from config import ServerConfig # Import server configuration

if TYPE_CHECKING:
    from api.websocket_handler import WebSocketManager 

logger = logging.getLogger(__name__)

class NotificationService:
    """
    Handles sending various types of alerts (e.g., critical errors, maintenance needs)
    via multiple channels such as email and webhooks.
    """
    def __init__(self, config: ServerConfig): 
        """
        Initializes the NotificationService with server configuration.
        """
        self.config = config
        self.logger = logger
        # Email configuration details from the server config
        self.email_config = {
            "smtp_server": self.config.SMTP_SERVER,
            "smtp_port": self.config.SMTP_PORT,
            "username": self.config.EMAIL_USERNAME,
            "password": self.config.EMAIL_PASSWORD,
            "from_email": self.config.FROM_EMAIL
        }
        # Parse webhook URLs from config, splitting by comma and stripping whitespace
        self.webhook_urls = [url.strip() for url in self.config.WEBHOOK_URLS.split(",") if url.strip()]
        
        logger.info(f"NotificationService initialized. Webhooks configured: {len(self.webhook_urls)}, Email configured: {'yes' if self.email_config.get('username') else 'no'}")
        
    def set_websocket_manager(self, ws_manager: 'WebSocketManager'):
        """Sets the WebSocketManager instance for broadcasting alerts."""
        self._websocket_manager = ws_manager
        logger.info("WebSocketManager set for NotificationService.")


    async def send_alert(self, alert_type: str, message: str, data: Dict[str, Any] = None):
        """
        Sends an alert via configured channels.
        :param alert_type: A predefined type for the alert (e.g., "system_failure", "maintenance_required").
        :param message: A human-readable message describing the alert.
        :param data: Optional dictionary for additional context or details about the alert.
        """
        alert_payload = {
            "timestamp": datetime.now().isoformat(), # ISO format for easy parsing
            "type": alert_type,
            "message": message,
            "data": data or {}, # Ensure data is a dictionary
            "severity": self._get_severity(alert_type) # Determine severity based on type
        }
        
        self.logger.info(f"Preparing alert: Type={alert_type}, Severity={alert_payload['severity']}, Message='{message}'")

        # Send email notification if severity is high/critical and email credentials are set
        if alert_payload["severity"] in ["high", "critical"] and self.email_config.get("username"):
            # Run email sending in a separate asyncio task to avoid blocking the main loop
            asyncio.create_task(self._send_email_alert(alert_payload)) 
        
        # Send webhook notifications if URLs are configured
        if self.webhook_urls:
            # Run webhook sending in a separate asyncio task
            asyncio.create_task(self._send_webhook_alerts(alert_payload)) 
        
        if self._websocket_manager:
            # We need to wrap the alert in a structure the dashboard expects
            dashboard_alert_format = {
                "type": "alert",
                "alert": alert_payload
            }
            asyncio.create_task(self._websocket_manager.broadcast(dashboard_alert_format))
            self.logger.info(f"Alert '{alert_type}' broadcasted to WebSocket clients.")
        
        self.logger.info(f"Alert '{alert_type}' triggered for dispatch.")

    def _get_severity(self, alert_type: str) -> str:
        """Maps alert types to predefined severity levels."""
        severity_map = {
            "temperature_anomaly": "medium",
            "system_failure": "critical",
            "maintenance_required": "high",
            "energy_spike": "medium",
            "sensor_malfunction": "high",
            "connectivity_issue": "low",
            "device_command_failure": "high" # Added for failed CoAP commands
        }
        return severity_map.get(alert_type, "medium") # Default to medium if type not found

    async def _send_email_alert(self, alert: Dict[str, Any]):
        """
        Sends an email notification. Uses a thread pool executor for blocking SMTP operations
        to prevent blocking the asyncio event loop.
        """
        try:
            # Validate that all required email credentials are provided
            if not all([self.email_config.get("username"), self.email_config.get("password"), self.email_config.get("from_email")]):
                self.logger.warning("Email credentials not fully configured. Skipping email alert dispatch.")
                return
                
            msg = MIMEMultipart()
            msg['From'] = self.email_config["from_email"]
            msg['To'] = self.config.ALERT_EMAIL # Recipient email from config
            msg['Subject'] = f"Smart Thermostat Alert: {alert['type']} ({alert['severity'].upper()})"
            
            # Construct email body with alert details
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
            
            # Run the blocking SMTP operation in a separate thread (executor)
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._send_email_blocking, msg)
            
        except Exception as e:
            self.logger.error(f"Failed to send email alert: {e}", exc_info=True)

    def _send_email_blocking(self, msg: MIMEMultipart):
        """
        Blocking part of email sending (SMTP connection and send).
        Designed to be run in a separate thread via `run_in_executor`.
        """
        try:
            # Establish SMTP connection and send email
            server = smtplib.SMTP(self.email_config["smtp_server"], self.email_config["smtp_port"])
            server.starttls() # Upgrade connection to TLS for security
            server.login(self.email_config["username"], self.email_config["password"])
            server.send_message(msg)
            server.quit()
            self.logger.info(f"Email alert sent successfully to {msg['To']} with subject: '{msg['Subject']}'")
        except Exception as e:
            self.logger.error(f"Blocking email send operation failed: {e}", exc_info=True)

    async def _send_webhook_alerts(self, alert: Dict[str, Any]):
        """
        Sends webhook notifications to all configured URLs.
        Uses `aiohttp` for asynchronous HTTP requests.
        """
        for webhook_url in self.webhook_urls:
            if not webhook_url.strip(): # Skip empty URLs
                continue
                
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(webhook_url, json=alert, timeout=10) as resp:
                        if resp.status == 200:
                            self.logger.info(f"Webhook sent successfully to {webhook_url}")
                        else:
                            self.logger.warning(f"Webhook failed for {webhook_url} with status: {resp.status} - Response: {await resp.text()}")
                            
            except aiohttp.ClientError as e:
                self.logger.error(f"Aiohttp client error sending webhook to {webhook_url}: {e}")
            except asyncio.TimeoutError:
                self.logger.error(f"Webhook to {webhook_url} timed out after 10 seconds.")
            except Exception as e:
                self.logger.error(f"Unexpected error sending webhook to {webhook_url}: {e}", exc_info=True)