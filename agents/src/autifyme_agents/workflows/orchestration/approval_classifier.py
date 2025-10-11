"""LLM-powered approval intent classification using create_agent.

Replaces direct llm.with_structured_output() for architectural consistency.
"""

from __future__ import annotations

from langchain.agents import create_agent
from langchain.agents.middleware import AnthropicPromptCachingMiddleware
from langchain.chat_models import BaseChatModel

from autifyme_agents.core.llm_factory import get_llm
from autifyme_agents.schemas.approval import ApprovalRequest, ApprovalDecision
from autifyme_agents.core.logging_config import get_logger

logger = get_logger(__name__)


class ApprovalIntentClassifier:
    """Agent-based approval intent classification.

    Uses create_agent instead of direct LLM for:
    - Full LangSmith tracing
    - Middleware support (caching, etc.)
    - Architectural consistency
    """

    def __init__(
        self,
        llm: BaseChatModel | None = None,
        checkpointer: Any | None = None,
    ):
        """Initialize classifier agent.

        Args:
            llm: Optional LLM override (defaults to gpt-4o)
            checkpointer: Optional checkpointer for stateful classification
        """

        self.llm = llm or get_llm(model="gpt-4o", temperature=0.1)

        # ✅ Create agent with response_format for structured output
        self.agent = create_agent(
            model=self.llm,
            tools=[],  # Pure classification, no tools needed
            system_prompt=self._build_system_prompt(),
            response_format=ApprovalDecision,  # ✅ Structured output
            checkpointer=checkpointer,
            name="ApprovalIntentClassifier",
            middleware=self._build_middleware(),
        )

    def classify(
        self,
        user_message: str,
        approval_context: ApprovalRequest,
        thread_id: str,
        recent_history: list[dict[str, str]] | None = None,
    ) -> ApprovalDecision:
        """Classify user's approval message intent.

        Args:
            user_message: User's raw message
            approval_context: Pending approval details
            thread_id: Thread ID for checkpointing
            recent_history: Recent conversation for context

        Returns:
            Structured approval decision with intent and extracted data
        """

        # Build classification prompt with approval context
        classification_prompt = self._build_classification_prompt(
            user_message=user_message,
            approval=approval_context,
            history=recent_history or [],
        )

        messages = [{"role": "human", "content": classification_prompt}]

        # Invoke agent
        result = self.agent.invoke(
            {"messages": messages},
            config={
                "configurable": {"thread_id": f"approval_classifier:{thread_id}"},
                "tags": ["approval", "intent_classification"],
                "metadata": {
                    "approval_id": approval_context.id,
                    "action": approval_context.action,
                },
            },
        )

        # Extract structured decision
        decision: ApprovalDecision = result["response"]

        logger.info(
            "Approval intent classified",
            extra={
                "thread_id": thread_id,
                "approval_id": approval_context.id,
                "intent": decision.intent,
                "confidence": decision.confidence,
                "reasoning": decision.reasoning[:100],
            }
        )

        return decision

    def _build_system_prompt(self) -> str:
        """Build system prompt for classifier agent."""

        return """You are an approval intent classifier for a product cataloging system.

Given a pending action and user message, determine their intent:

INTENTS:
- approve: User wants to proceed as-is ("yes", "looks good", "go ahead")
- approve_with_edits: User wants to modify fields ("change price to $25")
- reject: User wants to cancel ("no", "never mind", "cancel")
- question: User needs clarification ("what category?", "show similar products")
- defer: User wants to postpone ("remind me later", "ask me tomorrow")
- park: User wants to handle something else first ("wait, catalog this other product")
- abandon: User wants to completely cancel and reset ("forget everything")

EXTRACTION RULES:
- For approve_with_edits: Extract field-level edits into edited_fields dict
- For question: Extract question_text and clarification_needed list
- For defer: Extract defer_until datetime if specified
- Provide confidence score (0.0-1.0) based on clarity
- Explain reasoning concisely

EXAMPLES:
- "looks good!" → approve (confidence: 0.95, reasoning: "clear approval phrase")
- "change the price to 25 dollars" → approve_with_edits (edited_fields: {"price": 25.0}, confidence: 0.9)
- "what's the category?" → question (question_text: "what's the category?", confidence: 0.95)
- "no thanks" → reject (confidence: 0.9, reasoning: "clear rejection")

Always provide:
1. intent (one of the above)
2. confidence (0.0-1.0)
3. reasoning (why you classified this way)
4. extracted details (edited_fields, question_text, etc. based on intent)
"""

    def _build_classification_prompt(
        self,
        user_message: str,
        approval: ApprovalRequest,
        history: list[dict[str, str]],
    ) -> str:
        """Build classification prompt with approval context."""

        editable_fields_str = ", ".join(approval.editable_fields)
        preview_str = self._format_preview(approval.preview_data)

        history_str = ""
        if history:
            history_str = "\n\nRECENT CONVERSATION:\n"
            for msg in history[-5:]:  # Last 5 messages
                role = msg.get("role", "user")
                content = msg.get("content", "")
                history_str += f"{role}: {content}\n"

        prompt = f"""PENDING ACTION:
{approval.action_description}

PRODUCT PREVIEW:
{preview_str}

EDITABLE FIELDS: {editable_fields_str}
{history_str}

USER MESSAGE:
{user_message}

Classify the user's intent and extract relevant details.
"""

        return prompt

    def _format_preview(self, preview_data: dict) -> str:
        """Format preview data for display."""
        lines = []
        for key, value in preview_data.items():
            if value is not None:
                lines.append(f"{key}: {value}")
        return "\n".join(lines)

    def _build_middleware(self) -> list:
        """Build middleware stack for classifier."""

        return [
            # Prompt caching for approval context (repeated across classifications)
            AnthropicPromptCachingMiddleware(
                ttl="5m",
                min_messages_to_cache=1,
                unsupported_model_behavior="ignore",
            ),
        ]
