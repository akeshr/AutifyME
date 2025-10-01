from functools import wraps
import logging
from typing import Any, Callable

# Configure a basic logger for now. We will implement structured logging later.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_company_profile(company_id: str) -> dict:
    """
    Placeholder function to retrieve a company's profile.
    In a real implementation, this would fetch data from our storage layer.
    """
    # This will be replaced by a call to the StorageInterface
    logger.info(f"Fetching profile for company_id: {company_id}")
    return {
        "id": company_id,
        "name": f"Company {company_id}",
        "brand_voice": "Friendly and professional",
        "target_audience": "Small business owners",
    }


def company_context_middleware(func: Callable) -> Callable:
    """
    Middleware decorator to automatically inject the 'company_profile' into a tool's kwargs.

    This assumes the company_id is passed within the agent's runtime configuration,
    which we will set up at the entry point of our application (e.g., the webhook).
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        config = kwargs.get("config", {})
        configurable = config.get("configurable", {})
        company_id = configurable.get("company_id")

        if not company_id:
            logger.warning(
                f"Tool '{func.__name__}' was called without a 'company_id' in the config. "
                "Skipping company_profile injection."
            )
        elif "company_profile" not in kwargs:
            # Fetch the profile and inject it into the tool's arguments
            company_profile = get_company_profile(company_id)
            kwargs["company_profile"] = company_profile
            logger.info(f"Injected company profile for '{company_profile['name']}' into '{func.__name__}'")

        return func(*args, **kwargs)

    return wrapper


def langsmith_tracing_middleware(
    func: Callable, workflow_id: str, department: str, specialist_name: str
) -> Callable:
    """
    Middleware factory to enrich LangSmith traces with specific workflow metadata.

    This is not a direct decorator, but a function that returns a configured
    decorator, allowing us to pass dynamic metadata.
    """

    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            config = kwargs.setdefault("config", {})
            metadata = config.setdefault("metadata", {})

            # Add our custom tags for better filtering and debugging in LangSmith
            metadata.update(
                {
                    "autifyme_workflow_id": workflow_id,
                    "autifyme_department": department,
                    "autifyme_specialist": specialist_name,
                }
            )
            logger.info(f"Enriched LangSmith trace for '{specialist_name}'")
            return fn(*args, **kwargs)

        return wrapper

    return decorator(func)

