import os


def load_prompt(file_name: str) -> str:
    """
    Loads a prompt template from the filesystem.

    This function is the designated way to access version-controlled
    prompts, ensuring that prompt content is decoupled from the agent logic.

    Args:
        file_name: The name of the prompt file, relative to the `prompts` directory.
                   e.g., "specialists/cataloging_specialist.prompt"

    Returns:
        The string content of the prompt template.

    Raises:
        FileNotFoundError: If the prompt file does not exist.
    """
    # Construct the full path to the prompt file.
    # __file__ gives the path of the current script (prompt_loader.py).
    # We navigate up one level to `core` and then down to `prompts`.
    base_path = os.path.dirname(__file__)
    prompt_path = os.path.join(base_path, '..', 'prompts', file_name)

    if not os.path.exists(prompt_path):
        raise FileNotFoundError(f"Prompt file not found at: {prompt_path}")

    with open(prompt_path, encoding='utf-8') as f:
        return f.read()
