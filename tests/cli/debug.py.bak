"""Interactive workflow debugger with step-by-step execution.

This tool provides an interactive debugging experience for workflows, allowing
you to pause execution, inspect state, set breakpoints, and modify state on-the-fly.

Features:
- Step-by-step execution (step into/over/out)
- Breakpoints (pause at specific turns or events)
- State inspection at any point
- State modification (edit variables, inject messages)
- Execution control (continue/pause/restart/stop)
- Workflow replay from checkpoint

Usage:
    # Start interactive debugger with a scenario
    uv run python -m autifyme_agents.cli.debug --scenario "Catalog sneakers"

    # Debug a conversation scenario
    uv run python -m autifyme_agents.cli.debug --conversation greeting_to_cataloging

    # Replay from existing thread
    uv run python -m autifyme_agents.cli.debug --replay --thread whatsapp:123456

    # Set breakpoints
    uv run python -m autifyme_agents.cli.debug --scenario "Catalog sneakers" --break-on approval

Available Commands (during debugging):
    step / s        - Execute next step
    continue / c    - Continue until breakpoint
    inspect / i     - Inspect current state
    messages / m    - Show message history
    variables / v   - Show state variables
    tools / t       - Show tool calls
    breakpoint / b  - Set/list breakpoints
    modify / mod    - Modify state variable
    inject / inj    - Inject message
    restart / r     - Restart from beginning
    quit / q        - Stop debugging
"""

import sys
import json
import cmd
from pathlib import Path
from typing import Any
from dotenv import load_dotenv

from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.integrations.storage.storage_factory import get_storage
from autifyme_agents.integrations.storage.postgres_saver_factory import get_checkpointer
from autifyme_agents.workflows.orchestration.runner_v2 import WorkflowRunner
from autifyme_agents.workflows.channels.protocol import MessagingChannel
from autifyme_agents.schemas.models import Product
from autifyme_agents.cli.inspect import StateInspector


def safe_print(text: str) -> None:
    """Print text safely, handling console encoding issues on Windows."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode('ascii', errors='replace').decode('ascii'))


class DebugChannel(MessagingChannel):
    """Messaging channel with debugging hooks."""

    def __init__(self, debugger: 'WorkflowDebugger'):
        """Initialize debug channel.

        Args:
            debugger: WorkflowDebugger instance
        """
        self.debugger = debugger
        self.messages_sent: list[dict[str, Any]] = []
        self.approvals_requested: list[dict[str, Any]] = []

    def format_thread_id(self, sender: str) -> str:
        return f"debug:{sender}"

    def send_text(self, recipient: str, message: str, *, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        """Send text message with debug hooks."""
        print(f"\n{'='*60}")
        safe_print(f"📤 PM → {recipient}:")
        print(f"{'='*60}")
        print(message[:300] + ("..." if len(message) > 300 else ""))
        print(f"{'='*60}\n")

        self.messages_sent.append({"type": "text", "message": message})

        # Debug breakpoint
        if self.debugger.should_break("message_sent"):
            self.debugger.pause(f"Breakpoint: Message sent to {recipient}")

        return {"status": "sent"}

    def send_approval_request(self, recipient: str, draft: Product) -> dict[str, Any]:
        """Send approval request with debug hooks."""
        print(f"\n{'='*60}")
        safe_print(f"⏸️  APPROVAL REQUEST → {recipient}:")
        print(f"{'='*60}")

        draft_dict = draft.model_dump() if hasattr(draft, 'model_dump') else draft

        def json_encoder(obj):
            if hasattr(obj, '__str__'):
                return str(obj)
            raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

        print(json.dumps(draft_dict, indent=2, ensure_ascii=False, default=json_encoder))
        print(f"{'='*60}\n")

        self.approvals_requested.append({"draft": draft_dict})

        # Debug breakpoint
        if self.debugger.should_break("approval_request"):
            self.debugger.pause("Breakpoint: Approval requested")

        # Interactive approval
        while True:
            print("\nOptions: approve / reject / inspect / edit <field> <value>")
            decision = input("Your decision: ").strip().lower()

            if decision in ["approve", "yes", "y"]:
                print("\n[APPROVED]\n")
                return {"status": "approved", "draft": draft}

            elif decision in ["reject", "no", "n"]:
                print("\n[REJECTED]\n")
                return {"status": "rejected"}

            elif decision == "inspect":
                self.debugger.inspector.print_variables(self.debugger.thread_id)

            elif decision.startswith("edit"):
                parts = decision.split(maxsplit=2)
                if len(parts) >= 3:
                    field = parts[1]
                    value_str = parts[2]
                    if hasattr(draft, field):
                        try:
                            field_value = getattr(draft, field)
                            typed_value: int | float | str
                            if isinstance(field_value, float):
                                typed_value = float(value_str)
                            elif isinstance(field_value, int):
                                typed_value = int(value_str)
                            else:
                                typed_value = value_str
                            setattr(draft, field, typed_value)
                            safe_print(f"\n✏️  Edited {field}: {typed_value}")
                            print("[APPROVED WITH EDITS]\n")
                            return {"status": "approved", "draft": draft}
                        except ValueError:
                            print(f"Error: Invalid value type for {field}")
                    else:
                        print(f"Error: Field '{field}' not found")
                else:
                    print("Usage: edit <field> <value>")

            else:
                print("Invalid option. Try again.")

    def send_completion(self, recipient: str, result: dict[str, Any] | Any) -> dict[str, Any]:  # type: ignore[override]
        """Send completion with debug hooks."""
        print(f"\n{'='*60}")
        safe_print(f"✅ COMPLETION → {recipient}:")
        print(f"{'='*60}")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print(f"{'='*60}\n")

        self.messages_sent.append({"type": "completion", "result": result})

        # Debug breakpoint
        if self.debugger.should_break("completion"):
            self.debugger.pause("Breakpoint: Workflow completed")

        return {"status": "sent"}

    def send_error(self, recipient: str, error_type: str, custom_message: str | None = None) -> dict:
        """Send error with debug hooks."""
        print(f"\n{'='*60}")
        safe_print(f"❌ ERROR → {recipient}:")
        print(f"{'='*60}")
        print(f"Error Type: {error_type}")
        if custom_message:
            print(f"Message: {custom_message}")
        print(f"{'='*60}\n")

        self.messages_sent.append({"type": "error", "error_type": error_type})

        # Debug breakpoint
        if self.debugger.should_break("error"):
            self.debugger.pause("Breakpoint: Error occurred")

        return {"status": "sent"}

    def download_media(self, media_id: str) -> Path:
        """Download media (for local testing, media_id is already a path)."""
        return Path(media_id)


class WorkflowDebugger(cmd.Cmd):
    """Interactive debugger for workflows."""

    intro = """
╔════════════════════════════════════════════════════════════════╗
║                  AutifyME Workflow Debugger                    ║
║                                                                ║
║  Commands:                                                     ║
║    step (s)       - Execute next step                         ║
║    continue (c)   - Continue until breakpoint                 ║
║    inspect (i)    - Inspect current state                     ║
║    messages (m)   - Show message history                      ║
║    variables (v)  - Show state variables                      ║
║    tools (t)      - Show tool calls                           ║
║    breakpoint (b) - Set/list breakpoints                      ║
║    restart (r)    - Restart workflow                          ║
║    help (?)       - Show help                                 ║
║    quit (q)       - Exit debugger                             ║
╚════════════════════════════════════════════════════════════════╝
"""
    prompt = "(debug) "

    def __init__(self, scenario: str | None = None, thread_id: str | None = None):
        """Initialize debugger.

        Args:
            scenario: Scenario to debug
            thread_id: Thread ID for replay mode
        """
        super().__init__()
        self.scenario = scenario
        self.thread_id = thread_id or f"debug_session_{id(self)}"
        self.breakpoints: set[str] = set()
        self.paused = False
        self.step_mode = False
        self.inspector = StateInspector()

        # Workflow components
        self.storage: StorageInterface = get_storage()
        self.checkpointer = get_checkpointer()
        self.channel = DebugChannel(self)
        self.runner = WorkflowRunner(
            channel=self.channel,
            storage=self.storage,
            checkpointer=self.checkpointer,
        )

    def should_break(self, event_type: str) -> bool:
        """Check if should break at this event.

        Args:
            event_type: Type of event (message_sent, approval_request, etc.)

        Returns:
            True if should break
        """
        return event_type in self.breakpoints or self.step_mode

    def pause(self, reason: str) -> None:
        """Pause execution and enter interactive mode.

        Args:
            reason: Reason for pausing
        """
        print(f"\n⏸️  PAUSED: {reason}\n")
        self.paused = True
        self.cmdloop()

    # Command implementations

    def do_step(self, arg: str) -> bool:  # type: ignore[override]
        """Execute next step."""
        self.step_mode = True
        self.paused = False
        safe_print("▶️  Stepping...")
        return True  # Exit cmdloop

    def do_s(self, arg: str) -> bool:  # type: ignore[override]
        """Shorthand for step."""
        return self.do_step(arg)

    def do_continue(self, arg: str) -> bool:  # type: ignore[override]
        """Continue execution until next breakpoint."""
        self.step_mode = False
        self.paused = False
        safe_print("▶️  Continuing...")
        return True  # Exit cmdloop

    def do_c(self, arg: str) -> bool:  # type: ignore[override]
        """Shorthand for continue."""
        return self.do_continue(arg)

    def do_inspect(self, arg: str) -> None:
        """Inspect current state."""
        self.inspector.print_full_state(self.thread_id)

    def do_i(self, arg: str) -> None:
        """Shorthand for inspect."""
        return self.do_inspect(arg)

    def do_messages(self, arg: str) -> None:
        """Show message history."""
        self.inspector.print_messages(self.thread_id)

    def do_m(self, arg: str) -> None:
        """Shorthand for messages."""
        return self.do_messages(arg)

    def do_variables(self, arg: str) -> None:
        """Show state variables."""
        self.inspector.print_variables(self.thread_id)

    def do_v(self, arg: str) -> None:
        """Shorthand for variables."""
        return self.do_variables(arg)

    def do_tools(self, arg: str) -> None:
        """Show tool call history."""
        self.inspector.print_tool_calls(self.thread_id)

    def do_t(self, arg: str) -> None:
        """Shorthand for tools."""
        return self.do_tools(arg)

    def do_breakpoint(self, arg: str) -> None:
        """Set or list breakpoints.

        Usage:
            breakpoint                - List all breakpoints
            breakpoint add <event>    - Add breakpoint
            breakpoint remove <event> - Remove breakpoint
            breakpoint clear          - Clear all breakpoints

        Events: message_sent, approval_request, completion, error
        """
        args = arg.split()

        if not args:
            # List breakpoints
            if self.breakpoints:
                safe_print(f"\n🔴 Active Breakpoints ({len(self.breakpoints)}):")
                for bp in sorted(self.breakpoints):
                    safe_print(f"   • {bp}")
                print()
            else:
                print("\n✅ No active breakpoints\n")

        elif args[0] == "add" and len(args) > 1:
            event = args[1]
            self.breakpoints.add(event)
            safe_print(f"\n✅ Breakpoint added: {event}\n")

        elif args[0] == "remove" and len(args) > 1:
            event = args[1]
            if event in self.breakpoints:
                self.breakpoints.remove(event)
                safe_print(f"\n✅ Breakpoint removed: {event}\n")
            else:
                print(f"\n❌ Breakpoint not found: {event}\n")

        elif args[0] == "clear":
            self.breakpoints.clear()
            print("\n✅ All breakpoints cleared\n")

        else:
            print("\nUsage: breakpoint [add|remove|clear] <event>\n")

    def do_b(self, arg: str) -> None:
        """Shorthand for breakpoint."""
        return self.do_breakpoint(arg)

    def do_restart(self, arg: str) -> None:
        """Restart workflow from beginning."""
        safe_print("\n🔄 Restarting workflow...\n")
        self.thread_id = f"debug_session_{id(self)}_{len(self.channel.messages_sent)}"
        self.channel = DebugChannel(self)
        self.runner = WorkflowRunner(
            channel=self.channel,
            storage=self.storage,
            checkpointer=self.checkpointer,
        )
        safe_print("✅ Workflow restarted with new thread\n")

    def do_r(self, arg: str) -> None:
        """Shorthand for restart."""
        return self.do_restart(arg)

    def do_quit(self, arg: str) -> bool:  # type: ignore[override]
        """Exit debugger."""
        safe_print("\n👋 Exiting debugger...\n")
        return True

    def do_q(self, arg: str) -> bool:  # type: ignore[override]
        """Shorthand for quit."""
        return self.do_quit(arg)

    def do_EOF(self, arg: str) -> bool:  # type: ignore[override]
        """Handle Ctrl+D."""
        return self.do_quit(arg)

    def run(self) -> None:
        """Run the debugger session."""
        if not self.scenario:
            print("Error: No scenario provided")
            return

        print(f"\n{'#'*70}")
        safe_print(f"🐛 DEBUGGING SCENARIO: {self.scenario}")
        safe_print(f"🔖 Thread ID: {self.thread_id}")
        print(f"{'#'*70}\n")

        try:
            # Initial breakpoint
            self.pause("Starting debug session")

            # Execute scenario
            self.runner.handle_message(
                sender=self.thread_id,
                text=self.scenario,
                media_id=None,
            )

            print(f"\n{'#'*70}")
            safe_print("✅ DEBUGGING SESSION COMPLETE")
            print(f"{'#'*70}\n")

        except Exception as e:
            print(f"\n{'#'*70}")
            safe_print(f"❌ ERROR DURING DEBUGGING: {type(e).__name__}: {e}")
            print(f"{'#'*70}\n")
            raise


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

    if len(sys.argv) < 2:
        print(__doc__)
        print("\nExamples:")
        print('  # Debug a scenario')
        print('  uv run python -m autifyme_agents.cli.debug --scenario "Catalog sneakers"')
        print()
        print('  # Debug with breakpoints')
        print('  uv run python -m autifyme_agents.cli.debug --scenario "Catalog sneakers" --break-on approval_request')
        print()
        sys.exit(1)

    # Parse arguments
    scenario = None
    thread_id = None
    initial_breakpoints = []

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]

        if arg in ["--help", "-h"]:
            print(__doc__)
            return

        elif arg == "--scenario":
            if i + 1 < len(sys.argv):
                scenario = sys.argv[i + 1]
                i += 2
            else:
                print("Error: --scenario requires a message")
                sys.exit(1)

        elif arg == "--thread":
            if i + 1 < len(sys.argv):
                thread_id = sys.argv[i + 1]
                i += 2
            else:
                print("Error: --thread requires a thread ID")
                sys.exit(1)

        elif arg == "--break-on":
            if i + 1 < len(sys.argv):
                initial_breakpoints.append(sys.argv[i + 1])
                i += 2
            else:
                print("Error: --break-on requires an event type")
                sys.exit(1)

        else:
            print(f"Unknown argument: {arg}")
            sys.exit(1)

    if not scenario:
        print("Error: --scenario is required")
        sys.exit(1)

    # Create and run debugger
    debugger = WorkflowDebugger(scenario=scenario, thread_id=thread_id)

    # Set initial breakpoints
    for bp in initial_breakpoints:
        debugger.breakpoints.add(bp)

    debugger.run()


if __name__ == "__main__":
    main()
