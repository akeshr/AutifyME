"""Vercel-compatible FastAPI entrypoint for AutifyME WhatsApp webhook."""

# Import the FastAPI app instance from the actual application entrypoint.
# Vercel will detect and serve this 'app' instance.
from autifyme_agents.entrypoints.whatsapp_webhook import app

# The __all__ variable is a convention to explicitly state which names are
# part of the public API of this module. Vercel doesn't require this, but
# it's good practice.
__all__ = ["app"]