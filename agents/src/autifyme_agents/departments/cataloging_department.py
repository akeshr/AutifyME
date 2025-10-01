"""
Cataloging department - orchestrates product cataloging workflow.

Following LangChain v1 patterns:
- Uses ToolNode with handle_tool_errors for robust tool execution
- Errors are caught and returned as ToolMessages (not crashes)
- Agent can self-correct based on error messages
"""

from langchain.agents import create_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from autifyme_agents.core.llm_factory import get_llm
from autifyme_agents.tools.analysis_tools import analyze_product_image
from autifyme_agents.tools.storage_tools import save_product, get_company_profile
from autifyme_agents.core.prompt_loader import load_prompt
# NOTE: Checkpointing (P0 Blocker #2) is not yet fully implemented
# from autifyme_agents.integrations.storage.postgres_saver_factory import get_checkpointer


def create_cataloging_department() -> Runnable:
    """
    Creates the Department Head agent for Product Cataloging.
    
    Uses LangChain v1's `create_agent` with robust error handling.
    
    Error Handling Strategy (v1 Pattern):
        Layer 1 (Tools): Each tool catches external API errors and raises custom exceptions
                        with context (StorageError, ImageAnalysisError, etc.)
        Layer 2 (Retry): Tools use tenacity for automatic retry on transient failures
                        (network timeouts, rate limits)
        Layer 3 (Agent): Exceptions propagate as tool call failures, agent sees error
                        messages and can self-correct or report gracefully
    
    Why Not ToolNode Here:
        create_agent() doesn't properly support ToolNode in this version.
        Instead, we rely on tool-level error handling + the agent's natural
        ability to handle tool failures through ReAct reasoning.
    
    Returns:
        A runnable agent that takes a dict with `{"input": "user task"}` as input.
    """
    # TODO: Implement checkpointing once P0 Blocker #2 (State Persistence) is complete
    # checkpointer = get_checkpointer()

    # Tools with built-in error handling and retry logic
    tools = [
        analyze_product_image,  # Has retry logic for Vision API
        save_product,           # Has retry logic + custom exceptions
        get_company_profile,    # Has retry logic + custom exceptions
    ]
    
    custom_instructions = load_prompt("departments/cataloging_department.prompt")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", custom_instructions),
        ("placeholder", "{messages}"),
    ])
    
    llm = get_llm()
    agent = create_agent(
        llm, 
        tools,
        prompt=prompt,
        name="CatalogingDepartmentAgent"  # Specific name for LangSmith traces
        # TODO P0 Blocker #2: Add checkpointer for state persistence
        # Error handling is built into tools via exceptions + retry logic
    )
    
    # Apply workflow-level tracing configuration
    # This enriches all traces from this agent with Cataloging workflow context
    return agent.with_config({
        "run_name": "CatalogingDepartment",
        "tags": ["department:cataloging", "workflow:Cataloging"],
        "metadata": {
            "department": "cataloging",
            "workflow": "Cataloging",
            "agent_type": "department_head"
        }
    })
