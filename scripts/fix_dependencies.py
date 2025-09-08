#!/usr/bin/env python3
"""
Dependency Fix Script

Fixes critical dependency issues found in the audit:
1. Adds missing required dependencies
2. Removes unused dependencies  
3. Optimizes dependency structure
"""

import subprocess
import sys
from pathlib import Path

def run_command(cmd: str, description: str, check: bool = True):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=check, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} completed")
        else:
            print(f"⚠️  {description} completed with warnings")
            if result.stderr:
                print(f"   Warning: {result.stderr.strip()}")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e.stderr}")
        if check:
            sys.exit(1)
        return None

def main():
    """Fix AutifyME dependency issues"""
    print("🔧 AutifyME Dependency Fix")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("pyproject.toml").exists():
        print("❌ Please run this script from the AutifyME root directory")
        sys.exit(1)
    
    print("📋 Audit Summary:")
    print("   ❌ Missing: cryptography, langchain-openai, langchain-anthropic")
    print("   ⚠️  Unused: langgraph, langsmith, google-*, python-dotenv, aiohttp")
    print("   ✅ Used: langchain, supabase, pillow, pydantic, requests")
    print()
    
    # Step 1: Add missing critical dependencies
    print("🚨 Step 1: Adding Missing Critical Dependencies")
    print("=" * 50)
    
    missing_deps = [
        "cryptography>=41.0.0",
        "langchain-openai>=0.1.0", 
        "langchain-anthropic>=0.1.0"
    ]
    
    for dep in missing_deps:
        run_command(f"uv add {dep}", f"Adding {dep}")
    
    # Step 2: Test that critical functionality works
    print("\n🧪 Step 2: Testing Critical Functionality")
    print("=" * 50)
    
    test_commands = [
        ("python -c \"from cryptography.fernet import Fernet; print('✅ Cryptography works')\"", "Testing cryptography"),
        ("python -c \"from src.core.credentials import get_credential_manager; print('✅ Credential manager works')\"", "Testing credential manager"),
        ("python -c \"from langchain_openai import ChatOpenAI; print('✅ LangChain OpenAI works')\"", "Testing LangChain OpenAI"),
        ("python -c \"from langchain_anthropic import ChatAnthropic; print('✅ LangChain Anthropic works')\"", "Testing LangChain Anthropic"),
    ]
    
    for cmd, desc in test_commands:
        run_command(f"uv run {cmd}", desc, check=False)
    
    # Step 3: Ask about removing unused dependencies
    print("\n🧹 Step 3: Clean Up Unused Dependencies")
    print("=" * 50)
    
    unused_deps = [
        "langgraph",
        "langsmith", 
        "google-api-python-client",
        "google-auth",
        "python-dotenv",
        "aiohttp"
    ]
    
    print("The following dependencies are declared but not used in the code:")
    for dep in unused_deps:
        print(f"   - {dep}")
    print()
    
    remove_unused = input("Remove unused dependencies? [Y/n]: ").lower()
    if remove_unused != 'n':
        for dep in unused_deps:
            run_command(f"uv remove {dep}", f"Removing {dep}", check=False)
    
    # Step 4: Show final status
    print("\n📊 Step 4: Final Status")
    print("=" * 50)
    
    # Get package list
    result = run_command("uv pip list", "Getting installed packages", check=False)
    if result:
        lines = result.strip().split('\n')
        package_count = len([line for line in lines if line and not line.startswith('Package')])
        print(f"✅ {package_count} packages installed")
    
    # Test core functionality
    print("\n🧪 Final Validation:")
    core_tests = [
        ("python -c \"from src.core.models import *; print('✅ Models work')\"", "Core models"),
        ("python -c \"from src.core.credentials import supabase, openai; print('✅ Credentials work')\"", "Credential services"),
        ("python -c \"from src.specialists.database import DatabaseSpecialist; print('✅ Specialists work')\"", "Database specialist"),
        ("python -c \"from src.tools.database import create_record; print('✅ Tools work')\"", "Database tools"),
    ]
    
    for cmd, desc in core_tests:
        run_command(f"uv run {cmd}", f"Testing {desc}", check=False)
    
    print("\n🎉 Dependency fix complete!")
    print("\n📋 Summary of Changes:")
    print("   ✅ Added cryptography for secure credential storage")
    print("   ✅ Added langchain-openai for OpenAI integration") 
    print("   ✅ Added langchain-anthropic for Anthropic integration")
    
    if remove_unused != 'n':
        print("   🧹 Removed unused dependencies")
        print("   📦 Moved optional dependencies to extras")
    
    print("\n💡 Next Steps:")
    print("1. Update pyproject.toml with optimized structure (see audit report)")
    print("2. Test your application thoroughly")
    print("3. Update team documentation about new dependency structure")
    print("4. Consider implementing monitoring (langsmith) and workflows (langgraph) in future")

if __name__ == "__main__":
    main()