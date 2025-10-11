"""State inspection tools for debugging workflows.

This module provides tools to inspect LangGraph checkpoints, message history,
state variables, and tool call history during workflow execution.

Features:
- Checkpoint viewer (show full checkpoint state)
- Message history viewer (conversation timeline)
- Variable inspector (state variables)
- Tool call history (all tool invocations)
- State comparison (before/after)
- JSON export for offline analysis

Usage:
    # Inspect checkpoint for a specific thread
    uv run python -m autifyme_agents.cli.inspect --checkpoint --thread whatsapp:123456

    # Show message history
    uv run python -m autifyme_agents.cli.inspect --messages --thread whatsapp:123456

    # Show all state variables
    uv run python -m autifyme_agents.cli.inspect --variables --thread whatsapp:123456

    # Show tool call history
    uv run python -m autifyme_agents.cli.inspect --tools --thread whatsapp:123456

    # Full state dump
    uv run python -m autifyme_agents.cli.inspect --full --thread whatsapp:123456

    # Export to JSON
    uv run python -m autifyme_agents.cli.inspect --full --thread whatsapp:123456 --export state.json

    # List all threads
    uv run python -m autifyme_agents.cli.inspect --list-threads
"""

import sys
import json
from pathlib import Path
from typing import Any
from datetime import datetime
from dotenv import load_dotenv

from autifyme_agents.integrations.storage.postgres_saver_factory import get_checkpointer


def safe_print(text: str) -> None:
    """Print text safely, handling console encoding issues on Windows."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode('ascii', errors='replace').decode('ascii'))


class StateInspector:
    """Inspects workflow state from LangGraph checkpoints."""

    def __init__(self):
        """Initialize state inspector."""
        self.checkpointer = get_checkpointer()

    def list_threads(self) -> list[dict[str, Any]]:
        """List all available thread IDs with checkpoint metadata.

        Returns:
            List of thread information dictionaries
        """
        # Note: PostgresSaver doesn't expose a direct list method
        # This is a placeholder for future implementation
        print("⚠️  Thread listing not yet implemented for PostgresSaver")
        print("   Use known thread IDs (e.g., 'whatsapp:123456', 'console:test_user')")
        return []

    def get_checkpoint(self, thread_id: str, checkpoint_ns: str = "") -> dict[str, Any] | None:
        """Get checkpoint for a thread.

        Args:
            thread_id: Thread identifier
            checkpoint_ns: Optional checkpoint namespace

        Returns:
            Checkpoint data or None if not found
        """
        config = {
            "configurable": {
                "thread_id": thread_id,
            }
        }

        if checkpoint_ns:
            config["configurable"]["checkpoint_ns"] = checkpoint_ns

        try:
            checkpoint_tuple = self.checkpointer.get_tuple(config)

            if not checkpoint_tuple:
                return None

            # Extract checkpoint data
            checkpoint = checkpoint_tuple.checkpoint
            metadata = checkpoint_tuple.metadata
            parent_config = checkpoint_tuple.parent_config

            return {
                "checkpoint_id": checkpoint.get("id") if isinstance(checkpoint, dict) else str(checkpoint),
                "channel_values": checkpoint.get("channel_values") if isinstance(checkpoint, dict) else {},
                "metadata": metadata,
                "parent_config": parent_config,
                "pending_sends": checkpoint.get("pending_sends", []) if isinstance(checkpoint, dict) else [],
                "versions_seen": checkpoint.get("versions_seen", {}) if isinstance(checkpoint, dict) else {},
            }

        except Exception as e:
            print(f"❌ Error loading checkpoint: {e}")
            return None

    def get_messages(self, thread_id: str) -> list[dict[str, Any]]:
        """Get message history from checkpoint.

        Args:
            thread_id: Thread identifier

        Returns:
            List of messages
        """
        checkpoint = self.get_checkpoint(thread_id)

        if not checkpoint:
            return []

        # Extract messages from channel_values
        channel_values = checkpoint.get("channel_values", {})
        messages = channel_values.get("messages", [])

        # Convert to serializable format
        message_list = []
        for msg in messages:
            if hasattr(msg, 'model_dump'):
                message_list.append(msg.model_dump())
            elif hasattr(msg, 'dict'):
                message_list.append(msg.dict())
            elif isinstance(msg, dict):
                message_list.append(msg)
            else:
                message_list.append({"raw": str(msg)})

        return message_list

    def get_variables(self, thread_id: str) -> dict[str, Any]:
        """Get all state variables from checkpoint.

        Args:
            thread_id: Thread identifier

        Returns:
            Dictionary of state variables
        """
        checkpoint = self.get_checkpoint(thread_id)

        if not checkpoint:
            return {}

        channel_values = checkpoint.get("channel_values", {})

        # Extract key state variables
        variables = {}

        # Standard state variables
        for key in ["messages", "intent", "approval_decision", "tool_calls", "errors"]:
            if key in channel_values:
                value = channel_values[key]
                # Serialize complex objects
                if hasattr(value, 'model_dump'):
                    variables[key] = value.model_dump()
                elif hasattr(value, 'dict'):
                    variables[key] = value.dict()
                elif isinstance(value, (list, dict, str, int, float, bool, type(None))):
                    variables[key] = value
                else:
                    variables[key] = str(value)

        # Add all other channel values
        for key, value in channel_values.items():
            if key not in variables:
                if hasattr(value, 'model_dump'):
                    variables[key] = value.model_dump()
                elif hasattr(value, 'dict'):
                    variables[key] = value.dict()
                elif isinstance(value, (list, dict, str, int, float, bool, type(None))):
                    variables[key] = value
                else:
                    variables[key] = str(value)

        return variables

    def get_tool_calls(self, thread_id: str) -> list[dict[str, Any]]:
        """Get tool call history from messages.

        Args:
            thread_id: Thread identifier

        Returns:
            List of tool calls with results
        """
        messages = self.get_messages(thread_id)

        tool_calls = []

        for i, msg in enumerate(messages):
            msg_type = msg.get("type") or msg.get("__class__", "")

            # Check for tool calls in AIMessage
            if "tool_calls" in msg:
                for tool_call in msg["tool_calls"]:
                    tool_calls.append({
                        "message_index": i,
                        "tool_name": tool_call.get("name"),
                        "tool_args": tool_call.get("args"),
                        "tool_id": tool_call.get("id"),
                        "timestamp": msg.get("timestamp"),
                    })

            # Check for tool results in ToolMessage
            if msg_type in ["ToolMessage", "tool"]:
                tool_calls.append({
                    "message_index": i,
                    "tool_name": msg.get("name"),
                    "tool_result": msg.get("content"),
                    "tool_id": msg.get("tool_call_id"),
                    "status": msg.get("status"),
                    "timestamp": msg.get("timestamp"),
                })

        return tool_calls

    def print_checkpoint(self, thread_id: str, checkpoint_ns: str = "") -> None:
        """Print checkpoint in readable format.

        Args:
            thread_id: Thread identifier
            checkpoint_ns: Optional checkpoint namespace
        """
        print(f"\n{'='*70}")
        safe_print(f"🔍 CHECKPOINT INSPECTION: {thread_id}")
        if checkpoint_ns:
            safe_print(f"   Namespace: {checkpoint_ns}")
        print(f"{'='*70}\n")

        checkpoint = self.get_checkpoint(thread_id, checkpoint_ns)

        if not checkpoint:
            print("❌ No checkpoint found for this thread\n")
            return

        # Checkpoint ID
        safe_print(f"📋 Checkpoint ID: {checkpoint['checkpoint_id']}")
        print()

        # Metadata
        if checkpoint.get('metadata'):
            safe_print("📝 Metadata:")
            for key, value in checkpoint['metadata'].items():
                safe_print(f"   {key}: {value}")
            print()

        # Channel values summary
        channel_values = checkpoint.get('channel_values', {})
        safe_print(f"📊 Channel Values: {len(channel_values)} keys")
        for key in sorted(channel_values.keys()):
            value = channel_values[key]
            if isinstance(value, list):
                safe_print(f"   {key}: [{len(value)} items]")
            elif isinstance(value, dict):
                safe_print(f"   {key}: {{{len(value)} keys}}")
            else:
                safe_print(f"   {key}: {type(value).__name__}")
        print()

        # Pending sends
        if checkpoint.get('pending_sends'):
            safe_print(f"📤 Pending Sends: {len(checkpoint['pending_sends'])}")
            print()

        print(f"{'='*70}\n")

    def print_messages(self, thread_id: str) -> None:
        """Print message history in readable format.

        Args:
            thread_id: Thread identifier
        """
        print(f"\n{'='*70}")
        safe_print(f"💬 MESSAGE HISTORY: {thread_id}")
        print(f"{'='*70}\n")

        messages = self.get_messages(thread_id)

        if not messages:
            print("❌ No messages found for this thread\n")
            return

        for i, msg in enumerate(messages, 1):
            msg_type = msg.get("type") or msg.get("__class__", "unknown")
            content = msg.get("content", "")

            # Message header
            safe_print(f"[{i}] {msg_type}")

            # Message content (truncated for readability)
            if isinstance(content, str):
                if len(content) > 200:
                    safe_print(f"   {content[:200]}...")
                else:
                    safe_print(f"   {content}")
            elif isinstance(content, list):
                safe_print(f"   [List with {len(content)} items]")
            elif isinstance(content, dict):
                safe_print(f"   {json.dumps(content, indent=4)[:200]}...")
            else:
                safe_print(f"   {str(content)[:200]}")

            # Additional info
            if "name" in msg:
                safe_print(f"   Name: {msg['name']}")

            if "tool_calls" in msg and msg["tool_calls"]:
                safe_print(f"   Tool Calls: {len(msg['tool_calls'])}")

            print()

        print(f"{'='*70}\n")
        safe_print(f"Total Messages: {len(messages)}")
        print()

    def print_variables(self, thread_id: str) -> None:
        """Print state variables in readable format.

        Args:
            thread_id: Thread identifier
        """
        print(f"\n{'='*70}")
        safe_print(f"📦 STATE VARIABLES: {thread_id}")
        print(f"{'='*70}\n")

        variables = self.get_variables(thread_id)

        if not variables:
            print("❌ No state variables found for this thread\n")
            return

        for key, value in sorted(variables.items()):
            safe_print(f"🔹 {key}:")

            if isinstance(value, list):
                if len(value) == 0:
                    print("   []")
                elif len(value) > 3:
                    print(f"   [List with {len(value)} items]")
                    print(f"   First 3: {json.dumps(value[:3], indent=4)}")
                else:
                    print(f"   {json.dumps(value, indent=4)}")

            elif isinstance(value, dict):
                if len(value) == 0:
                    print("   {}")
                elif len(value) > 5:
                    print(f"   {{Dict with {len(value)} keys}}")
                    first_5 = dict(list(value.items())[:5])
                    print(f"   First 5: {json.dumps(first_5, indent=4)}")
                else:
                    print(f"   {json.dumps(value, indent=4)}")

            else:
                print(f"   {value}")

            print()

        print(f"{'='*70}\n")

    def print_tool_calls(self, thread_id: str) -> None:
        """Print tool call history in readable format.

        Args:
            thread_id: Thread identifier
        """
        print(f"\n{'='*70}")
        safe_print(f"🔧 TOOL CALL HISTORY: {thread_id}")
        print(f"{'='*70}\n")

        tool_calls = self.get_tool_calls(thread_id)

        if not tool_calls:
            print("❌ No tool calls found for this thread\n")
            return

        for i, call in enumerate(tool_calls, 1):
            safe_print(f"[{i}] {call.get('tool_name', 'unknown')}")

            if "tool_args" in call:
                print(f"   Args: {json.dumps(call['tool_args'], indent=4)}")

            if "tool_result" in call:
                result = call['tool_result']
                if isinstance(result, str) and len(result) > 200:
                    print(f"   Result: {result[:200]}...")
                else:
                    print(f"   Result: {result}")

            if "status" in call:
                safe_print(f"   Status: {call['status']}")

            print()

        print(f"{'='*70}\n")
        safe_print(f"Total Tool Calls: {len(tool_calls)}")
        print()

    def print_full_state(self, thread_id: str) -> None:
        """Print complete state inspection.

        Args:
            thread_id: Thread identifier
        """
        print(f"\n{'#'*70}")
        safe_print(f"🔍 FULL STATE INSPECTION: {thread_id}")
        print(f"{'#'*70}\n")

        # Checkpoint
        self.print_checkpoint(thread_id)

        # Messages
        self.print_messages(thread_id)

        # Variables
        self.print_variables(thread_id)

        # Tool calls
        self.print_tool_calls(thread_id)

        print(f"{'#'*70}\n")

    def export_state(self, thread_id: str, output_path: Path) -> None:
        """Export complete state to JSON file.

        Args:
            thread_id: Thread identifier
            output_path: Path to output JSON file
        """
        checkpoint = self.get_checkpoint(thread_id)
        messages = self.get_messages(thread_id)
        variables = self.get_variables(thread_id)
        tool_calls = self.get_tool_calls(thread_id)

        state_export = {
            "thread_id": thread_id,
            "exported_at": datetime.now().isoformat(),
            "checkpoint": checkpoint,
            "messages": messages,
            "variables": variables,
            "tool_calls": tool_calls,
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(state_export, f, indent=2, ensure_ascii=False)

        safe_print(f"\n✅ State exported to: {output_path}\n")


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

    inspector = StateInspector()

    if len(sys.argv) < 2:
        print(__doc__)
        print("\nExamples:")
        print("  # Full state inspection")
        print("  uv run python -m autifyme_agents.cli.inspect --full --thread whatsapp:123456")
        print()
        print("  # Messages only")
        print("  uv run python -m autifyme_agents.cli.inspect --messages --thread console:test_user")
        print()
        print("  # Export to JSON")
        print("  uv run python -m autifyme_agents.cli.inspect --full --thread whatsapp:123456 --export state.json")
        print()
        sys.exit(1)

    # Parse arguments
    thread_id = None
    export_path = None
    show_checkpoint = False
    show_messages = False
    show_variables = False
    show_tools = False
    show_full = False
    list_threads_flag = False

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]

        if arg in ["--help", "-h"]:
            print(__doc__)
            return

        elif arg == "--list-threads":
            list_threads_flag = True
            i += 1

        elif arg == "--thread":
            if i + 1 < len(sys.argv):
                thread_id = sys.argv[i + 1]
                i += 2
            else:
                print("Error: --thread requires a thread ID")
                sys.exit(1)

        elif arg == "--export":
            if i + 1 < len(sys.argv):
                export_path = Path(sys.argv[i + 1])
                i += 2
            else:
                print("Error: --export requires a file path")
                sys.exit(1)

        elif arg == "--checkpoint":
            show_checkpoint = True
            i += 1

        elif arg == "--messages":
            show_messages = True
            i += 1

        elif arg == "--variables":
            show_variables = True
            i += 1

        elif arg == "--tools":
            show_tools = True
            i += 1

        elif arg == "--full":
            show_full = True
            i += 1

        else:
            print(f"Unknown argument: {arg}")
            sys.exit(1)

    # Execute commands
    if list_threads_flag:
        inspector.list_threads()
        return

    if not thread_id:
        print("Error: --thread is required (except for --list-threads)")
        sys.exit(1)

    # Show requested information
    if show_full:
        inspector.print_full_state(thread_id)
    else:
        if show_checkpoint:
            inspector.print_checkpoint(thread_id)
        if show_messages:
            inspector.print_messages(thread_id)
        if show_variables:
            inspector.print_variables(thread_id)
        if show_tools:
            inspector.print_tool_calls(thread_id)

        if not (show_checkpoint or show_messages or show_variables or show_tools):
            # Default: show everything
            inspector.print_full_state(thread_id)

    # Export if requested
    if export_path:
        inspector.export_state(thread_id, export_path)


if __name__ == "__main__":
    main()
