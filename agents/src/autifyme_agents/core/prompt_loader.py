from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=32)
def load_prompt(file_name: str) -> str:
    """
    Loads a prompt template from the filesystem with caching.

    Uses functools.lru_cache to avoid repeated disk I/O for the same prompts.
    Cache size of 32 is sufficient for all current prompts (PM + specialists).

    This function is the designated way to access version-controlled
    prompts, ensuring that prompt content is decoupled from the agent logic.

    Args:
        file_name: The name of the prompt file, relative to the `prompts` directory.
                   e.g., "specialists/catalog_specialist.prompt"

    Returns:
        The string content of the prompt template.

    Raises:
        FileNotFoundError: If the prompt file does not exist.
    """
    # Construct the full path to the prompt file using pathlib.
    # Path(__file__).parent gives the directory of the current script (core/).
    # We navigate up to parent and then down to prompts/.
    base_path = Path(__file__).parent.parent  # Go up from core/ to autifyme_agents/
    prompt_path = (base_path / "prompts" / file_name).resolve()

    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found at: {prompt_path}")

    return prompt_path.read_text(encoding="utf-8")
