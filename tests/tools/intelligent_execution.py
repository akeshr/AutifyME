"""Intelligent execution where AI acts as test user.

Instead of pattern matching, AI (OpenAI) reads PM messages and responds intelligently,
detecting issues and debugging in real-time.
"""
import asyncio
import json
import sys
import time
import uuid
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langsmith import Client
from openai import OpenAI

# Ensure .env is loaded
load_dotenv()

# Windows-specific fix: psycopg async requires SelectorEventLoop
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.integrations.storage.postgres_saver_factory import get_checkpointer
from autifyme_agents.integrations.storage.storage_factory import get_storage
from autifyme_agents.workflows.channels.protocol import MessagingChannel
from autifyme_agents.workflows.orchestration.runner_v2 import WorkflowRunner

from .models import ExecutionResult


class _IntelligentConsoleChannel(MessagingChannel):
    """Console channel that captures ALL PM messages for AI to analyze."""

    def __init__(self):
        self.messages_sent = []
        self.pending_interrupt: dict[str, Any] | None = None

    def format_thread_id(self, sender: str) -> str:
        return f"console:{sender}"

    def send_text(self, recipient: str, message: str, *, metadata: dict | None = None) -> dict:
        """Capture PM text messages."""
        self.messages_sent.append({
            "type": "text",
            "message": message,
            "timestamp": time.time()
        })
        return {"status": "sent"}

    def send_approval_request(self, recipient: str, interrupt_value) -> dict:
        """Capture HITL approval requests - don't auto-respond, wait for AI decision."""
        self.pending_interrupt = {
            "type": "approval_request",
            "value": interrupt_value,
            "timestamp": time.time()
        }
        self.messages_sent.append(self.pending_interrupt.copy())
        # Return pending status - AI will decide
        return {"status": "pending"}

    def send_completion(self, recipient: str, result) -> dict:
        """Capture completion."""
        self.messages_sent.append({
            "type": "completion",
            "result": result,
            "timestamp": time.time()
        })
        return {"status": "sent"}

    def send_error(self, recipient: str, error_type: str, custom_message: str | None = None) -> dict:
        """Capture errors."""
        self.messages_sent.append({
            "type": "error",
            "error_type": error_type,
            "message": custom_message,
            "timestamp": time.time()
        })
        return {"status": "sent"}

    def download_media(self, media_id: str) -> Path:
        """Return resolved absolute path for media file."""
        path = Path(media_id)
        if not path.is_absolute():
            path = path.resolve()
        return path


def _ask_ai_how_to_respond(
    pm_messages: list[dict],
    scenario_context: str,
    conversation_history: list[dict],
) -> dict:
    """Ask AI (OpenAI gpt-4.1-nano) how to respond to PM's messages.

    Returns:
        {
            "action": "respond" | "approve" | "reject" | "debug",
            "response_text": str,  # What to send to PM (if action=respond/approve/reject)
            "reasoning": str,  # Why AI chose this action
            "debug_reason": str | None,  # Why we need to debug (if action=debug)
        }
    """
    client = OpenAI()

    # Build context for AI
    messages_text = "\n\n".join([
        f"[{msg['type'].upper()}] {msg.get('message', msg.get('error_type', str(msg)))}"
        for msg in pm_messages
    ])

    history_text = "\n".join([
        f"User: {turn['user']}\nPM: {turn['pm_response']}"
        for turn in conversation_history
    ]) if conversation_history else "No previous conversation"

    prompt = f"""You are a BUSINESS USER testing the AutifyME PM agent. You are NOT the PM - you are the customer/user.

**Scenario:** {scenario_context}

**Conversation History:**
{history_text}

**PM's Latest Messages:**
{messages_text}

**WHO YOU ARE:**
- You are a BUSINESS USER who wants to onboard products or create campaigns
- You are NOT the PM agent - the PM works FOR you
- The PM asks YOU questions, YOU answer them
- The PM does the work, YOU provide requirements and approve results

**Your Task:**
Read PM's messages and decide how to respond. You have 4 options:

1. **respond**: PM asks a question → YOU answer as a business user would
2. **approve**: PM presents work for approval → YOU approve it
3. **reject**: PM's work has clear errors → YOU reject it
4. **debug**: PM is broken/stuck → trigger debugging

**Response Guidelines:**
- Keep responses SHORT (1-2 sentences as a user would)
- Answer PM's questions directly - don't ask the PM to do things
- When PM asks for details, provide them (e.g., "It's a 500ml PET jar")
- When PM presents results, approve/reject them
- NEVER say things like "Please share the details" - YOU are the one sharing details

**Decision Criteria:**

- If PM asks "what type of container?" → respond: "PET jars" (not "please share the type")
- If PM presents product for approval → approve: "approved"
- If PM is repeating itself or stuck → debug
- If PM says "complete" but didn't call save_product_family → debug

Return JSON:
{{
    "action": "respond" | "approve" | "reject" | "debug",
    "response_text": "YOUR response AS A USER",
    "reasoning": "why you chose this",
    "debug_reason": "issue detected (if debug)"
}}

Remember: YOU are the user, PM serves YOU. Answer PM's questions, don't ask PM to provide things.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-nano",  # Fast and cheap for test orchestration
            max_tokens=500,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are a test orchestration AI. Return valid JSON only."},
                {"role": "user", "content": prompt}
            ]
        )

        # Parse AI response
        response_text = response.choices[0].message.content
        decision = json.loads(response_text)

    except json.JSONDecodeError as e:
        # Fallback - if AI didn't return valid JSON
        decision = {
            "action": "debug",
            "response_text": "",
            "reasoning": "Failed to parse AI response",
            "debug_reason": f"AI returned invalid JSON: {response_text if 'response_text' in locals() else str(e)}"
        }
    except Exception as e:
        # Any other error
        decision = {
            "action": "debug",
            "response_text": "",
            "reasoning": "AI call failed",
            "debug_reason": f"Error calling OpenAI: {str(e)}"
        }

    return decision


async def intelligent_execute_scenario(
    scenario_id: str,
    media_path: str | None = None,
    max_turns: int = 10,
) -> ExecutionResult:
    """Execute test scenario with AI as intelligent test user.

    AI (OpenAI gpt-4.1-nano) reads PM's messages, responds naturally, and detects issues in real-time.

    Args:
        scenario_id: Scenario identifier or custom prompt text
        media_path: Optional path to media file
        max_turns: Maximum conversation turns before stopping

    Returns:
        ExecutionResult with debugging info if issues detected
    """
    start_time = time.time()

    # Setup components
    storage: StorageInterface = get_storage()
    channel = _IntelligentConsoleChannel()
    # Don't pass checkpointer - runner will create AsyncPostgresSaver lazily for async execution

    # Create workflow handler
    from autifyme_agents.workflows.handlers.cataloging_handler import CatalogingWorkflowHandler
    workflow_handler = CatalogingWorkflowHandler(channel=channel)

    runner = WorkflowRunner(
        channel=channel,
        storage=storage,
        workflow_handler=workflow_handler,
        checkpointer=None,  # Async runner will create AsyncPostgresSaver
    )

    # Generate unique sender
    unique_sender = f"test_{uuid.uuid4().hex[:8]}"
    thread_id = channel.format_thread_id(unique_sender)

    errors = []
    success = False
    trace_id = None
    trace_url = None
    conversation_history = []

    def safe_print(text):
        """Print safely handling unicode."""
        try:
            print(text)
        except UnicodeEncodeError:
            print(text.encode('ascii', 'replace').decode('ascii'))

    try:
        safe_print(f"\n{'='*80}")
        safe_print("INTELLIGENT TESTING MODE - AI as Test User (OpenAI gpt-4.1-nano)")
        safe_print(f"{'='*80}")
        safe_print(f"Scenario: {scenario_id}")
        safe_print(f"Thread: {thread_id}")
        safe_print(f"{'='*80}\n")

        # Send initial message
        safe_print(f"[USER -> PM] {scenario_id}")
        await runner.handle_message(
            sender=unique_sender,
            text=scenario_id,
            media_id=media_path if media_path else None,
        )

        conversation_history.append({
            "user": scenario_id,
            "pm_response": "pending..."
        })

        # INTELLIGENT CONVERSATION LOOP
        # AI reads PM messages and decides how to respond
        last_message_count = 0
        interrupt_occurred = False

        for turn in range(max_turns):
            time.sleep(1.0)  # Give PM time to respond

            # Check for new PM messages
            current_message_count = len(channel.messages_sent)
            if current_message_count == last_message_count:
                # No new messages - check if workflow completed
                has_completion = any(m.get("type") == "completion" for m in channel.messages_sent)
                if has_completion:
                    safe_print("\n[WORKFLOW] Completed successfully")
                    success = True
                    break
                else:
                    # No messages and no completion - might be stuck
                    time.sleep(1.5)
                    if len(channel.messages_sent) == current_message_count:
                        safe_print("\n[WORKFLOW] No new messages - analyzing...")
                        # Ask AI if this is normal or if we should debug
                        decision = _ask_ai_how_to_respond(
                            pm_messages=[{"type": "silence", "message": "PM stopped responding"}],
                            scenario_context=scenario_id,
                            conversation_history=conversation_history,
                        )
                        if decision["action"] == "debug":
                            safe_print(f"\n[DEBUG TRIGGERED] {decision['debug_reason']}")
                            errors.append(f"Debug triggered: {decision['debug_reason']}")
                            break
                        else:
                            # Maybe workflow is just done
                            break

            # Get new messages from PM
            new_messages = channel.messages_sent[last_message_count:]
            last_message_count = current_message_count

            # Display PM's messages
            for msg in new_messages:
                if msg.get("type") == "text":
                    safe_print(f"\n[PM -> USER] {msg['message'][:200]}...")
                elif msg.get("type") == "approval_request":
                    safe_print(f"\n[PM -> USER] [HITL APPROVAL REQUEST]")
                    interrupt_occurred = True
                elif msg.get("type") == "completion":
                    safe_print(f"\n[PM -> USER] [COMPLETION]")
                elif msg.get("type") == "error":
                    safe_print(f"\n[PM -> USER] [ERROR: {msg['error_type']}]")

            # Ask AI how to respond
            safe_print(f"\n[AI] Analyzing PM's messages...")
            decision = _ask_ai_how_to_respond(
                pm_messages=new_messages,
                scenario_context=scenario_id,
                conversation_history=conversation_history,
            )

            safe_print(f"[AI] Decision: {decision['action']}")
            safe_print(f"[AI] Reasoning: {decision['reasoning']}")

            # Act on AI's decision
            if decision["action"] == "debug":
                safe_print(f"\n{'='*80}")
                safe_print("DEBUG MODE ACTIVATED")
                safe_print(f"{'='*80}")
                safe_print(f"Reason: {decision['debug_reason']}")
                safe_print(f"\nStopping test for manual debugging...")
                errors.append(f"Debug triggered: {decision['debug_reason']}")
                break

            elif decision["action"] in ["respond", "approve", "reject"]:
                response_text = decision["response_text"]
                safe_print(f"\n[USER -> PM] {response_text}")

                # Send response to PM
                await runner.handle_message(
                    sender=unique_sender,
                    text=response_text,
                    media_id=None,
                )

                # Update conversation history
                pm_summary = "\n".join([
                    msg.get("message", msg.get("error_type", ""))[:100]
                    for msg in new_messages
                    if msg.get("type") in ["text", "error"]
                ])
                conversation_history.append({
                    "user": response_text,
                    "pm_response": pm_summary
                })

        # Get trace from LangSmith
        time.sleep(3.0)
        try:
            client = Client()
            runs = list(client.list_runs(
                project_name="autifyme-dev",
                is_root=True,
                limit=20
            ))

            for run in runs:
                if run.extra:
                    metadata = run.extra.get("metadata", {})
                    langsmith_thread_id = metadata.get("langsmith.thread_id")
                    if langsmith_thread_id == thread_id:
                        # Safely extract trace info with None checks
                        trace_id = str(run.trace_id) if run.trace_id else None
                        session_id = run.session_id if hasattr(run, 'session_id') and run.session_id else None
                        if trace_id and session_id:
                            trace_url = f"https://smith.langchain.com/public/{session_id}/r/{trace_id}"
                        break

            if not trace_id:
                errors.append(f"Trace not found for thread {thread_id}")
        except Exception as e:
            errors.append(f"Failed to capture trace: {str(e)}")

        if not errors:
            success = True

    except Exception as e:
        errors.append(f"{type(e).__name__}: {str(e)}")

    execution_time = time.time() - start_time

    # Count products created
    products_created = len([m for m in channel.messages_sent if m.get("type") == "completion"])

    safe_print(f"\n{'='*80}")
    safe_print(f"Result: {'SUCCESS' if success else 'FAILED'}")
    safe_print(f"Time: {execution_time:.2f}s")
    safe_print(f"HITL: {'Yes' if interrupt_occurred else 'No'}")
    safe_print(f"Trace: {trace_url or 'Not available'}")
    if errors:
        safe_print(f"\nErrors/Debug:")
        for err in errors:
            safe_print(f"  - {err}")
    safe_print(f"{'='*80}\n")

    return ExecutionResult(
        success=success,
        thread_id=thread_id,
        trace_url=trace_url or "https://smith.langchain.com",
        trace_id=trace_id or "unknown",
        products_created=products_created,
        execution_time_seconds=round(execution_time, 2),
        interrupt_occurred=interrupt_occurred,
        approval_message=None,  # Not applicable in intelligent mode
        approval_type=None,
        is_batch_approval=False,
        errors=errors,
    )
