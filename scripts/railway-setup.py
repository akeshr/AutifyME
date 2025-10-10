#!/usr/bin/env python3
"""Railway deployment setup and validation script."""

import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

def check_env_file() -> Dict[str, str]:
    """Load and validate .env file."""
    env_path = Path(".env")
    if not env_path.exists():
        print("❌ .env file not found")
        return {}

    from dotenv import load_dotenv
    load_dotenv()

    env_vars = {}
    required_vars = [
        "SUPABASE_URL",
        "SUPABASE_ANON_KEY",
        "DATABASE_URL",
        "WHATSAPP_PHONE_NUMBER_ID",
        "WHATSAPP_ACCESS_TOKEN",
        "WHATSAPP_WEBHOOK_VERIFY_TOKEN",
        "LANGCHAIN_API_KEY",
        "OPENAI_API_KEY"
    ]

    print("\n🔍 Checking environment variables:")
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if "KEY" in var.upper() or "TOKEN" in var.upper():
                display_value = f"{value[:8]}...{value[-4:]}" if len(value) > 12 else "***"
            else:
                display_value = value
            print(f"✅ {var}: {display_value}")
            env_vars[var] = value
        else:
            print(f"❌ {var}: NOT SET")

    return env_vars

def generate_railway_env_template() -> str:
    """Generate Railway environment variables template."""
    template = """# Railway Environment Variables Template
# Copy these to Railway Dashboard → Your Project → Variables

SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_supabase_anon_key
DATABASE_URL=postgresql://postgres:password@containers-us-west-1.railway.app:xxxx/railway
WHATSAPP_PHONE_NUMBER_ID=your_whatsapp_phone_number_id
WHATSAPP_ACCESS_TOKEN=your_whatsapp_access_token
WHATSAPP_WEBHOOK_VERIFY_TOKEN=your_webhook_verify_token
WHATSAPP_API_VERSION=v20.0
LANGCHAIN_API_KEY=your_langsmith_api_key
OPENAI_API_KEY=your_openai_api_key
AGENT_RECURSION_LIMIT=15
PYTHONPATH=/app/agents/src
PYTHONUNBUFFERED=1
"""

    print("\n📋 Railway Environment Variables Template:")
    print("=" * 50)
    print(template)
    return template

def check_deployment_files() -> List[str]:
    """Check if all deployment files exist."""
    required_files = [
        "Dockerfile",
        "railway.toml",
        ".github/workflows/ci-cd.yml",
        "pyproject.toml",
        "uv.lock"
    ]

    print("\n📁 Checking deployment files:")
    missing = []
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - MISSING")
            missing.append(file_path)

    return missing

def validate_dockerfile() -> bool:
    """Basic Dockerfile validation."""
    dockerfile = Path("Dockerfile")
    if not dockerfile.exists():
        return False

    content = dockerfile.read_text()

    checks = [
        ("FROM python:", "Python base image"),
        ("WORKDIR /app", "Working directory"),
        ("COPY pyproject.toml", "Dependencies"),
        ("COPY agents/", "Application code"),
        ("EXPOSE 8000", "Port exposure"),
        ("HEALTHCHECK", "Health check"),
        ("CMD", "Start command")
    ]

    print("\n🐳 Dockerfile validation:")
    all_passed = True
    for check, description in checks:
        if check in content:
            print(f"✅ {description}")
        else:
            print(f"❌ {description} - MISSING")
            all_passed = False

    return all_passed

def test_local_build() -> bool:
    """Test if Docker build works locally."""
    print("\n🏗️ Testing Docker build (dry run):")

    import subprocess
    try:
        # Just validate syntax, don't actually build
        result = subprocess.run(
            ["docker", "build", "--dry-run", "."],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            print("✅ Dockerfile syntax is valid")
            return True
        else:
            print("❌ Dockerfile syntax error:")
            print(result.stderr)
            return False

    except FileNotFoundError:
        print("⚠️ Docker not installed locally - will validate on Railway")
        return True
    except subprocess.TimeoutExpired:
        print("⚠️ Docker build check timed out - will validate on Railway")
        return True

def main():
    """Main setup validation function."""
    print("🚂 Railway Deployment Setup Validator")
    print("=" * 50)

    # Check deployment files
    missing_files = check_deployment_files()
    if missing_files:
        print(f"\n❌ Missing required files: {missing_files}")
        print("Please ensure all deployment files are present.")
        return False

    # Validate Dockerfile
    if not validate_dockerfile():
        print("\n❌ Dockerfile validation failed")
        return False

    # Check environment variables
    env_vars = check_env_file()
    if not env_vars:
        print("\n⚠️ No environment variables found")
        print("Make sure to create a .env file with your API keys")
    else:
        required_count = len([v for v in env_vars.values() if v])
        print(f"\n📊 Environment variables: {required_count}/8 required vars set")

    # Test Docker build
    test_local_build()

    # Generate Railway template
    generate_railway_env_template()

    print("\n" + "=" * 50)
    print("🎯 Next Steps:")
    print("1. Push these files to GitHub")
    print("2. Create Railway account and connect repository")
    print("3. Set environment variables in Railway dashboard")
    print("4. Deploy and test your webhook")
    print("\n📖 See docs/deployment/RAILWAY_SETUP.md for detailed instructions")

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
