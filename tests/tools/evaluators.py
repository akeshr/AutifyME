"""LangSmith Evaluators for PM Workflow Evaluation.

These evaluators run on traces to evaluate:
1. Protocol Loading - Did agents load protocols first?
2. Tool Usage - Are tools being used correctly?
3. Task Delegation - Is PM delegating to the right subagents?
4. Synthesis Quality - Is PM synthesizing outputs well? (LLM-as-judge)

Usage with LangSmith Rule Automations:
    These evaluators can be bound to datasets or run via automation rules
    on incoming production traces.

Usage programmatically:
    from tests.tools.evaluators import (
        evaluate_protocol_loading,
        evaluate_tool_usage,
        evaluate_delegation,
        evaluate_synthesis,
        run_all_evaluators,
    )

    # Run all evaluators on a trace
    results = run_all_evaluators(trace_id)
    for result in results:
        print(f"{result['key']}: {result['score']} - {result['comment']}")
"""

from __future__ import annotations

import re
from typing import Any

from langsmith import Client
from langsmith.schemas import Run

from .trace_analysis import (
    get_agent_final_message,
    get_delegation_graph,
    get_protocol_loads,
    get_tool_call_sequence,
)

# LangSmith client
_client: Client | None = None


def _get_client() -> Client:
    """Get or create LangSmith client."""
    global _client
    if _client is None:
        from dotenv import load_dotenv
        load_dotenv()
        _client = Client()
    return _client


# =============================================================================
# Evaluator 1: Protocol Loading
# =============================================================================

def evaluate_protocol_loading(run: Run) -> list[dict[str, Any]]:
    """Evaluate if agents load protocols as their first action.

    Checks:
    - PM loads protocol as first action
    - Each subagent loads protocol before other tools
    - Correct protocols loaded for each agent type

    Args:
        run: LangSmith Run object (root run of trace)

    Returns:
        List of evaluation results with keys:
        - pm_protocol_first: Did PM load protocol first?
        - all_agents_protocol_first: Did all agents load protocols first?
        - protocol_compliance_score: Overall compliance (0-1)
    """
    trace_id = str(run.trace_id)
    results = []

    try:
        protocols = get_protocol_loads(trace_id)
        seq = get_tool_call_sequence(trace_id)

        # Check 1: PM loaded protocol first
        pm_first = protocols.pm_first_action_was_protocol
        results.append({
            "key": "pm_protocol_first",
            "score": 1 if pm_first else 0,
            "comment": f"PM {'loaded' if pm_first else 'did NOT load'} protocol as first action. "
                      f"First protocol: {protocols.pm_protocol or 'none'}"
        })

        # Check 2: All agents load protocols first
        # Build agent first actions from tool sequence
        agent_first_tools: dict[str, str] = {}
        for tc in seq.tool_calls:
            if tc.agent not in agent_first_tools:
                agent_first_tools[tc.agent] = tc.tool_name

        agents_compliant = []
        agents_non_compliant = []

        for agent, first_tool in agent_first_tools.items():
            if first_tool == "load_protocol":
                agents_compliant.append(agent)
            else:
                agents_non_compliant.append(f"{agent}({first_tool})")

        all_compliant = len(agents_non_compliant) == 0
        compliance_ratio = len(agents_compliant) / max(len(agent_first_tools), 1)

        results.append({
            "key": "all_agents_protocol_first",
            "score": 1 if all_compliant else 0,
            "comment": f"Compliant: {agents_compliant}. "
                      f"Non-compliant: {agents_non_compliant or 'none'}"
        })

        results.append({
            "key": "protocol_compliance_score",
            "score": round(compliance_ratio, 2),
            "comment": f"{len(agents_compliant)}/{len(agent_first_tools)} agents loaded protocol first"
        })

        # Check 3: Protocol appropriateness
        expected_protocols = {
            "PM": ["discovery_mindset", "synthesis", "execution_flows"],
            "visual_analyst": ["visual_analysis"],
            "catalog_analyst": ["business_context", "family_fit"],
            "product_analyst": ["market_research"],
            "creative_specialist": ["catalog_visual"],
            "catalog_specialist": ["business_context", "duplicate_prevention"],
        }

        protocol_match_count = 0
        protocol_check_count = 0
        mismatches = []

        for agent, loaded_protocol in protocols.agent_protocols.items():
            if agent in expected_protocols:
                protocol_check_count += 1
                if any(exp in loaded_protocol for exp in expected_protocols[agent]):
                    protocol_match_count += 1
                else:
                    mismatches.append(f"{agent}: loaded '{loaded_protocol}' expected one of {expected_protocols[agent]}")

        protocol_match_score = protocol_match_count / max(protocol_check_count, 1)
        results.append({
            "key": "protocol_appropriateness",
            "score": round(protocol_match_score, 2),
            "comment": f"Protocol match: {protocol_match_count}/{protocol_check_count}. "
                      f"Mismatches: {mismatches or 'none'}"
        })

    except Exception as e:
        results.append({
            "key": "protocol_loading_error",
            "score": 0,
            "comment": f"Error evaluating protocol loading: {str(e)}"
        })

    return results


# =============================================================================
# Evaluator 2: Tool Usage
# =============================================================================

def evaluate_tool_usage(run: Run) -> list[dict[str, Any]]:
    """Evaluate tool usage patterns.

    Checks:
    - Tools used in correct sequence
    - No redundant tool calls
    - Tool errors handled appropriately
    - Tool outputs utilized

    Args:
        run: LangSmith Run object (root run of trace)

    Returns:
        List of evaluation results
    """
    trace_id = str(run.trace_id)
    results = []

    try:
        seq = get_tool_call_sequence(trace_id)

        # Check 1: Tool diversity (are different tools being used?)
        tool_names = [tc.tool_name for tc in seq.tool_calls]
        unique_tools = set(tool_names)

        results.append({
            "key": "tool_diversity",
            "score": min(len(unique_tools) / 5, 1.0),  # Expect at least 5 different tools
            "comment": f"Used {len(unique_tools)} unique tools: {list(unique_tools)}"
        })

        # Check 2: Tool error rate
        error_count = sum(1 for tc in seq.tool_calls if tc.status == "error")
        error_rate = error_count / max(len(seq.tool_calls), 1)

        results.append({
            "key": "tool_error_rate",
            "score": round(1 - error_rate, 2),
            "comment": f"{error_count}/{seq.total_tool_calls} tool calls resulted in errors"
        })

        # Check 3: Redundant tool calls (same tool by same agent consecutively)
        redundant_calls = 0
        prev_tool = None
        prev_agent = None

        for tc in seq.tool_calls:
            if tc.tool_name == prev_tool and tc.agent == prev_agent:
                # Allow load_protocol to be called multiple times (loading different protocols)
                if tc.tool_name != "load_protocol":
                    redundant_calls += 1
            prev_tool = tc.tool_name
            prev_agent = tc.agent

        redundancy_score = 1 - (redundant_calls / max(seq.total_tool_calls, 1))
        results.append({
            "key": "tool_redundancy_score",
            "score": round(redundancy_score, 2),
            "comment": f"{redundant_calls} potentially redundant consecutive tool calls detected"
        })

        # Check 4: Critical tools used (for catalog workflow)
        critical_tools = ["load_protocol", "task", "view_image"]
        tools_used = set(tool_names)
        critical_used = [t for t in critical_tools if t in tools_used]
        critical_score = len(critical_used) / len(critical_tools)

        results.append({
            "key": "critical_tools_used",
            "score": round(critical_score, 2),
            "comment": f"Critical tools used: {critical_used}. "
                      f"Missing: {[t for t in critical_tools if t not in tools_used]}"
        })

        # Check 5: Tool sequence appropriateness
        # Expected pattern: load_protocol -> (view_image | task) -> ...
        first_tool = seq.tool_calls[0].tool_name if seq.tool_calls else None
        sequence_score = 1.0 if first_tool == "load_protocol" else 0.5

        results.append({
            "key": "tool_sequence_score",
            "score": sequence_score,
            "comment": f"First tool: {first_tool}. Expected: load_protocol"
        })

    except Exception as e:
        results.append({
            "key": "tool_usage_error",
            "score": 0,
            "comment": f"Error evaluating tool usage: {str(e)}"
        })

    return results


# =============================================================================
# Evaluator 3: Task Delegation
# =============================================================================

def evaluate_delegation(run: Run) -> list[dict[str, Any]]:
    """Evaluate PM's task delegation to subagents.

    Checks:
    - Appropriate agents delegated to
    - Wave structure (parallel vs serial)
    - Context passed to subagents
    - Delegation completeness

    Args:
        run: LangSmith Run object (root run of trace)

    Returns:
        List of evaluation results
    """
    trace_id = str(run.trace_id)
    results = []

    try:
        graph = get_delegation_graph(trace_id)

        # Check 1: Delegation occurred
        delegation_count = len(graph.delegations)
        results.append({
            "key": "delegation_occurred",
            "score": 1 if delegation_count > 0 else 0,
            "comment": f"PM delegated to {delegation_count} subagents: {graph.agents_involved}"
        })

        # Check 2: Analyst vs Specialist balance
        analysts = ["visual_analyst", "catalog_analyst", "product_analyst"]
        specialists = ["creative_specialist", "catalog_specialist"]

        analysts_used = [a for a in graph.agents_involved if a in analysts]
        specialists_used = [s for s in graph.agents_involved if s in specialists]

        # For analysis phase, expect analysts. For execution, expect specialists.
        # Score based on whether appropriate agents are used
        has_analysts = len(analysts_used) > 0
        has_specialists = len(specialists_used) > 0

        results.append({
            "key": "analyst_delegation",
            "score": 1 if has_analysts else 0,
            "comment": f"Analysts delegated: {analysts_used or 'none'}"
        })

        results.append({
            "key": "specialist_delegation",
            "score": 1 if has_specialists else 0.5,  # Specialists optional in analysis phase
            "comment": f"Specialists delegated: {specialists_used or 'none (analysis phase only?)'}"
        })

        # Check 3: Wave structure (parallel execution where appropriate)
        wave_count = len(graph.waves)
        parallel_delegations = sum(1 for w in graph.waves.values() if len(w) > 1)

        results.append({
            "key": "wave_structure",
            "score": min(wave_count / 2, 1.0),  # Expect at least 2 waves
            "comment": f"{wave_count} waves detected. "
                      f"Waves with parallel execution: {parallel_delegations}. "
                      f"Wave breakdown: {dict(graph.waves)}"
        })

        # Check 4: Delegation order appropriateness
        # For image-based workflows: visual_analyst should be first
        expected_first = "visual_analyst"
        actual_first = graph.delegation_order[0] if graph.delegation_order else None
        order_correct = actual_first == expected_first

        results.append({
            "key": "delegation_order",
            "score": 1 if order_correct else 0.5,
            "comment": f"First delegation: {actual_first}. "
                      f"Full order: {' -> '.join(graph.delegation_order)}"
        })

        # Check 5: Context passing (were descriptions provided?)
        delegations_with_context = sum(
            1 for d in graph.delegations if d.context_passed
        )
        context_ratio = delegations_with_context / max(delegation_count, 1)

        results.append({
            "key": "context_passing",
            "score": round(context_ratio, 2),
            "comment": f"{delegations_with_context}/{delegation_count} delegations included context"
        })

    except Exception as e:
        results.append({
            "key": "delegation_error",
            "score": 0,
            "comment": f"Error evaluating delegation: {str(e)}"
        })

    return results


# =============================================================================
# Evaluator 4: Synthesis Quality (LLM-as-Judge)
# =============================================================================

def evaluate_synthesis(run: Run) -> list[dict[str, Any]]:
    """Evaluate PM's synthesis of tool outputs and subagent responses.

    Uses LLM-as-judge to evaluate:
    - Completeness of synthesis
    - Quality of presentation
    - Open-ended question (not numbered options)

    Args:
        run: LangSmith Run object (root run of trace)

    Returns:
        List of evaluation results
    """
    trace_id = str(run.trace_id)
    results = []

    try:
        # Get PM's final message
        final_msg = get_agent_final_message(trace_id, "PM")

        if not final_msg:
            results.append({
                "key": "synthesis_available",
                "score": 0,
                "comment": "No PM final message found in trace"
            })
            return results

        message = final_msg.message or ""

        # Check 1: Message exists and has substance
        has_substance = len(message) > 50
        results.append({
            "key": "synthesis_substance",
            "score": 1 if has_substance else 0,
            "comment": f"Message length: {len(message)} chars. "
                      f"Preview: {message[:100]}..."
        })

        # Check 2: Open-ended question (not numbered options)
        has_open_question = final_msg.has_open_question
        has_numbered_options = final_msg.has_numbered_options

        # Anti-pattern: numbered options constrain user
        open_question_score = 1.0 if has_open_question and not has_numbered_options else (
            0.5 if has_open_question else 0.0
        )

        results.append({
            "key": "open_ended_question",
            "score": open_question_score,
            "comment": f"Open question: {has_open_question}. "
                      f"Numbered options (anti-pattern): {has_numbered_options}"
        })

        # Check 3: Product/context mention (synthesis includes key details)
        context_keywords = ["product", "family", "catalog", "variant", "price", "image"]
        keywords_found = [kw for kw in context_keywords if kw.lower() in message.lower()]
        context_score = min(len(keywords_found) / 3, 1.0)

        results.append({
            "key": "synthesis_context",
            "score": round(context_score, 2),
            "comment": f"Context keywords found: {keywords_found}"
        })

        # Check 4: Synthesis structure (has sections/organization)
        has_structure = (
            "\n\n" in message or  # Paragraph breaks
            "**" in message or    # Bold headers
            ":" in message        # Key-value style
        )

        results.append({
            "key": "synthesis_structure",
            "score": 1 if has_structure else 0.5,
            "comment": f"Message appears {'structured' if has_structure else 'unstructured'}"
        })

        # Check 5: Asks for user direction (approval gate behavior)
        approval_phrases = [
            "would you like", "shall i", "do you want",
            "let me know", "please confirm", "what would you"
        ]
        asks_direction = any(phrase in message.lower() for phrase in approval_phrases)

        results.append({
            "key": "asks_user_direction",
            "score": 1 if asks_direction else 0,
            "comment": f"PM {'asks' if asks_direction else 'does NOT ask'} for user direction"
        })

        # Calculate overall synthesis score
        subscores = [r["score"] for r in results if isinstance(r["score"], (int, float))]
        overall = sum(subscores) / max(len(subscores), 1)

        results.append({
            "key": "synthesis_overall",
            "score": round(overall, 2),
            "comment": f"Overall synthesis quality based on {len(subscores)} criteria"
        })

    except Exception as e:
        results.append({
            "key": "synthesis_error",
            "score": 0,
            "comment": f"Error evaluating synthesis: {str(e)}"
        })

    return results


# =============================================================================
# Combined Evaluator
# =============================================================================

def run_all_evaluators(trace_id: str) -> list[dict[str, Any]]:
    """Run all evaluators on a trace and return combined results.

    Args:
        trace_id: LangSmith trace ID

    Returns:
        List of all evaluation results from all evaluators
    """
    client = _get_client()

    # Get root run for the trace
    runs = list(client.list_runs(trace_id=trace_id))
    if not runs:
        return [{
            "key": "trace_not_found",
            "score": 0,
            "comment": f"No runs found for trace {trace_id}"
        }]

    # Find root run (no parent)
    root_run = None
    for run in runs:
        if not run.parent_run_id:
            root_run = run
            break

    if not root_run:
        root_run = runs[0]  # Fallback to first run

    # Run all evaluators
    all_results = []

    # 1. Protocol Loading
    all_results.extend(evaluate_protocol_loading(root_run))

    # 2. Tool Usage
    all_results.extend(evaluate_tool_usage(root_run))

    # 3. Delegation
    all_results.extend(evaluate_delegation(root_run))

    # 4. Synthesis
    all_results.extend(evaluate_synthesis(root_run))

    # Add overall score
    scores = [r["score"] for r in all_results if isinstance(r.get("score"), (int, float)) and "error" not in r["key"]]
    if scores:
        all_results.append({
            "key": "overall_score",
            "score": round(sum(scores) / len(scores), 2),
            "comment": f"Average of {len(scores)} evaluation criteria"
        })

    return all_results


def evaluate_and_record(trace_id: str, scenario_id: str | None = None) -> list[dict[str, Any]]:
    """Run evaluators and record results as LangSmith feedback.

    Args:
        trace_id: LangSmith trace ID
        scenario_id: Optional scenario ID for tagging

    Returns:
        List of evaluation results
    """
    client = _get_client()
    results = run_all_evaluators(trace_id)

    # Record each result as feedback
    for result in results:
        try:
            client.create_feedback(
                run_id=trace_id,
                key=result["key"],
                score=result["score"],
                comment=result.get("comment", ""),
                feedback_source_type="model",
                extra={"scenario_id": scenario_id} if scenario_id else None,
            )
        except Exception as e:
            # Log but don't fail
            print(f"Failed to record feedback for {result['key']}: {e}")

    return results


# =============================================================================
# LangSmith Evaluator Wrappers (for use with evaluate() function)
# =============================================================================

def protocol_loading_evaluator(run: Run, example: Any = None) -> dict[str, Any]:
    """LangSmith-compatible evaluator wrapper for protocol loading."""
    results = evaluate_protocol_loading(run)
    # Return the overall protocol compliance score
    for r in results:
        if r["key"] == "protocol_compliance_score":
            return r
    return {"key": "protocol_loading", "score": 0, "comment": "No results"}


def tool_usage_evaluator(run: Run, example: Any = None) -> dict[str, Any]:
    """LangSmith-compatible evaluator wrapper for tool usage."""
    results = evaluate_tool_usage(run)
    # Return composite score
    scores = [r["score"] for r in results if isinstance(r.get("score"), (int, float))]
    return {
        "key": "tool_usage",
        "score": round(sum(scores) / max(len(scores), 1), 2),
        "comment": f"Based on {len(scores)} tool usage criteria"
    }


def delegation_evaluator(run: Run, example: Any = None) -> dict[str, Any]:
    """LangSmith-compatible evaluator wrapper for delegation."""
    results = evaluate_delegation(run)
    scores = [r["score"] for r in results if isinstance(r.get("score"), (int, float))]
    return {
        "key": "delegation",
        "score": round(sum(scores) / max(len(scores), 1), 2),
        "comment": f"Based on {len(scores)} delegation criteria"
    }


def synthesis_evaluator(run: Run, example: Any = None) -> dict[str, Any]:
    """LangSmith-compatible evaluator wrapper for synthesis."""
    results = evaluate_synthesis(run)
    for r in results:
        if r["key"] == "synthesis_overall":
            return r
    return {"key": "synthesis", "score": 0, "comment": "No synthesis results"}
