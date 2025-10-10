"""Vercel-compatible FastAPI entrypoint for AutifyME WhatsApp webhook."""

import sys
from pathlib import Path

# Ensure the 'agents/src' directory is in the Python path to allow for absolute imports
# of the 'autifyme_agents' package. This is necessary because the entrypoint 'app.py'
# is at the project root, while the main application source is nested.
project_root = Path(__file__).parent
agents_src_path = project_root / "agents" / "src"
if str(agents_src_path) not in sys.path:
    sys.path.insert(0, str(agents_src_path))

# Import the FastAPI app instance from the actual application entrypoint.
# Vercel will detect and serve this 'app' instance.
from autifyme_agents.entrypoints.whatsapp_webhook import app

# The __all__ variable is a convention to explicitly state which names are
# part of the public API of this module. Vercel doesn't require this, but
# it's good practice.
__all__ = ["app"]