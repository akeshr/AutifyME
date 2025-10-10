"""Messaging channel adapters.

This package contains channel-specific implementations for different
messaging platforms (WhatsApp, SMS, Telegram, etc.).

Each adapter implements the MessagingChannel protocol.
"""

from autifyme_agents.workflows.channels.protocol import MessagingChannel

__all__ = ["MessagingChannel"]
