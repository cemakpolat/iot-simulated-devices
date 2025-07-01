"""Webhook notifier implementations with improved error handling"""
import asyncio
import logging
from typing import Dict, Any, List
import aiohttp
import json
from datetime import datetime
from .base_notifier import BaseNotifier

logger = logging.getLogger(__name__)


class WebhookNotifier(BaseNotifier):
    """Base webhook notifier with enhanced error handling"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.webhook_urls = config.get('webhook_urls', [])
        if isinstance(self.webhook_urls, str):
            self.webhook_urls = [self.webhook_urls]
        self.session = None
        self.timeout = config.get('timeout', 30)  # Increased timeout
        self.retry_attempts = config.get('retry_attempts', 3)  # More retries
    
    async def initialize(self) -> bool:
        """Initialize webhook notifier"""
        if not self.webhook_urls:
            logger.warning("No webhook URLs configured")
            return False
        
        # Create aiohttp session with proper timeout and connector settings
        connector = aiohttp.TCPConnector(
            limit=10,
            limit_per_host=2,
            ttl_dns_cache=300,
            use_dns_cache=True,
        )
        timeout = aiohttp.ClientTimeout(
            total=self.timeout,
            connect=10,
            sock_read=10
        )
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers={'User-Agent': 'Smart-Thermostat-AI/1.0'}
        )
        logger.info(f"Webhook notifier initialized with {len(self.webhook_urls)} URLs")
        return True
    
    async def send(self, alert_type: str, message: str, data: Dict[str, Any] = None) -> bool:
        """Send webhook notification to all configured URLs"""
        if not self.enabled or not self.webhook_urls or not self.session:
            logger.warning(f"Webhook notifier not ready: enabled={self.enabled}, urls={len(self.webhook_urls)}, session={self.session is not None}")
            return False
        
        success_count = 0
        logger.info(f"Sending webhook notification to {len(self.webhook_urls)} URLs")
        
        # Send to all URLs concurrently
        tasks = []
        for url in self.webhook_urls:
            task = asyncio.create_task(self._send_to_url(url, alert_type, message, data or {}))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Webhook to {self.webhook_urls[i]} failed with exception: {result}")
            elif result:
                success_count += 1
        
        logger.info(f"Webhook notifications: {success_count}/{len(self.webhook_urls)} successful")
        return success_count > 0
    
    async def _send_to_url(self, url: str, alert_type: str, message: str, data: Dict[str, Any]) -> bool:
        """Send webhook to a specific URL with retry logic"""
        for attempt in range(self.retry_attempts + 1):
            try:
                payload = await self._format_payload(url, alert_type, message, data)
                logger.debug(f"Sending webhook to {url} (attempt {attempt + 1}): {payload}")
                
                async with self.session.post(
                    url,
                    json=payload,
                    headers={
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    }
                ) as response:
                    response_text = await response.text()
                    
                    if response.status in [200, 201, 202, 204]:
                        logger.info(f"✅ Webhook sent successfully to {url} (status: {response.status})")
                        return True
                    else:
                        logger.warning(f"❌ Webhook failed for {url} - Status: {response.status}, Response: {response_text}")
                        if attempt < self.retry_attempts and response.status >= 500:
                            # Only retry on server errors
                            await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        elif response.status < 500:
                            # Client error - don't retry
                            return False
                        
            except asyncio.TimeoutError:
                logger.error(f"❌ Webhook timeout for {url} (attempt {attempt + 1})")
                if attempt < self.retry_attempts:
                    await asyncio.sleep(2 ** attempt)
            except aiohttp.ClientError as e:
                logger.error(f"❌ Webhook client error for {url} (attempt {attempt + 1}): {e}")
                if attempt < self.retry_attempts:
                    await asyncio.sleep(2 ** attempt)
            except Exception as e:
                logger.error(f"❌ Unexpected webhook error for {url} (attempt {attempt + 1}): {e}")
                if attempt < self.retry_attempts:
                    await asyncio.sleep(2 ** attempt)
        
        logger.error(f"❌ All webhook attempts failed for {url}")
        return False
    
    async def _format_payload(self, url: str, alert_type: str, message: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format payload based on webhook URL"""
        if 'slack.com' in url or 'hooks.slack.com' in url:
            return await self._format_slack_payload(alert_type, message, data)
        elif 'discord.com' in url:
            return await self._format_discord_payload(alert_type, message, data)
        elif 'teams.microsoft.com' in url or 'outlook.office.com' in url:
            return await self._format_teams_payload(alert_type, message, data)
        else:
            return await self._format_generic_payload(alert_type, message, data)
    
    async def _format_slack_payload(self, alert_type: str, message: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format payload for Slack webhook"""
        severity = data.get('severity', 'medium')
        color_map = {
            "critical": "danger",
            "high": "warning",
            "medium": "good",
            "low": "#36a64f"
        }
        
        color = color_map.get(severity, "#808080")
        
        # Create fields from data, excluding internal fields
        fields = []
        for key, value in data.items():
            if key not in ['timestamp', 'severity'] and value is not None:
                fields.append({
                    "title": key.replace('_', ' ').title(),
                    "value": str(value),
                    "short": True
                })
        
        return {
            "text": f"🏠 Smart Thermostat Alert",
            "attachments": [{
                "color": color,
                "title": f"{alert_type.replace('_', ' ').title()}",
                "text": message,
                "fields": fields,
                "footer": "Smart Thermostat AI",
                "ts": int(datetime.now().timestamp())
            }]
        }
    
    async def _format_teams_payload(self, alert_type: str, message: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format payload for Microsoft Teams webhook"""
        severity = data.get('severity', 'medium')
        color_map = {
            "critical": "FF0000",
            "high": "FFA500", 
            "medium": "FFFF00",
            "low": "008000"
        }
        
        theme_color = color_map.get(severity, "808080")
        
        facts = []
        for key, value in data.items():
            if key not in ['timestamp', 'severity'] and value is not None:
                facts.append({
                    "name": key.replace('_', ' ').title(),
                    "value": str(value)
                })
        
        return {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": theme_color,
            "summary": f"Smart Thermostat Alert: {alert_type}",
            "title": f"🏠 Smart Thermostat Alert",
            "sections": [{
                "activityTitle": alert_type.replace('_', ' ').title(),
                "activitySubtitle": message,
                "facts": facts
            }]
        }
    
    async def _format_discord_payload(self, alert_type: str, message: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format payload for Discord webhook"""
        severity = data.get('severity', 'medium')
        color_map = {
            "critical": 0xFF0000,
            "high": 0xFFA500,
            "medium": 0xFFFF00,
            "low": 0x008000
        }
        
        color = color_map.get(severity, 0x808080)
        
        fields = []
        for key, value in data.items():
            if key not in ['timestamp', 'severity'] and value is not None:
                fields.append({
                    "name": key.replace('_', ' ').title(),
                    "value": str(value),
                    "inline": True
                })
        
        return {
            "embeds": [{
                "title": f"🏠 Smart Thermostat Alert",
                "description": message,
                "color": color,
                "fields": fields,
                "footer": {
                    "text": f"Smart Thermostat AI • {alert_type.replace('_', ' ').title()}"
                },
                "timestamp": datetime.now().isoformat()
            }]
        }
    
    async def _format_generic_payload(self, alert_type: str, message: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format payload for generic webhook"""
        return {
            "source": "smart_thermostat_ai",
            "alert_type": alert_type,
            "message": message,
            "severity": data.get('severity', 'medium'),
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
    
    async def cleanup(self):
        """Cleanup webhook resources"""
        if self.session:
            await self.session.close()
            logger.info("Webhook session closed")


class SlackWebhookNotifier(WebhookNotifier):
    """Slack-specific webhook notifier"""
    
    def __init__(self, webhook_url: str):
        config = {
            'webhook_urls': [webhook_url],
            'timeout': 30,
            'retry_attempts': 3
        }
        super().__init__(config)
        self.webhook_url = webhook_url
        logger.info(f"SlackWebhookNotifier initialized with URL: {webhook_url}")
    
    async def _format_payload(self, url: str, alert_type: str, message: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Always use Slack formatting"""
        return await self._format_slack_payload(alert_type, message, data)


class GenericWebhookNotifier(WebhookNotifier):
    """Generic webhook notifier"""
    
    def __init__(self, webhook_url: str):
        config = {
            'webhook_urls': [webhook_url],
            'timeout': 30,
            'retry_attempts': 3
        }
        super().__init__(config)
        self.webhook_url = webhook_url
        logger.info(f"GenericWebhookNotifier initialized with URL: {webhook_url}")
    
    async def _format_payload(self, url: str, alert_type: str, message: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Always use generic formatting"""
        return await self._format_generic_payload(alert_type, message, data)


class TeamsWebhookNotifier(WebhookNotifier):
    """Microsoft Teams webhook notifier"""
    
    def __init__(self, webhook_url: str):
        config = {
            'webhook_urls': [webhook_url],
            'timeout': 30,
            'retry_attempts': 3
        }
        super().__init__(config)
        self.webhook_url = webhook_url
        logger.info(f"TeamsWebhookNotifier initialized with URL: {webhook_url}")
    
    async def _format_payload(self, url: str, alert_type: str, message: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Always use Teams formatting"""
        return await self._format_teams_payload(alert_type, message, data)


class DiscordWebhookNotifier(WebhookNotifier):
    """Discord webhook notifier"""
    
    def __init__(self, webhook_url: str):
        config = {
            'webhook_urls': [webhook_url],
            'timeout': 30,
            'retry_attempts': 3
        }
        super().__init__(config)
        self.webhook_url = webhook_url
        logger.info(f"DiscordWebhookNotifier initialized with URL: {webhook_url}")
    
    async def _format_payload(self, url: str, alert_type: str, message: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Always use Discord formatting"""
        return await self._format_discord_payload(alert_type, message, data)