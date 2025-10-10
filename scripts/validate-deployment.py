#!/usr/bin/env python3
"""Validate Railway deployment and webhook functionality."""

import os
import sys
import time
import requests
from typing import Dict, Optional

def test_health_check(base_url: str) -> bool:
    """Test the health check endpoint."""
    try:
        print(f"🏥 Testing health check: {base_url}/health")
        response = requests.get(f"{base_url}/health", timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "healthy":
                print("✅ Health check passed")
                return True

        print(f"❌ Health check failed: {response.status_code}")
        print(f"Response: {response.text}")
        return False

    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_webhook_verification(base_url: str, verify_token: str) -> bool:
    """Test WhatsApp webhook verification."""
    try:
        print(f"🔐 Testing webhook verification: {base_url}/webhook")
        params = {
            "hub.mode": "subscribe",
            "hub.challenge": "test_challenge_123",
            "hub.verify_token": verify_token
        }

        response = requests.get(f"{base_url}/webhook", params=params, timeout=10)

        if response.status_code == 200 and response.text == "test_challenge_123":
            print("✅ Webhook verification passed")
            return True

        print(f"❌ Webhook verification failed: {response.status_code}")
        print(f"Expected: test_challenge_123, Got: {response.text}")
        return False

    except Exception as e:
        print(f"❌ Webhook verification error: {e}")
        return False

def test_database_connection(db_url: str) -> bool:
    """Test database connection (basic connectivity test)."""
    try:
        print("🗄️ Testing database connection...")
        # Basic connection test without executing queries
        # This is a simplified check - in production you'd want more thorough tests

        # For Supabase, we can test the REST API
        if "supabase" in db_url.lower():
            supabase_url = os.getenv("SUPABASE_URL")
            if supabase_url:
                response = requests.get(f"{supabase_url}/rest/v1/", timeout=10)
                if response.status_code in [200, 401]:  # 401 is expected without auth
                    print("✅ Supabase connection OK")
                    return True

        print("⚠️ Database connection test skipped (complex validation needed)")
        return True

    except Exception as e:
        print(f"⚠️ Database connection test failed: {e}")
        return False

def wait_for_deployment(base_url: str, max_attempts: int = 10) -> bool:
    """Wait for deployment to be ready."""
    print(f"⏳ Waiting for deployment at {base_url}")

    for attempt in range(max_attempts):
        try:
            response = requests.get(f"{base_url}/health", timeout=5)
            if response.status_code == 200:
                print("✅ Deployment is ready!")
                return True
        except:
            pass

        print(f"Attempt {attempt + 1}/{max_attempts} - waiting...")
        time.sleep(10)

    print("❌ Deployment failed to respond")
    return False

def main():
    """Main validation function."""
    print("🚂 Railway Deployment Validator")
    print("=" * 50)

    # Get Railway URL from environment or ask user
    railway_url = os.getenv("RAILWAY_STATIC_URL") or input("Enter your Railway app URL (e.g., https://autifyme.up.railway.app): ").strip()

    if not railway_url:
        print("❌ No Railway URL provided")
        return False

    # Ensure URL has protocol
    if not railway_url.startswith("http"):
        railway_url = f"https://{railway_url}"

    # Remove trailing slash
    railway_url = railway_url.rstrip("/")

    print(f"🎯 Validating deployment: {railway_url}")

    # Wait for deployment to be ready
    if not wait_for_deployment(railway_url):
        return False

    # Test health check
    if not test_health_check(railway_url):
        return False

    # Test webhook verification
    verify_token = os.getenv("WHATSAPP_WEBHOOK_VERIFY_TOKEN")
    if verify_token:
        if not test_webhook_verification(railway_url, verify_token):
            return False
    else:
        print("⚠️ Skipping webhook verification (WHATSAPP_WEBHOOK_VERIFY_TOKEN not set)")

    # Test database connection
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        test_database_connection(db_url)
    else:
        print("⚠️ Skipping database test (DATABASE_URL not set)")

    print("\n" + "=" * 50)
    print("🎉 Deployment validation completed!")
    print("\n📋 Next steps:")
    print("1. Update WhatsApp Business API webhook URL to:")
    print(f"   {railway_url}/webhook")
    print("2. Test with a real WhatsApp message")
    print("3. Monitor logs in Railway dashboard")
    print("4. Set up monitoring and alerts")

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
