"""Email notifier implementation"""
import asyncio
import smtplib
import logging
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List
from .base_notifier import BaseNotifier

logger = logging.getLogger(__name__)


class EmailNotifier(BaseNotifier):
    """Email notifier using SMTP"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.smtp_server = config.get('smtp_server', 'smtp.gmail.com')
        self.smtp_port = config.get('smtp_port', 587)
        self.username = config.get('email_username')
        self.password = config.get('email_password')
        self.from_email = config.get('from_email', self.username)
        self.recipients = config.get('recipients', [])
        
    async def initialize(self) -> bool:
        """Initialize email notifier"""
        if not self.username or not self.password:
            logger.warning("Email credentials not configured")
            return False
        
        # Test SMTP connection
        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.username, self.password)
            server.quit()
            logger.info("Email SMTP connection tested successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize email notifier: {e}")
            return False
    
    async def send(self, alert_type: str, message: str, data: Dict[str, Any] = None) -> bool:
        """Send email notification"""
        if not self.enabled or not self.recipients:
            return False
        
        try:
            # Create email message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Smart Thermostat Alert: {alert_type.replace('_', ' ').title()}"
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.recipients)
            
            # Create HTML and text versions
            html_body = self._create_html_body(alert_type, message, data or {})
            text_body = self._create_text_body(alert_type, message, data or {})
            
            msg.attach(MIMEText(text_body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))
            
            # Send email
            await asyncio.get_event_loop().run_in_executor(
                None, self._send_email_sync, msg
            )
            
            logger.info(f"Email notification sent to {len(self.recipients)} recipients")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email notification: {e}")
            return False
    
    def _send_email_sync(self, msg: MIMEMultipart):
        """Send email synchronously (runs in executor)"""
        server = smtplib.SMTP(self.smtp_server, self.smtp_port)
        server.starttls()
        server.login(self.username, self.password)
        server.send_message(msg)
        server.quit()
    
    def _create_html_body(self, alert_type: str, message: str, data: Dict[str, Any]) -> str:
        """Create HTML email body"""
        color_map = {
            'critical': '#dc3545',
            'warning': '#ffc107', 
            'info': '#17a2b8',
            'maintenance': '#007bff'
        }
        
        color = color_map.get(alert_type, '#6c757d')
        
        html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
              <div style="background-color: {color}; color: white; padding: 20px; border-radius: 8px 8px 0 0;">
                <h1 style="margin: 0; font-size: 24px;">🏠 Smart Thermostat Alert</h1>
                <h2 style="margin: 10px 0 0 0; font-size: 18px; opacity: 0.9;">{alert_type.replace('_', ' ').title()}</h2>
              </div>
              <div style="padding: 20px;">
                <p style="font-size: 16px; line-height: 1.5; color: #333;">{message}</p>
        """
        
        if data:
            html += """
                <h3 style="color: #333; border-bottom: 2px solid #eee; padding-bottom: 5px;">Additional Details:</h3>
                <table style="width: 100%; border-collapse: collapse; margin-top: 10px;">
            """
            
            for key, value in data.items():
                if key != 'timestamp':
                    html += f"""
                    <tr>
                      <td style="padding: 8px; border: 1px solid #ddd; background-color: #f9f9f9; font-weight: bold;">{key.replace('_', ' ').title()}</td>
                      <td style="padding: 8px; border: 1px solid #ddd;">{value}</td>
                    </tr>
                    """
            
            html += "</table>"
        
        html += f"""
              </div>
              <div style="background-color: #f8f9fa; padding: 15px; border-radius: 0 0 8px 8px; text-align: center; color: #6c757d; font-size: 12px;">
                Smart Thermostat AI System • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
              </div>
            </div>
          </body>
        </html>
        """
        
        return html
    
    def _create_text_body(self, alert_type: str, message: str, data: Dict[str, Any]) -> str:
        """Create plain text email body"""
        text = f"""
Smart Thermostat Alert: {alert_type.replace('_', ' ').title()}
{'=' * 50}

{message}
"""
        
        if data:
            text += "\nAdditional Details:\n"
            text += "-" * 20 + "\n"
            for key, value in data.items():
                if key != 'timestamp':
                    text += f"{key.replace('_', ' ').title()}: {value}\n"
        
        text += f"\n\nGenerated by Smart Thermostat AI System\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return text
    
    async def cleanup(self):
        """Cleanup email resources"""
        # No persistent connections to cleanup for SMTP
        pass