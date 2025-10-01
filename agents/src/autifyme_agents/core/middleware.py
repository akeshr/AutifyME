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
    """

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
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

        return await func(*args, **kwargs)

    return wrapper


def langsmith_tracing_middleware(workflow_name: str) -> Callable:
    """
    Middleware factory to inject LangSmith tracing tags and run_name.

    This allows us to automatically add context to all LangSmith traces
    for tools within a specific workflow.
    
    The middleware extracts the config, enriches it, but then removes it
    from kwargs before calling the tool function (since tools don't expect it).
    
    Supports both sync and async tools automatically.
    """
    def decorator(func: Callable) -> Callable:
        # Check if the wrapped function is async
        import asyncio
        import inspect
        
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs) -> Any:
                # Extract and enrich config for LangSmith tracing
                config = kwargs.pop("config", {})
                tags = config.get("tags", [])
                run_name = config.get("run_name", func.__name__)

                # Add workflow-specific tags
                tags.append(f"workflow:{workflow_name}")
                config["tags"] = tags
                config["run_name"] = f"{workflow_name}-{run_name}"
                
                # The config is used by LangChain's tracing automatically;
                # we don't pass it down to the tool function
                return await func(*args, **kwargs)
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs) -> Any:
                # Extract and enrich config for LangSmith tracing
                config = kwargs.pop("config", {})
                tags = config.get("tags", [])
                run_name = config.get("run_name", func.__name__)

                # Add workflow-specific tags
                tags.append(f"workflow:{workflow_name}")
                config["tags"] = tags
                config["run_name"] = f"{workflow_name}-{run_name}"
                
                # The config is used by LangChain's tracing automatically;
                # we don't pass it down to the tool function
                return func(*args, **kwargs)
            return sync_wrapper
    return decorator

