"""Vercel-compatible FastAPI entrypoint for AutifyME WhatsApp webhook."""

import sys
import os
from pathlib import Path

# Add the agents/src directory to the Python path
agents_src_path = Path(__file__).parent / "agents" / "src"
sys.path.insert(0, str(agents_src_path))

# Import and expose the FastAPI app
from autifyme_agents.entrypoints.whatsapp_webhook import app

# Vercel expects the app to be named 'app' and available at module level
__all__ = ["app"]