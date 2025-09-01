#!/usr/bin/env python3
"""
Credential Validation Script

Validates all configured credentials and provides setup guidance.
Run this script to check your credential configuration before starting AutifyME.
"""

import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.credentials.credential_manager import CredentialManager


def print_header(title: str):
    """Print a formatted header"""
    print(f"\n{'='*50}")
    print(f" {title}")
    print(f"{'='*50}")


def print_status(item: str, status: bool, details: str = ""):
    """Print status with emoji"""
    emoji = "✅" if status else "❌"
    print(f"{emoji} {item}")
    if details:
        print(f"   {details}")


def validate_credentials():
    """Main credential validation function"""
    print_header("AutifyME Credential Validation")
    
    try:
        # Initialize credential manager
        manager = CredentialManager()
        
        # Check overall status
        available_providers = manager.get_available_providers()
        missing_credentials = manager.get_missing_credentials()
        
        print(f"📊 Found {len(available_providers)} providers with valid credentials")
        print(f"⚠️  Missing {len(missing_credentials)} required credentials")
        
        # Detailed credential status
        print_header("Credential Status")
        
        all_info = manager.get_all_credential_info()
        
        # Group by category
        categories = {
            "AI Providers": ["openai", "anthropic", "google"],
            "Database": ["supabase", "supabase_key"],
            "Storage": ["google_drive", "google_drive_json"],
            "Monitoring": ["langsmith"],
            "Security": ["app_secret"]
        }
        
        for category, providers in categories.items():
            print(f"\n🔧 {category}:")
            for provider in providers:
                if provider in all_info:
                    info = all_info[provider]
                    status = info["loaded"] and info["valid"]
                    details = ""
                    
                    if not info["loaded"]:
                        details = f"Set {info['env_var']} environment variable"
                    elif not info["valid"]:
                        details = "Credential loaded but invalid"
                    else:
                        details = "Ready to use"
                    
                    print_status(f"{provider}: {info['description']}", status, details)
        
        # Missing credentials
        if missing_credentials:
            print_header("Missing Required Credentials")
            print("Please set these environment variables:")
            for missing in missing_credentials:
                print(f"❌ {missing}")
        
        # Setup recommendations
        print_header("Setup Recommendations")
        
        # Check for at least one AI provider
        ai_providers = [p for p in ["openai", "anthropic", "google"] if p in available_providers]
        if not ai_providers:
            print("❌ No AI providers configured!")
            print("   Set at least one: OPENAI_API_KEY, ANTHROPIC_API_KEY, or GOOGLE_API_KEY")
        else:
            print(f"✅ AI providers available: {', '.join(ai_providers)}")
        
        # Check database
        if "supabase" in available_providers and "supabase_key" in available_providers:
            print("✅ Database configured (Supabase)")
        else:
            print("❌ Database not configured!")
            print("   Set SUPABASE_URL and SUPABASE_KEY")
        
        # Check storage
        storage_providers = [p for p in ["google_drive", "google_drive_json"] if p in available_providers]
        if storage_providers:
            print(f"✅ Storage configured: {', '.join(storage_providers)}")
        else:
            print("⚠️  No storage configured (optional)")
            print("   Set GOOGLE_DRIVE_CREDENTIALS_PATH or GOOGLE_DRIVE_CREDENTIALS_JSON")
        
        # Overall readiness
        print_header("System Readiness")
        
        required_for_basic = ["supabase", "supabase_key"] + ai_providers[:1]  # At least one AI provider
        basic_ready = all(p in available_providers for p in required_for_basic)
        
        if basic_ready:
            print("🎉 AutifyME is ready to run!")
            print("   You can start the cataloging workflow.")
        else:
            print("⚠️  AutifyME needs more configuration")
            print("   Set the missing credentials above to get started.")
        
        # Quick start commands
        print_header("Quick Start")
        print("1. Copy environment template:")
        print("   cp .env.example .env")
        print("\n2. Edit .env with your credentials")
        print("\n3. Run this script again to validate:")
        print("   python scripts/validate_credentials.py")
        print("\n4. Start AutifyME:")
        print("   uv run python -m src.workflows.cataloging")
        
        return basic_ready
        
    except Exception as e:
        print(f"❌ Error validating credentials: {e}")
        return False


if __name__ == "__main__":
    success = validate_credentials()
    sys.exit(0 if success else 1)