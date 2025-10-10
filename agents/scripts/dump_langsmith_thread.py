"""Dump LangSmith run details for a given thread id.

Usage:
    uv run python agents/scripts/dump_langsmith_thread.py --thread <thread-id>

This script fetches the run corresponding to the provided thread id and
prints a detailed, hierarchical view of all child runs, including agent
messages, tool calls, and structured outputs. It leverages the guidance from
the LangSmith documentation on tracing entire applications.
"""

from __future__ import annotations

import argparse
from collections import deque
from typing import Any, Dict, List, Optional

from langsmith import Client
from langsmith.schemas import Run


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dump LangSmith run details for a thread")
    parser.add_argument(
        "--thread",
        required=True,
        help="Thread ID associated with the LangGraph run (configurable.thread_id)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=200,
        help="Maximum number of recent runs to search (default: 200)",
    )
    return parser.parse_args()


def resolve_run(thread_id: str, limit: int) -> Optional[Run]:
    client = Client()
    runs = client.list_runs(order="desc", limit=limit)
    for run in runs:
        config_meta: Dict[str, Any] = (run.inputs or {}).get("config", {}) if run.inputs else {}
        configurable = config_meta.get("configurable", {}) if isinstance(config_meta, dict) else {}
        if configurable.get("thread_id") == thread_id:
            return run
    return None


def fetch_run_tree(client: Client, root_run: Run) -> Run:
    return client.get_run(root_run.id, include_children=True)


def format_messages(run: Run) -> List[str]:
    messages: List[str] = []
    if run.outputs:
        outputs = run.outputs
        if "output" in outputs:
            messages.append(f"Output: {outputs['output']}")
        if "structured_response" in outputs:
            messages.append(f"Structured Response: {outputs['structured_response']}")
    if run.inputs:
        inputs = run.inputs
        if "messages" in inputs:
            messages.append("Input Messages:")
            for msg in inputs["messages"]:
                role = msg.get("role")
                content = msg.get("content")
                messages.append(f"  - {role}: {content}")
    return messages


def dump_run_tree(root: Run) -> None:
    queue = deque([(root, 0)])
    while queue:
        current, depth = queue.popleft()
        indent = "  " * depth
        print(f"{indent}Run: {current.name} ({current.id})")
        print(f"{indent}  Type: {current.run_type} | Status: {current.status}")
        config_meta = (current.inputs or {}).get("config", {}) if current.inputs else {}
        configurable = config_meta.get("configurable", {}) if isinstance(config_meta, dict) else {}
        if configurable:
            print(f"{indent}  Configurable: {configurable}")
        for message in format_messages(current):
            print(f"{indent}  {message}")
        if current.outputs and "error" in current.outputs:
            print(f"{indent}  Error: {current.outputs['error']}")
        if current.child_runs:
            for child in current.child_runs:
                queue.append((child, depth + 1))


def main() -> None:
    args = parse_args()
    thread_id: str = args.thread
    print(f"Searching for LangSmith run with thread_id={thread_id}")
    client = Client()
    root_run = resolve_run(thread_id, args.limit)
    if not root_run:
        raise SystemExit(f"No run found for thread_id={thread_id}")
    print(f"Found run: {root_run.id} ({root_run.name})")
    run_tree = fetch_run_tree(client, root_run)
    dump_run_tree(run_tree)


if __name__ == "__main__":
    main()

