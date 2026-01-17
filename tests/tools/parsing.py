"""Shared parsing utilities for trace analysis.

These functions handle LangChain serialization formats and are used by
trace_loader.py, trace_analysis.py, and evaluation/helpers.py.

Consolidates duplicate parsing logic into single source of truth.
"""

from typing import Any


def extract_content_from_parts(content: Any) -> str:
    """Extract text from content that may be string or list of parts.

    LLM outputs can be:
    - Direct string: "hello"
    - List of parts: [{"type": "text", "text": "hello"}, {"type": "image", ...}]
    - Empty list/string: returns ""

    Args:
        content: Raw content from LLM output

    Returns:
        Extracted text string
    """
    if not content:
        return ""

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict):
                text = part.get("text", "")
                if text:
                    parts.append(str(text))
            elif isinstance(part, str):
                parts.append(part)
        return "\n".join(parts)

    return str(content)


def parse_lc_messages(messages: list) -> list[dict]:
    """Parse LangChain message serialization format into clean dicts.

    LangChain serializes messages as: {lc: 1, type: "constructor", id: [...], kwargs: {...}}
    This function extracts the useful parts.

    Args:
        messages: Raw messages from run.inputs['messages']

    Returns:
        List of dicts with keys: type, content, tool_calls
    """
    # Handle nested list (common in LangSmith)
    if messages and isinstance(messages[0], list):
        messages = messages[0]

    parsed = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue

        # Extract message type from id field
        msg_id = msg.get("id", [])
        msg_type = "unknown"
        if isinstance(msg_id, list) and msg_id:
            # id is like ["langchain_core", "messages", "HumanMessage"]
            msg_type = msg_id[-1] if msg_id else "unknown"

        # Extract content and tool_calls from kwargs
        kwargs = msg.get("kwargs", {})
        content = kwargs.get("content", "")
        tool_calls = kwargs.get("tool_calls", [])

        # Handle multimodal content (list of parts)
        if isinstance(content, list):
            text_parts = []
            has_image = False
            for part in content:
                if isinstance(part, dict):
                    if part.get("type") == "text":
                        text_parts.append(part.get("text", ""))
                    elif part.get("type") == "image_url":
                        has_image = True
            content = " ".join(text_parts)
            if has_image:
                content = f"[IMAGE] {content}" if content else "[IMAGE]"

        parsed.append({
            "type": msg_type,
            "content": content,
            "tool_calls": tool_calls,
        })

    return parsed


def parse_lc_output(outputs: dict) -> dict:
    """Parse LangChain LLM output format.

    Args:
        outputs: Raw outputs from run.outputs

    Returns:
        Dict with keys: content, tool_calls, raw
    """
    result = {"content": "", "tool_calls": [], "raw": outputs}

    if not outputs:
        return result

    try:
        generations = outputs.get("generations", [[]])
        if generations and generations[0]:
            gen = generations[0][0] if isinstance(generations[0], list) else generations[0]
            if isinstance(gen, dict):
                # Try text first (completion models)
                text_val = gen.get("text", "")
                if text_val and isinstance(text_val, str) and text_val.strip():
                    result["content"] = text_val

                # Try message.kwargs (chat models with LangChain serialization)
                msg = gen.get("message", {})
                kwargs = msg.get("kwargs", {})

                if not result["content"]:
                    raw_content = kwargs.get("content", "")
                    result["content"] = extract_content_from_parts(raw_content)

                result["tool_calls"] = kwargs.get("tool_calls", [])
    except Exception:
        pass

    return result


def extract_user_input(root_run) -> str:
    """Extract user input preview from root run for display.

    Handles multiple message formats including multimodal content.

    Args:
        root_run: LangSmith root run object

    Returns:
        User input preview string
    """
    if not root_run.inputs or "messages" not in root_run.inputs:
        return "(no input found)"

    messages = root_run.inputs["messages"]
    if messages and isinstance(messages[0], list):
        messages = messages[0]

    for msg in messages:
        if not isinstance(msg, dict):
            continue

        # Check for human message - two formats:
        # 1. Simple format: {"type": "human", "content": ...}
        # 2. LangChain serialization: {"id": ["...", "HumanMessage"], "kwargs": {"content": ...}}
        is_human = False
        content = ""

        # Format 1: Simple format
        if msg.get("type") == "human":
            is_human = True
            content = msg.get("content", "")
            # Check for media attachment
            if "[Media attachment:" in content:
                return "[Image] (no text)"

        # Format 2: LangChain serialization
        msg_id = msg.get("id", [])
        if isinstance(msg_id, list) and "HumanMessage" in msg_id:
            is_human = True
            content = msg.get("kwargs", {}).get("content", "")

        if is_human:
            # Handle multimodal content (list of parts)
            if isinstance(content, list):
                has_image = any(
                    p.get("type") == "image_url"
                    for p in content
                    if isinstance(p, dict)
                )
                text_parts = [
                    p.get("text", "")
                    for p in content
                    if isinstance(p, dict) and p.get("type") == "text"
                ]
                text = " ".join(text_parts).strip()

                if has_image and text:
                    return f"[Image] {text[:80]}..."
                elif has_image:
                    return "[Image] (no text)"
                elif text:
                    return f"{text[:100]}..."
                else:
                    return "(empty)"
            else:
                # Plain text
                if content:
                    return f"{content[:100]}..." if len(content) > 100 else content
                return "(empty)"

    return "(no HumanMessage found)"


def extract_pm_output(root_run) -> str:
    """Extract PM output preview from root run for display.

    Args:
        root_run: LangSmith root run object

    Returns:
        PM output preview string
    """
    if not root_run.outputs:
        return "(no output)"

    # Try structured_response first (AutifyME pattern)
    sr = root_run.outputs.get("structured_response", {})
    if isinstance(sr, dict) and "message" in sr:
        msg = sr["message"]
        if msg:
            # Truncate and clean up
            preview = msg[:120].replace("\n", " ")
            return f'"{preview}..."' if len(msg) > 120 else f'"{preview}"'

    # Fallback: check messages output
    messages = root_run.outputs.get("messages", [])
    if messages:
        # Get last AIMessage
        for msg in reversed(messages):
            if isinstance(msg, dict):
                msg_id = msg.get("id", [])
                if isinstance(msg_id, list) and "AIMessage" in msg_id:
                    content = msg.get("kwargs", {}).get("content", "")
                    if content:
                        preview = content[:120].replace("\n", " ")
                        return f'"{preview}..."' if len(content) > 120 else f'"{preview}"'

    return "(no PM message found)"


def safe_parse_dict(value: Any) -> dict[str, Any]:
    """Safely parse a string representation of a dict.

    Handles:
    - Already a dict -> return as-is
    - String repr like "{'key': 'value'}" -> ast.literal_eval
    - JSON string -> json.loads
    - Unparseable -> return empty dict

    Args:
        value: Value to parse

    Returns:
        Parsed dict or empty dict
    """
    import ast
    import json

    if isinstance(value, dict):
        return value

    if not isinstance(value, str):
        return {}

    # Try ast.literal_eval first (handles Python dict repr)
    try:
        result = ast.literal_eval(value)
        if isinstance(result, dict):
            return result
    except (ValueError, SyntaxError):
        pass

    # Try JSON parsing
    try:
        result = json.loads(value)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass

    return {}
