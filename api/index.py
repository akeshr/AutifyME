"""Vercel-compatible entry point for FastAPI application."""

import sys
import os

# Add the agents/src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agents', 'src'))

# Import and expose the FastAPI app
from autifyme_agents.entrypoints.whatsapp_webhook import app

# Vercel expects the app to be named 'app'
app = app
