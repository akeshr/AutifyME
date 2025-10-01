"""
Cataloging department - orchestrates product cataloging workflow.

Architecture Note:
This implementation currently uses a simplified single-layer approach where
the department agent directly uses tools. This works but violates our
documented architecture which calls for:
  [Department Head] → [Specialists] → [Tools]

TODO: Refactor to proper 3-layer hierarchy once we have multi-department workflows.
For now, this pattern is acceptable for our MVP.
"""

from typing import TypedDict, Annotated, Sequence
import operator

from langchain.agents import create_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableLambda
from langchain_core.messages import BaseMessage
from langgraph.checkpoint.base import BaseCheckpointSaver

from autifyme_agents.core.llm_factory import get_llm
from autifyme_agents.core.prompt_loader import load_prompt
from autifyme_agents.tools.analysis_tools import analyze_product_image
from autifyme_agents.tools.storage_tools import save_product

# This is the new state for our graph.
# It tracks the list of messages, which is the core of the conversation.
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]


def create_cataloging_department(checkpointer: BaseCheckpointSaver) -> Runnable:
    """
    Creates the Department Head agent for Product Cataloging.
    
    This version is stateful, using the provided checkpointer to persist
    state across runs.
    
    Current Implementation:
        Uses a simplified single-layer approach where tools handle both
        specialist-level operations (image analysis) and storage operations.
        
    Future Architecture:
        Should be refactored to:
        [Department] → [ImageAnalysisSpecialist, CatalogingSpecialist] → [Tools]
        
    Args:
        checkpointer: An already instantiated checkpointer (e.g., PostgresSaver).

    Returns:
        A stateful, runnable agent graph.
    
    Note on Output:
        The graph returns the full state dict: {"messages": [all_messages]}.
        LangSmith will display this entire structure. The final AIMessage
        (last in the list) contains the actual response.
    """
    tools = [
        analyze_product_image,   # TODO: Should be a specialist, not a tool
        save_product,            # ✅ Correct - storage operation
        # get_company_profile removed - injected via middleware instead
    ]
    
    custom_instructions = load_prompt("departments/cataloging_department.prompt")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", custom_instructions),
        ("placeholder", "{messages}"),
    ])
    
    llm = get_llm()
    
    # create_agent already returns a CompiledStateGraph with agent + tools routing
    # We just need to pass the checkpointer and configuration
    agent_graph = create_agent(
        llm, 
        tools,
        prompt=prompt,
        checkpointer=checkpointer,
        name="CatalogingDepartmentAgent"
    )
    
    # Transform output: Extract final message for cleaner API response
    # WHY: Project Manager (orchestrator) needs just the result, not full conversation
    # HOW: Pipe the graph through a lambda that extracts the last AI message
    # 
    # Input to graph: {"messages": [HumanMessage(...)]}
    # Output from graph: {"messages": [HumanMessage, AIMessage, ToolMessage, ...]}
    # Output after transform: {"output": "Final AI response text"}
    #
    # This pattern uses LangChain's LCEL (LangChain Expression Language):
    # - The graph runs normally with full state (needed for tools/checkpointing)
    # - The lambda transforms it before returning to the caller
    # - LangSmith will show the transformed output (just the final message)
    def extract_final_output(state: dict) -> dict:
        """
        Simply extract the final AI message content.
        
        No complex parsing - just return the last message.
        Project Manager can parse it if needed, or we can use
        .with_structured_output() at the LLM level for typed responses.
        """
        # During streaming, pass through chunks unchanged
        if "messages" not in state:
            return state
            
        messages = state["messages"]
        if not messages:
            return state
        
        # Get final message content
        final_message = messages[-1]
        content = final_message.content if hasattr(final_message, 'content') else str(final_message)
        
        return {"output": content}
    
    # Pipe: graph → extract_final_output
    # Note: Piping creates a RunnableSequence, so we need to configure AFTER piping
    piped_chain = agent_graph | RunnableLambda(extract_final_output)
    
    # Configure with metadata for LangSmith tracing
    # IMPORTANT: Must be done AFTER piping to preserve the name
    return piped_chain.with_config({
        "run_name": "CatalogingDepartment",
        "tags": ["department:cataloging", "workflow:Cataloging"],
        "metadata": {
            "department": "cataloging",
            "workflow": "Cataloging",
            "agent_type": "department_head"
        }
    })
