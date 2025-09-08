#!/usr/bin/env python3
"""
Dependency Cleanup Script

Removes unused dependencies and optimizes the AutifyME installation.
Run this after the dependency audit to clean up your environment.
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
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e.stderr}")
        if check:
            sys.exit(1)
        return None

def main():
    """Clean up AutifyME dependencies"""
    print("🧹 AutifyME Dependency Cleanup")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("pyproject.toml").exists():
        print("❌ Please run this script from the AutifyME root directory")
        sys.exit(1)
    
    # Remove old lock file to force fresh resolution
    if Path("uv.lock").exists():
        print("🗑️  Removing old lock file...")
        Path("uv.lock").unlink()
        print("✅ Old lock file removed")
    
    # Sync with new dependencies
    run_command("uv sync", "Installing core dependencies")
    
    # Install LLM providers (most users will need at least OpenAI)
    print("\n📦 Optional Dependencies")
    print("=" * 30)
    
    install_llm = input("Install LLM providers (OpenAI, Anthropic, Google)? [Y/n]: ").lower()
    if install_llm != 'n':
        run_command("uv sync --extra llm-providers", "Installing LLM providers")
    
    install_web = input("Install web interface dependencies? [y/N]: ").lower()  
    if install_web == 'y':
        run_command("uv sync --extra web", "Installing web dependencies")
    
    install_data = input("Install data processing dependencies? [y/N]: ").lower()
    if install_data == 'y':
        run_command("uv sync --extra data", "Installing data processing dependencies")
    
    # Always install dev dependencies for development
    run_command("uv sync --extra dev", "Installing development dependencies")
    
    # Show final status
    print("\n📊 Dependency Status")
    print("=" * 30)
    
    # Get package list
    result = run_command("uv pip list", "Getting installed packages", check=False)
    if result:
        lines = result.strip().split('\n')
        package_count = len([line for line in lines if line and not line.startswith('Package')])
        print(f"✅ {package_count} packages installed")
    
    # Show disk usage
    venv_path = Path(".venv")
    if venv_path.exists():
        try:
            import shutil
            size_mb = shutil.disk_usage(venv_path).used / (1024 * 1024)
            print(f"💾 Virtual environment size: ~{size_mb:.0f}MB")
        except:
            print("💾 Virtual environment created")
    
    print("\n🎉 Dependency cleanup complete!")
    print("\nNext steps:")
    print("1. Test your application: uv run python scripts/validate_credentials.py")
    print("2. Run tests: uv run pytest")
    print("3. Start developing with optimized dependencies!")
    
    print("\n💡 Tip: Use 'uv sync --extra <group>' to install optional dependencies later")

if __name__ == "__main__":
    main()