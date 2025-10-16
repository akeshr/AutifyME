"""Communication tools for outbound messaging."""

import logging

from langchain.tools import tool

from autifyme_agents.core.exceptions import ExternalAPIError
from autifyme_agents.integrations.communication.whatsapp_client import WhatsAppClient

logger = logging.getLogger(__name__)


@tool("send_whatsapp_message")
def send_whatsapp_message(recipient: str, message: str, *, client: WhatsAppClient | None = None) -> str:
    """Send a WhatsApp message to the specified recipient."""

    messaging_client = client or WhatsAppClient()
    try:
        response = messaging_client.send_text(recipient=recipient, message=message)
        message_id = response.get("messages", [{}])[0].get("id")
        return message_id or ""
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to send WhatsApp message")
        raise ExternalAPIError(
            message=str(exc),
            tool_name="send_whatsapp_message",
            api_name="WhatsApp Business Cloud",
            original_error=exc,
        ) from exc


def create_send_whatsapp_message_tool():
    return send_whatsapp_message
