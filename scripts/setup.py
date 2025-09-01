#!/usr/bin/env python3
"""
Setup script for AutifyME development environment
"""
import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd: str, description: str):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e.stderr}")
        sys.exit(1)

def main():
    """Setup AutifyME development environment"""
    print("🚀 Setting up AutifyME development environment...")
    
    # Check if uv is installed
    try:
        subprocess.run(["uv", "--version"], check=True, capture_output=True)
        print("✅ uv is already installed")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("📦 Installing uv...")
        run_command("pip install uv", "Installing uv")
        print("⚠️  You may need to restart your terminal or add uv to PATH")
    
    # Sync dependencies (creates venv and installs everything)
    run_command("uv sync", "Installing all dependencies with uv")
    
    # Create .env file if it doesn't exist
    if not Path(".env").exists():
        run_command("cp .env.example .env", "Creating .env file")
        print("📝 Please edit .env file with your API keys")
    
    print("\n🎉 Setup complete!")
    print("\nNext steps:")
    print("1. Edit .env file with your API keys")
    print("2. Run: uv run python -m src.workflows.cataloging")
    print("3. Start developing!")

if __name__ == "__main__":
    main()