"""Debug script for Vercel deployment issues."""

import sys
import os
from pathlib import Path

def check_imports():
    """Check if all required imports work."""
    try:
        import fastapi
        print("✅ fastapi imported")

        import uvicorn
        print("✅ uvicorn imported")

        import pydantic
        print("✅ pydantic imported")

        import supabase
        print("✅ supabase imported")

        import langchain
        print("✅ langchain imported")

        import langgraph
        print("✅ langgraph imported")

        import deepagents
        print("✅ deepagents imported")

        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def check_environment():
    """Check environment variables."""
    required_vars = [
        'SUPABASE_URL',
        'SUPABASE_ANON_KEY',
        'DATABASE_URL',
        'WHATSAPP_WEBHOOK_VERIFY_TOKEN'
    ]

    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
        else:
            print(f"✅ {var} is set")

    if missing:
        print(f"❌ Missing environment variables: {missing}")
        return False

    return True

def check_paths():
    """Check if paths are set up correctly."""
    python_path = os.getenv('PYTHONPATH')
    if python_path:
        print(f"✅ PYTHONPATH: {python_path}")
    else:
        print("❌ PYTHONPATH not set")

    agents_src = Path(__file__).parent / "agents" / "src"
    if agents_src.exists():
        print(f"✅ agents/src exists: {agents_src}")
        sys.path.insert(0, str(agents_src))
        print("✅ Added agents/src to sys.path")
    else:
        print(f"❌ agents/src not found: {agents_src}")
        return False

    return True

def test_webhook_import():
    """Test importing the webhook module."""
    try:
        from autifyme_agents.entrypoints.whatsapp_webhook import app
        print("✅ WhatsApp webhook imported successfully")
        return True
    except Exception as e:
        print(f"❌ WhatsApp webhook import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_initialization():
    """Test WorkflowRunner initialization."""
    try:
        from autifyme_agents.entrypoints.whatsapp_webhook import _get_runner
        runner = _get_runner()
        print("✅ WorkflowRunner initialized successfully")
        return True
    except Exception as e:
        print(f"❌ WorkflowRunner initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all diagnostic checks."""
    print("🔍 Vercel Deployment Diagnostic")
    print("=" * 50)

    print("\n1. Checking imports...")
    imports_ok = check_imports()

    print("\n2. Checking environment variables...")
    env_ok = check_environment()

    print("\n3. Checking paths...")
    paths_ok = check_paths()

    if paths_ok:
        print("\n4. Testing webhook import...")
        webhook_ok = test_webhook_import()

        if webhook_ok:
            print("\n5. Testing WorkflowRunner initialization...")
            init_ok = test_initialization()
        else:
            init_ok = False
    else:
        webhook_ok = False
        init_ok = False

    print("\n" + "=" * 50)
    if imports_ok and env_ok and paths_ok and webhook_ok and init_ok:
        print("🎉 All checks passed! Deployment should work.")
        return True
    else:
        print("❌ Some checks failed. Fix the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
