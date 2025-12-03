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

    def send_typing_indicator(self, message_id: str) -> dict[str, Any]:
        """Mark message as read and show typing indicator.

        WhatsApp typing indicator behavior (per official Cloud API docs):
        - Marks the incoming message as read
        - Shows "typing..." animation to sender
        - Lasts 25 seconds or until next message sent
        - Should only be used when bot will respond (prevents poor UX)

        Official format:
        {
          "messaging_product": "whatsapp",
          "status": "read",
          "message_id": "<WHATSAPP_MESSAGE_ID>",
          "typing_indicator": {
            "type": "text"
          }
        }

        Args:
            message_id: WhatsApp message ID from incoming webhook

        Returns:
            WhatsApp API response dict

        Raises:
            httpx.HTTPStatusError: If API call fails
        """
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
            "typing_indicator": {
                "type": "text"
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
            "WhatsApp typing indicator sent (message marked as read)",
            extra={"message_id": message_id},
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

    def send_image(self, recipient: str, media_id: str, *, caption: str | None = None) -> dict[str, Any]:
        """Send image message using WhatsApp media_id.

        Media must be uploaded first via WhatsAppMediaClient.upload_media().

        Args:
            recipient: WhatsApp phone number (e.g., "919876543210")
            media_id: WhatsApp media ID from upload_media()
            caption: Optional image caption (max 1024 chars)

        Returns:
            WhatsApp API response dict

        Raises:
            httpx.HTTPStatusError: If API call fails
        """
        image_payload: dict[str, Any] = {"id": media_id, "quality": "hd"}
        if caption:
            # WhatsApp caption limit is 1024 chars
            if len(caption) > 1024:
                caption = caption[:1021] + "..."
            image_payload["caption"] = caption

        payload = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "image",
            "image": image_payload,
        }

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        response = httpx.post(self._base_url, json=payload, headers=headers, timeout=10.0)
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        logger.debug(
            "WhatsApp image sent",
            extra={
                "recipient": recipient,
                "media_id": media_id,
                "has_caption": caption is not None,
                "message_id": (data.get("messages") or [{}])[0].get("id"),
            },
        )
        return data
