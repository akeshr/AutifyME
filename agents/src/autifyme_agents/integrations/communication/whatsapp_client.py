"""WhatsApp Business Cloud client adapter."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from autifyme_agents.core.config import settings

logger = logging.getLogger(__name__)


class WhatsAppClient:
    """Thin wrapper around the WhatsApp Business Cloud send API."""

    def __init__(self, *, access_token: str | None = None, phone_number_id: str | None = None, api_version: str | None = None) -> None:
        self.access_token = access_token or settings.WHATSAPP_ACCESS_TOKEN
        self.phone_number_id = phone_number_id or settings.WHATSAPP_PHONE_NUMBER_ID
        self.api_version = api_version or settings.WHATSAPP_API_VERSION

        if not self.access_token or not self.phone_number_id:
            raise ValueError("WhatsApp credentials are not configured")

        self._base_url = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}/messages"

    def send_typing_indicator(self, recipient: str, *, typing: bool = True) -> dict[str, Any]:
        """Send typing indicator to WhatsApp user.

        WhatsApp typing indicator behavior:
        - Shows "typing..." animation for 25 seconds or until message sent
        - Can be explicitly stopped by sending typing=False
        - Recommended for operations that may take >2 seconds

        Args:
            recipient: WhatsApp phone number (E.164 format)
            typing: True to show typing, False to hide

        Returns:
            WhatsApp API response dict

        Raises:
            httpx.HTTPStatusError: If API call fails
        """
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "typing_indicator",
            "typing_indicator": {
                "status": "typing" if typing else "text"
            }
        }

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        response = httpx.post(self._base_url, json=payload, headers=headers, timeout=10.0)
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        logger.debug(
            "WhatsApp typing indicator sent",
            extra={
                "recipient": recipient,
                "typing": typing,
            },
        )
        return data

    def send_text(self, recipient: str, message: str, *, preview_url: bool = False) -> dict[str, Any]:
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "text",
            "text": {"body": message, "preview_url": preview_url},
        }

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        response = httpx.post(self._base_url, json=payload, headers=headers, timeout=10.0)
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        logger.debug(
            "WhatsApp message sent",
            extra={
                "recipient": recipient,
                "message_id": (data.get("messages") or [{}])[0].get("id"),
            },
        )
        return data
