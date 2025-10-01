"""Cataloging department - orchestrates product cataloging workflow."""

from langchain.agents import create_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from autifyme_agents.core.llm_factory import get_llm
from autifyme_agents.tools.analysis_tools import analyze_product_image
from autifyme_agents.tools.storage_tools import save_product, get_company_profile
from autifyme_agents.core.prompt_loader import load_prompt


def create_cataloging_department() -> Runnable:
    """
    Creates the Department Head agent for Product Cataloging.
    
    Uses LangChain v1's `create_agent` which handles ReAct formatting internally
    and orchestrates the multi-step cataloging workflow.
    
    Returns:
        A runnable agent that takes {"messages": [("human", task)]} as input.
    """
    tools = [
        analyze_product_image,
        save_product,
        get_company_profile,
    ]
    
    custom_instructions = load_prompt("departments/cataloging_department.prompt")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", custom_instructions),
        ("human", "{messages}"),
        ("placeholder", "{agent_scratchpad}"),
    ])
    
    llm = get_llm()
    agent = create_agent(llm, tools, prompt=prompt)
    
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
