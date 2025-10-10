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

# Try importing the main app
try:
    from autifyme_agents.entrypoints.whatsapp_webhook import app as main_app
    HAS_MAIN_APP = True
    # Export the FastAPI app for Vercel (ASGI)
    app = main_app
except ImportError as e:
    print(f"Warning: Could not import main app: {e}")
    HAS_MAIN_APP = False

    # Fallback: Create a minimal ASGI app
    try:
        from fastapi import FastAPI
        app = FastAPI()

        @app.get("/health")
        async def health_check():
            return {"status": "partial", "message": "Main app not available", "error": str(e)}

        @app.get("/debug")
        async def debug():
            return {"message": "Hello from Vercel Python function!", "status": "debug_ok"}

        @app.get("/")
        async def root():
            return {"message": "Fallback FastAPI app", "error": str(e)}

    except ImportError:
        # No FastAPI available - create a basic WSGI app
        def app(environ, start_response):
            status = '200 OK'
            headers = [('Content-type', 'application/json')]
            start_response(status, headers)
            return [b'{"status": "no_dependencies", "message": "No FastAPI available"}']

# For Vercel, we need to export the app variable
__all__ = ["app"]