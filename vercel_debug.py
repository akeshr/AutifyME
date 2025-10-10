"""Vercel-compatible debug endpoint to diagnose deployment issues."""

import json
import os
import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

def check_imports():
    """Check if all required imports work."""
    results = {}
    try:
        import fastapi
        results["fastapi"] = "✅ imported"
    except Exception as e:
        results["fastapi"] = f"❌ failed: {e}"

    try:
        import supabase
        results["supabase"] = "✅ imported"
    except Exception as e:
        results["supabase"] = f"❌ failed: {e}"

    try:
        import langchain
        results["langchain"] = "✅ imported"
    except Exception as e:
        results["langchain"] = f"❌ failed: {e}"

    try:
        import langgraph
        results["langgraph"] = "✅ imported"
    except Exception as e:
        results["langgraph"] = f"❌ failed: {e}"

    try:
        import deepagents
        results["deepagents"] = "✅ imported"
    except Exception as e:
        results["deepagents"] = f"❌ failed: {e}"

    return results

def check_environment():
    """Check environment variables."""
    required_vars = [
        'SUPABASE_URL',
        'SUPABASE_ANON_KEY',
        'DATABASE_URL',
        'WHATSAPP_WEBHOOK_VERIFY_TOKEN'
    ]

    results = {}
    for var in required_vars:
        if os.getenv(var):
            results[var] = "✅ set"
        else:
            results[var] = "❌ missing"

    return results

def check_paths():
    """Check if paths are set up correctly."""
    results = {}

    python_path = os.getenv('PYTHONPATH')
    results["PYTHONPATH"] = python_path or "❌ not set"

    # Add agents/src to path like the main app does
    agents_src_path = Path(__file__).parent / "agents" / "src"
    if agents_src_path.exists():
        results["agents_src_exists"] = "✅ exists"
        sys.path.insert(0, str(agents_src_path))
        results["agents_src_added_to_path"] = "✅ added to sys.path"
    else:
        results["agents_src_exists"] = f"❌ not found at {agents_src_path}"

    return results

def test_webhook_import():
    """Test importing the webhook module."""
    try:
        from autifyme_agents.entrypoints.whatsapp_webhook import app as webhook_app
        return "✅ imported successfully"
    except Exception as e:
        return f"❌ failed: {e}"

def test_runner_initialization():
    """Test WorkflowRunner initialization."""
    try:
        from autifyme_agents.entrypoints.whatsapp_webhook import _get_runner
        runner = _get_runner()
        return "✅ initialized successfully"
    except Exception as e:
        return f"❌ failed: {e}"

@app.get("/debug")
async def debug_endpoint():
    """Debug endpoint that runs all diagnostic checks."""
    results = {
        "status": "running_diagnostics",
        "python_version": sys.version,
        "platform": sys.platform,
        "working_directory": os.getcwd(),
        "environment_variables": check_environment(),
        "imports": check_imports(),
        "paths": check_paths()
    }

    # Only test webhook import if paths are OK
    if "✅ added to sys.path" in str(results["paths"]):
        results["webhook_import"] = test_webhook_import()
        results["runner_initialization"] = test_runner_initialization()
    else:
        results["webhook_import"] = "❌ skipped - path issues"
        results["runner_initialization"] = "❌ skipped - path issues"

    return JSONResponse(content=results)

@app.get("/health")
async def health_check():
    """Simple health check."""
    return {"status": "healthy", "service": "vercel-debug"}
