import aiohttp
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any

logger = logging.getLogger(__name__)

class BaseWebhookNotifier(ABC):
    """Abstract base class for all webhook notifiers."""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self.logger = logger # Use the module-level logger

    @abstractmethod
    def _format_payload(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """
        Abstract method to format the generic alert into a service-specific payload.
        This must be implemented by concrete notifier classes.
        """
        pass

    async def send(self, alert: Dict[str, Any]):
        """
        Sends the formatted alert payload to the webhook URL.
        """
        payload_to_send = self._format_payload(alert)
        self.logger.info(f"Sending to {self.__class__.__name__} at {self.webhook_url} with payload: {payload_to_send}")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload_to_send, timeout=10) as resp:
                    if resp.status == 200:
                        self.logger.info(f"Webhook sent successfully to {self.webhook_url}")
                    else:
                        response_text = await resp.text()
                        self.logger.warning(f"Webhook failed for {self.webhook_url} with status: {resp.status} - Response: {response_text}")

        except aiohttp.ClientError as e:
            self.logger.error(f"Aiohttp client error sending webhook to {self.webhook_url}: {e}")
        except asyncio.TimeoutError:
            self.logger.error(f"Webhook to {self.webhook_url} timed out after 10 seconds.")
        except Exception as e:
            self.logger.error(f"Unexpected error sending webhook to {self.webhook_url}: {e}", exc_info=True)


class SlackWebhookNotifier(BaseWebhookNotifier):
    """
    Notifier for Slack Incoming Webhooks.
    Formats the generic alert into a Slack-compatible message.
    """
    def _format_payload(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        device_id = alert['data'].get('device_id', 'N/A')
        message = alert.get('message', 'No specific message.')
        priority = alert['data'].get('priority', 'unknown')
        recommendations = ', '.join(alert['data'].get('recommendations', ['No recommendations.']))
        total_estimate = alert['data'].get('estimated_cost', {}).get('total_estimate', 0.0)
        currency = alert['data'].get('estimated_cost', {}).get('currency', 'USD')
        optimal_schedule_date = alert['data'].get('optimal_schedule_date', 'N/A')
        
        # Extract date part if present
        if optimal_schedule_date != 'N/A' and 'T' in optimal_schedule_date:
            optimal_schedule_date = optimal_schedule_date.split('T')[0]

        text_message = (
            f"🚨 *Maintenance Alert:* {device_id}\n"
            f"> *Message:* {message}\n"
            f"> *Priority:* `{priority.upper()}`\n"
            f"> *Recommendations:* {recommendations}\n"
            f"> *Estimated Cost:* ${total_estimate:.2f} {currency}\n"
            f"> *Optimal Schedule Date:* {optimal_schedule_date}"
        )

        return {
            "text": text_message,
            "attachments": [
                {
                    "fields": [
                        {"title": "Device ID", "value": device_id, "short": True},
                        {"title": "Maintenance Score", "value": alert['data'].get('maintenance_score', 'N/A'), "short": True},
                        {"title": "Priority", "value": priority.upper(), "short": True},
                        {"title": "Estimated Cost", "value": f"${total_estimate:.2f} {currency}", "short": True},
                        {"title": "Optimal Schedule Date", "value": optimal_schedule_date, "short": True},
                    ],
                    "color": "#FFC0CB" if priority == "high" else "#FFA500" if priority == "medium" else "#ADD8E6"
                }
            ]
        }


class GenericWebhookNotifier(BaseWebhookNotifier):
    """
    Notifier for generic webhooks that can directly consume the alert payload.
    """
    def _format_payload(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        # For generic webhooks, send the alert as is.
        # You might want to return a deep copy if there's any chance the original
        # alert object could be modified elsewhere.
        return alert.copy()

# You can add more notifiers here, e.g.:
# class MicrosoftTeamsWebhookNotifier(BaseWebhookNotifier):
#     def _format_payload(self, alert: Dict[str, Any]) -> Dict[str, Any]:
#         # Logic to format for Microsoft Teams
#         pass