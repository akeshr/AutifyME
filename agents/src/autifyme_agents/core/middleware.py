from functools import wraps
import logging
from typing import Any, Callable

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def company_context_middleware(func: Callable) -> Callable:
    """
    Middleware decorator to inject company_profile from storage layer.
    
    Uses the global storage client initialized at application startup.
    The storage client must be initialized via initialize_storage() before
    any middleware-decorated tools are invoked.
    
    Also passes LangChain config through to enable proper trace nesting.
    """

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Extract config for trace propagation
        config = kwargs.pop("config", {})
        
        if "company_profile" not in kwargs:
            # Import here to avoid circular dependency
            from autifyme_agents.tools.storage_tools import _storage_client
            
            if _storage_client is None:
                logger.warning(
                    f"Tool '{func.__name__}' called but storage client not initialized. "
                    "Skipping company_profile injection."
                )
            else:
                try:
                    company_profile = _storage_client.get_company_profile()
                    kwargs["company_profile"] = company_profile
                    logger.info(f"Injected company profile for '{company_profile.name}' into '{func.__name__}'")
                except Exception as e:
                    logger.error(f"Failed to fetch company profile: {e}")

        # Pass config through for downstream LangChain calls (specialists, LLMs)
        kwargs["_langchain_config"] = config
        
        return await func(*args, **kwargs)

    return wrapper


def langsmith_tracing_middleware(workflow_name: str) -> Callable:
    """
    Middleware factory to inject LangSmith tracing metadata.
    
    Enriches the LangChain config with workflow-specific tags and metadata
    for better trace organization in LangSmith.
    
    Note: This middleware operates at the decorator level and modifies the
    wrapped function's metadata. For tools that call LLMs or specialists,
    the config propagation happens through LangChain's RunnableConfig system.
    """
    def decorator(func: Callable) -> Callable:
        import asyncio
        
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs) -> Any:
                config = kwargs.pop("config", {})
                
                # Enrich config with workflow context
                metadata = config.setdefault("metadata", {})
                metadata["workflow"] = workflow_name
                metadata["tool_name"] = func.__name__
                
                tags = config.setdefault("tags", [])
                if f"workflow:{workflow_name}" not in tags:
                    tags.append(f"workflow:{workflow_name}")
                
                run_name = config.setdefault("run_name", func.__name__)
                if not run_name.startswith(workflow_name):
                    config["run_name"] = f"{workflow_name}-{run_name}"
                
                # Store enriched config in kwargs for downstream LangChain calls
                # Tools that invoke specialists/LLMs will use this config
                kwargs["_langchain_config"] = config
                
                result = await func(*args, **kwargs)
                return result
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs) -> Any:
                config = kwargs.pop("config", {})
                
                # Enrich config with workflow context
                metadata = config.setdefault("metadata", {})
                metadata["workflow"] = workflow_name
                metadata["tool_name"] = func.__name__
                
                tags = config.setdefault("tags", [])
                if f"workflow:{workflow_name}" not in tags:
                    tags.append(f"workflow:{workflow_name}")
                
                run_name = config.setdefault("run_name", func.__name__)
                if not run_name.startswith(workflow_name):
                    config["run_name"] = f"{workflow_name}-{run_name}"
                
                # Store enriched config in kwargs for downstream LangChain calls
                kwargs["_langchain_config"] = config
                
                result = func(*args, **kwargs)
                return result
            return sync_wrapper
    return decorator

