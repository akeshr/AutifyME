"""Live interactive monitor - send messages/files and see real-time analysis.

This tool provides a live interactive shell where you can:
- Send text messages and see PM analysis in real-time
- Attach images/files and watch them get processed
- Interact with HITL approvals naturally
- Monitor database changes live
- See complete agent interactions and state transitions

Usage:
    uv run python run_live_monitor.py

Commands:
    > Your message here              - Send text message
    > @image path/to/file.jpg        - Attach image
    > @file path/to/document.pdf     - Attach document
    > @status                        - Show current state and DB status
    > @history                       - Show conversation history
    > @db                            - Show database contents
    > @clear                         - Clear conversation state
    > @help                          - Show help
    > @quit                          - Exit monitor
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


def safe_print(text: str) -> None:
    """Print text safely, handling console encoding issues."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode('ascii', errors='replace').decode('ascii'))


class LiveMonitorChannel:
    """Console channel for live monitoring with real-time output."""

    def format_thread_id(self, sender: str) -> str:
        return f"monitor:{sender}"

    def send_text(self, recipient: str, message: str, *, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        safe_print(f"\n{'='*60}")
        safe_print("📤 SYSTEM MESSAGE:")
        safe_print(f"{'='*60}")
        safe_print(message)
        safe_print(f"{'='*60}\n")
        return {"status": "sent"}

    def send_approval_request(self, recipient: str, draft: Any) -> dict[str, Any]:
        safe_print(f"\n{'='*60}")
        safe_print("⏸️  APPROVAL REQUEST:")
        safe_print(f"{'='*60}")

        # Convert to dict for display
        draft_dict = draft.model_dump() if hasattr(draft, 'model_dump') else draft

        def json_encoder(obj):
            if hasattr(obj, '__str__'):
                return str(obj)
            raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

        safe_print(json.dumps(draft_dict, indent=2, ensure_ascii=False, default=json_encoder))
        safe_print(f"{'='*60}")

        # Interactive approval
        while True:
            safe_print("\nYour response:")
            safe_print("  [a] Approve")
            safe_print("  [r] Reject")
            safe_print("  [e] Edit")

            choice = input("\nChoice: ").strip().lower()

            if choice in ['a', 'approve']:
                safe_print("\n✅ Approved - continuing workflow...")
                return {"status": "approved", "draft": draft}

            elif choice in ['r', 'reject']:
                feedback = input("Rejection reason: ").strip()
                safe_print("\n❌ Rejected - workflow will adjust...")
                return {"status": "rejected", "feedback": feedback}

            elif choice in ['e', 'edit']:
                edits = input("Your edits (e.g., 'price 99.99'): ").strip()
                safe_print("\n✏️  Edits applied - continuing...")

                # Parse simple edits
                parts = edits.split(maxsplit=1)
                if len(parts) == 2:
                    field, value_str = parts
                    if hasattr(draft, field):
                        try:
                            field_value = getattr(draft, field)
                            converted_value: Any = value_str
                            if isinstance(field_value, float):
                                converted_value = float(value_str)
                            elif isinstance(field_value, int):
                                converted_value = int(value_str)
                            setattr(draft, field, converted_value)
                            safe_print(f"   Updated {field}: {converted_value}")
                        except ValueError:
                            safe_print(f"   Warning: Could not convert {value_str} to correct type")

                return {"status": "approved", "draft": draft}

            else:
                safe_print("Invalid choice. Try again.")

    def send_completion(self, recipient: str, result: Any) -> dict[str, Any]:
        safe_print(f"\n{'='*60}")
        safe_print("✅ WORKFLOW COMPLETE:")
        safe_print(f"{'='*60}")
        safe_print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        safe_print(f"{'='*60}\n")
        return {"status": "sent"}

    def send_error(self, recipient: str, error_type: str, custom_message: str | None = None) -> dict:
        safe_print(f"\n{'='*60}")
        safe_print("❌ ERROR:")
        safe_print(f"{'='*60}")
        safe_print(f"Type: {error_type}")
        if custom_message:
            safe_print(f"Message: {custom_message}")
        safe_print(f"{'='*60}\n")
        return {"status": "sent"}

    def download_media(self, media_id: str) -> Path:
        # For local testing, media_id is already a path
        return Path(media_id)


class LiveMonitor:
    """Live interactive monitoring and testing tool."""

    def __init__(self):
        """Initialize live monitor."""
        from autifyme_agents.integrations.storage.postgres_saver_factory import get_checkpointer
        from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient
        from autifyme_agents.workflows.orchestration.runner_v2 import WorkflowRunner

        self.storage = SupabaseStorageClient()
        self.checkpointer = get_checkpointer()
        self.channel = LiveMonitorChannel()

        # Create workflow runner
        self.runner = WorkflowRunner(
            channel=self.channel,
            storage=self.storage,
            checkpointer=self.checkpointer
        )

        # Track state
        self.thread_id = f"monitor_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.message_count = 0
        self.session_start = datetime.now()

        safe_print("\n" + "="*70)
        safe_print("🔴 LIVE MONITOR INITIALIZED")
        safe_print("="*70)
        safe_print(f"Thread ID: {self.thread_id}")
        safe_print(f"Session started: {self.session_start.strftime('%Y-%m-%d %H:%M:%S')}")
        safe_print("="*70)

    def show_db_status(self) -> None:
        """Show current database status."""
        safe_print("\n" + "-"*70)
        safe_print("🗄️  DATABASE STATUS")
        safe_print("-"*70)

        try:
            company_profile = self.storage.get_company_profile()

            if company_profile:
                safe_print(f"Company: {company_profile.company_name}")
                safe_print(f"Products in catalog: {len(company_profile.products)}")

                if company_profile.products:
                    safe_print("\nRecent products:")
                    for product in company_profile.products[-3:]:
                        safe_print(f"  • {product.name} - ${product.price}")
            else:
                safe_print("No company profile found")

        except Exception as e:
            safe_print(f"Error reading database: {e}")

        safe_print("-"*70)

    def show_conversation_state(self) -> None:
        """Show current conversation state from checkpoint."""
        safe_print("\n" + "-"*70)
        safe_print("💬 CONVERSATION STATE")
        safe_print("-"*70)

        try:
            config = {"configurable": {"thread_id": self.thread_id}}
            checkpoint_tuple = self.checkpointer.get_tuple(config)

            if checkpoint_tuple and checkpoint_tuple.checkpoint:
                checkpoint = checkpoint_tuple.checkpoint
                channel_values = checkpoint.get("channel_values", {})
                messages = channel_values.get("messages", [])

                safe_print(f"Messages in state: {len(messages)}")
                safe_print(f"Checkpoint ID: {checkpoint_tuple.config['configurable'].get('checkpoint_id', 'N/A')}")

                if messages:
                    safe_print("\nRecent messages:")
                    for msg in messages[-3:]:
                        msg_type = msg.__class__.__name__
                        content_preview = str(msg.content)[:80]
                        safe_print(f"  • {msg_type}: {content_preview}")
            else:
                safe_print("No checkpoint found for this thread")

        except Exception as e:
            safe_print(f"Error reading state: {e}")

        safe_print("-"*70)

    def show_history(self) -> None:
        """Show conversation history."""
        safe_print("\n" + "-"*70)
        safe_print("📜 CONVERSATION HISTORY")
        safe_print("-"*70)

        try:
            config = {"configurable": {"thread_id": self.thread_id}}
            checkpoint_tuple = self.checkpointer.get_tuple(config)

            if checkpoint_tuple and checkpoint_tuple.checkpoint:
                channel_values = checkpoint_tuple.checkpoint.get("channel_values", {})
                messages = channel_values.get("messages", [])

                if messages:
                    for i, msg in enumerate(messages, 1):
                        msg_type = msg.__class__.__name__
                        safe_print(f"\n{i}. {msg_type}")
                        safe_print(f"   {msg.content}")
                else:
                    safe_print("No messages in history")
            else:
                safe_print("No history found")

        except Exception as e:
            safe_print(f"Error reading history: {e}")

        safe_print("-"*70)

    def clear_state(self) -> None:
        """Clear conversation state and start fresh."""
        self.thread_id = f"monitor_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.message_count = 0
        safe_print(f"\n✅ State cleared. New thread ID: {self.thread_id}")

    def process_message(self, text: str, image_path: Path | None = None) -> None:
        """Process a message through the workflow with real-time output.

        Args:
            text: Message text
            image_path: Optional image file path
        """
        self.message_count += 1

        safe_print("\n" + "="*70)
        safe_print(f"📨 MESSAGE #{self.message_count}")
        safe_print("="*70)
        safe_print(f"Text: {text}")
        if image_path:
            safe_print(f"Image: {image_path}")
        safe_print(f"Time: {datetime.now().strftime('%H:%M:%S')}")
        safe_print("="*70)

        try:
            safe_print("\n🤖 PROCESSING...")
            safe_print("-"*70)

            # Use unique sender for each message to avoid checkpoint pollution
            import uuid
            sender = f"monitor_{uuid.uuid4().hex[:8]}"

            # Run through workflow runner
            self.runner.handle_message(
                sender=sender,
                text=text,
                media_id=str(image_path) if image_path else None
            )

            safe_print("\n✅ WORKFLOW COMPLETE")
            safe_print("="*70)

            # Show updated DB status
            self.show_db_status()

        except KeyboardInterrupt:
            safe_print("\n\n⚠️  Interrupted by user")
            return

        except Exception as e:
            safe_print(f"\n❌ ERROR: {e}")
            import traceback
            safe_print(traceback.format_exc())

    def show_help(self) -> None:
        """Show help message."""
        safe_print("\n" + "-"*70)
        safe_print("📖 LIVE MONITOR COMMANDS")
        safe_print("-"*70)
        safe_print("  > Your message here          - Send text message")
        safe_print("  > @image path/to/file.jpg    - Attach image")
        safe_print("  > @file path/to/document.pdf - Attach document")
        safe_print("  > @status                    - Show state and DB status")
        safe_print("  > @history                   - Show conversation history")
        safe_print("  > @db                        - Show database contents")
        safe_print("  > @clear                     - Clear conversation state")
        safe_print("  > @help                      - Show this help")
        safe_print("  > @quit                      - Exit monitor")
        safe_print("-"*70)

    def run(self) -> None:
        """Run interactive monitoring loop."""
        self.show_help()

        while True:
            try:
                safe_print("\n" + ">"*70)
                user_input = input("You: ").strip()

                if not user_input:
                    continue

                # Handle commands
                if user_input.startswith("@"):
                    cmd = user_input[1:].lower()

                    if cmd == "quit" or cmd == "exit":
                        safe_print("\n👋 Exiting live monitor...")
                        break

                    elif cmd == "help":
                        self.show_help()

                    elif cmd == "status":
                        self.show_conversation_state()
                        self.show_db_status()

                    elif cmd == "history":
                        self.show_history()

                    elif cmd == "db":
                        self.show_db_status()

                    elif cmd == "clear":
                        self.clear_state()

                    elif cmd.startswith("image "):
                        # Extract image path and optional caption
                        parts = cmd[6:].strip().split(" ", 1)
                        image_path = Path(parts[0])

                        if not image_path.exists():
                            safe_print(f"❌ Image not found: {image_path}")
                            continue

                        caption = parts[1] if len(parts) > 1 else "Process this image"
                        self.process_message(caption, image_path)

                    elif cmd.startswith("file "):
                        # Extract file path
                        file_path = Path(cmd[5:].strip())

                        if not file_path.exists():
                            safe_print(f"❌ File not found: {file_path}")
                            continue

                        safe_print("⚠️  File processing not yet implemented")

                    else:
                        safe_print(f"❌ Unknown command: @{cmd}")
                        safe_print("Type '@help' for available commands")

                else:
                    # Process as regular message
                    self.process_message(user_input)

            except KeyboardInterrupt:
                safe_print("\n\n👋 Exiting live monitor...")
                break

            except EOFError:
                safe_print("\n\n👋 Exiting live monitor...")
                break

            except Exception as e:
                safe_print(f"\n❌ ERROR: {e}")
                import traceback
                safe_print(traceback.format_exc())


def main():
    """CLI entry point."""
    # Load environment
    env_path = Path.cwd() / ".env"
    if not env_path.exists():
        env_path = Path.cwd().parent / ".env"

    if env_path.exists():
        load_dotenv(env_path)
    else:
        print("Warning: .env file not found")

    safe_print("\n" + "="*70)
    safe_print("🔴 AUTIFYME LIVE MONITOR")
    safe_print("="*70)
    safe_print("\nReal-time interactive testing with complete analysis")
    safe_print("Type '@help' for commands, '@quit' to exit")
    safe_print("="*70)

    monitor = LiveMonitor()
    monitor.run()


if __name__ == "__main__":
    main()
