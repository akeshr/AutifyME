"""Vercel API route for AutifyME WhatsApp webhook."""

import sys
import os
from pathlib import Path

# Add the agents/src directory to the Python path
# In Vercel, files are deployed to /var/task
agents_src_path = Path("/var/task/agents/src")
if agents_src_path.exists():
    sys.path.insert(0, str(agents_src_path))
else:
    # Fallback for local development
    project_root = Path(__file__).parent.parent
    agents_src_path = project_root / "agents" / "src"
    if agents_src_path.exists():
        sys.path.insert(0, str(agents_src_path))

# Import and expose the FastAPI app
from autifyme_agents.entrypoints.whatsapp_webhook import app

# Vercel expects the app to be available at module level
__all__ = ["app"]
