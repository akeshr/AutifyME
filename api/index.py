"""Vercel API route for AutifyME WhatsApp webhook with built-in routing."""

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

# Try importing the main app, fallback to simple responses if dependencies missing
try:
    from autifyme_agents.entrypoints.whatsapp_webhook import app as main_app
    HAS_MAIN_APP = True
except ImportError as e:
    print(f"Warning: Could not import main app: {e}")
    HAS_MAIN_APP = False

    # Fallback simple app
    try:
        from fastapi import FastAPI
        main_app = FastAPI()

        @main_app.get("/health")
        async def health_check():
            return {"status": "partial", "message": "Main app not available", "error": str(e)}

        @main_app.get("/")
        async def root():
            return {"message": "Fallback FastAPI app", "error": str(e)}
    except ImportError:
        # No FastAPI available
        def main_app(request):
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": f'{{"status": "no_dependencies", "message": "No FastAPI available", "error": "{str(e)}"}}'
            }

# Vercel handler function
def handler(request):
    """Handle Vercel requests."""
    try:
        # Get the path from the request
        path = request.get("path", "/")

        # Simple routing based on path
        if path == "/debug":
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": '{"message": "Hello from Vercel Python function!", "status": "debug_ok"}'
            }
        elif path == "/simple/health":
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": '{"status": "healthy", "message": "Simple endpoint working"}'
            }
        elif path in ["/health", "/"]:
            if HAS_MAIN_APP:
                # For main app routes, we'd need ASGI handling
                # For now, return a simple response
                return {
                    "statusCode": 200,
                    "headers": {"Content-Type": "application/json"},
                    "body": '{"status": "healthy", "service": "autifyme-webhook", "has_main_app": true}'
                }
            else:
                return {
                    "statusCode": 200,
                    "headers": {"Content-Type": "application/json"},
                    "body": '{"status": "healthy", "service": "autifyme-webhook", "has_main_app": false}'
                }
        else:
            return {
                "statusCode": 404,
                "headers": {"Content-Type": "application/json"},
                "body": f'{{"error": "Not found", "path": "{path}"}}'
            }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": f'{{"error": "Internal server error", "details": "{str(e)}"}}'
        }

# For local development
if __name__ == "__main__":
    print("Testing Vercel handler...")
    # Test debug endpoint
    result = handler({"path": "/debug"})
    print(f"Debug test: {result}")

    # Test health endpoint
    result = handler({"path": "/health"})
    print(f"Health test: {result}")