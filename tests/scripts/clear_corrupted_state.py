"""Clear corrupted checkpoint state for users experiencing chat history errors.

This script clears the LangGraph checkpoint for a specific user to recover from
the 'INVALID_CHAT_HISTORY' error where tool calls don't have matching responses.

Usage:
    uv run python agents/scripts/clear_corrupted_state.py --phone 917258067800
"""

from __future__ import annotations

import argparse
from pathlib import Path

from dotenv import load_dotenv

from autifyme_agents.integrations.storage.postgres_saver_factory import get_checkpointer
from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient
from autifyme_agents.core.logging_config import get_logger

load_dotenv(Path.cwd() / ".env")
logger = get_logger(__name__)


def clear_user_state(phone_number: str, channel: str = "whatsapp") -> None:
    """Clear checkpoint and approval state for a user."""
    thread_id = f"{channel}:{phone_number}"

    logger.info(f"Clearing state for thread_id: {thread_id}")

    # Clear checkpoint
    try:
        checkpointer = get_checkpointer()
        checkpointer.delete_thread(thread_id)
        logger.info(f"✅ Cleared checkpoint for {thread_id}")
    except Exception as exc:
        logger.error(f"❌ Failed to clear checkpoint: {exc}")

    # Clear pending approval
    try:
        storage = SupabaseStorageClient()
        approval = storage.get_pending_approval(thread_id)
        if approval:
            storage.delete_pending_approval(thread_id)
            logger.info(f"✅ Cleared pending approval for {thread_id}")
        else:
            logger.info(f"No pending approval found for {thread_id}")
    except Exception as exc:
        logger.error(f"❌ Failed to clear approval: {exc}")

    logger.info(f"✅ State cleanup complete for {phone_number}")


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Clear corrupted state for WhatsApp users",
    )
    parser.add_argument(
        "--phone",
        required=True,
        help="Phone number (e.g., 917258067800)",
    )
    parser.add_argument(
        "--channel",
        default="whatsapp",
        help="Channel prefix (default: whatsapp)",
    )

    args = parser.parse_args()
    clear_user_state(args.phone, args.channel)


if __name__ == "__main__":
    main()
