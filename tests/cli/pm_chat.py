"""Simple CLI for chatting with PM directly.

This tool allows rapid iteration on PM logic without external dependencies.
Perfect for testing intent classification, delegation, and prompt changes.

Usage:
    # Simple message
    uv run python -m autifyme_agents.cli.pm_chat "Catalog these sneakers, price $79"

    # With media (images, videos, voice, documents)
    uv run python -m autifyme_agents.cli.pm_chat "Catalog this product" --media test_images/sneaker.jpg
    uv run python -m autifyme_agents.cli.pm_chat "Transcribe this" --media test_audio/voice_note.ogg

    # Legacy --image flag (still supported)
    uv run python -m autifyme_agents.cli.pm_chat "Catalog this" --image test_images/product.jpg

    # Interactive mode
    uv run python -m autifyme_agents.cli.pm_chat --interactive
"""

import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain.messages import HumanMessage

from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.integrations.storage.postgres_saver_factory import get_checkpointer
from autifyme_agents.integrations.storage.storage_factory import get_storage
from autifyme_agents.workflows.project_manager import create_project_manager


def chat_with_pm(message: str, image_path: Path | None = None, thread_id: str = "local_test"):
    """Send a message to PM and print response.

    Args:
        message: User's text message
        image_path: Optional path to image file
        thread_id: Thread ID for conversation continuity
    """
    print(f"\n{'='*60}")
    print("INVOKING PM...")
    print(f"{'='*60}\n")

    # Setup
    storage: StorageInterface = get_storage()
    company_profile = storage.get_company_profile()
    checkpointer = get_checkpointer()

    # Create PM
    pm = create_project_manager(
        company_profile=company_profile,
        checkpointer=checkpointer,
        storage=storage,
    )

    # Build message
    content = f"User message: {message}"
    if image_path:
        if not image_path.exists():
            print(f"Warning: Image not found: {image_path}")
            print("Proceeding without image...\n")
        else:
            content += f"\nUser provided an image (path: {image_path})"

    print(f"Input:\n{content}\n")

    # Invoke PM
    try:
        result = pm.invoke(
            {"messages": [HumanMessage(content=content)]},
            config={"configurable": {"thread_id": thread_id}},
        )

        # Extract response
        messages = result.get("messages", [])
        if messages:
            last_message = messages[-1]
            response = getattr(last_message, "content", str(last_message))

            print(f"{'='*60}")
            print("PM RESPONSE:")
            print(f"{'='*60}")
            print(response)
            print(f"{'='*60}\n")
        else:
            print("\n[No response from PM]\n")

    except Exception as e:
        print(f"\n{'='*60}")
        print("ERROR:")
        print(f"{'='*60}")
        print(f"{type(e).__name__}: {e}")
        print(f"{'='*60}\n")
        raise


def interactive_mode():
    """Interactive chat loop."""
    print("=" * 60)
    print("PM INTERACTIVE CHAT")
    print("=" * 60)
    print()
    print("Commands:")
    print("  exit, quit         - Exit the chat")
    print("  media <path>       - Set media file for next message")
    print("  image <path>       - Set media file (alias)")
    print("  clear              - Clear media")
    print("  new                - Start new conversation (new thread)")
    print()
    print("Type your message and press Enter to send.")
    print("=" * 60)
    print()

    media_path = None
    thread_id = "local_test"
    message_count = 0

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ["exit", "quit"]:
                print("\nGoodbye!\n")
                break

            if user_input.lower().startswith(("media ", "image ")):
                media_path = Path(user_input.split(maxsplit=1)[1].strip())
                if media_path.exists():
                    print(f"[Media set: {media_path}]")
                else:
                    print(f"[Warning: Media not found: {media_path}]")
                continue

            if user_input.lower() == "clear":
                media_path = None
                print("[Media cleared]")
                continue

            if user_input.lower() == "new":
                message_count = 0
                thread_id = f"local_test_{Path().absolute().stat().st_mtime}"
                print(f"[Started new conversation: {thread_id}]")
                continue

            # Send message
            message_count += 1
            chat_with_pm(user_input, media_path, thread_id)
            media_path = None  # Reset after use

        except KeyboardInterrupt:
            print("\n\nExiting...\n")
            break
        except Exception as e:
            print(f"\nError: {e}")
            print("Continuing...\n")


def main():
    """CLI entry point."""
    # Load environment
    env_path = Path.cwd() / ".env"
    if not env_path.exists():
        # Try parent directory
        env_path = Path.cwd().parent / ".env"

    if env_path.exists():
        load_dotenv(env_path)
    else:
        print("Warning: .env file not found")

    # Parse arguments
    if len(sys.argv) > 1:
        if sys.argv[1] in ["--help", "-h"]:
            print(__doc__)
            return

        if sys.argv[1] in ["--interactive", "-i"]:
            interactive_mode()
            return

        if sys.argv[1] in ["--media", "--image", "-img"]:
            if len(sys.argv) < 4:
                print("Usage: pm_chat --media <path> 'Your message'")
                sys.exit(1)
            media_path = Path(sys.argv[2])
            message = " ".join(sys.argv[3:])
            chat_with_pm(message, media_path)
            return

        # Default: treat all args as message
        message = " ".join(sys.argv[1:])
        chat_with_pm(message)
    else:
        # No args: show help
        print(__doc__)
        print("\nNo message provided. Use --interactive for chat mode.\n")


if __name__ == "__main__":
    main()
