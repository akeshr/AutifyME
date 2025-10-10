#!/usr/bin/env python3
"""Check custom domain configuration for Railway deployment."""

import sys
import requests
from typing import Optional

def check_domain_health(domain: str) -> bool:
    """Check if custom domain is properly configured and healthy."""
    # Ensure domain has protocol
    if not domain.startswith("http"):
        domain = f"https://{domain}"

    domain = domain.rstrip("/")

    try:
        print(f"🔍 Checking domain: {domain}")

        # Test health endpoint
        response = requests.get(f"{domain}/health", timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "healthy":
                print("✅ Domain is healthy and responding correctly")
                return True

        print(f"❌ Health check failed: {response.status_code}")
        print(f"Response: {response.text}")
        return False

    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to domain - DNS not configured or Railway deployment not ready")
        return False
    except Exception as e:
        print(f"❌ Domain check error: {e}")
        return False

def check_dns_propagation(domain: str) -> bool:
    """Check if DNS records have propagated."""
    try:
        import socket
        ip = socket.gethostbyname(domain.replace("https://", "").replace("http://", ""))
        print(f"📡 Domain resolves to: {ip}")

        # Railway IPs are typically in these ranges (this is approximate)
        if ip.startswith(("34.", "35.", "36.")):  # Google Cloud ranges where Railway hosts
            print("✅ DNS appears to be pointing to Railway infrastructure")
            return True
        else:
            print("⚠️ DNS points to non-Railway IP - may not be configured correctly")
            return False

    except socket.gaierror:
        print("❌ Domain does not resolve - DNS not configured")
        return False

def test_webhook_endpoints(domain: str) -> bool:
    """Test webhook-related endpoints."""
    if not domain.startswith("http"):
        domain = f"https://{domain}"
    domain = domain.rstrip("/")

    endpoints = [
        ("/health", "Health check"),
        ("/webhook", "Webhook verification (GET)")
    ]

    all_passed = True

    for endpoint, description in endpoints:
        try:
            if endpoint == "/webhook":
                # Test webhook verification with dummy params
                params = {
                    "hub.mode": "subscribe",
                    "hub.challenge": "test123",
                    "hub.verify_token": "dummy_token"
                }
                response = requests.get(f"{domain}{endpoint}", params=params, timeout=10)
            else:
                response = requests.get(f"{domain}{endpoint}", timeout=10)

            if response.status_code == 200:
                print(f"✅ {description}: OK")
            else:
                print(f"⚠️ {description}: {response.status_code}")
                all_passed = False

        except Exception as e:
            print(f"❌ {description}: Failed - {e}")
            all_passed = False

    return all_passed

def main():
    """Main domain verification function."""
    print("🌐 Railway Custom Domain Checker")
    print("=" * 50)

    if len(sys.argv) < 2:
        domain = input("Enter your custom domain (e.g., api.autifyme.com): ").strip()
    else:
        domain = sys.argv[1]

    if not domain:
        print("❌ No domain provided")
        return False

    print(f"🎯 Checking domain: {domain}")
    print()

    # Check DNS propagation
    dns_ok = check_dns_propagation(domain)
    if not dns_ok:
        print("\n❌ DNS configuration issues detected")
        print("Make sure your DNS records point to your Railway app URL")
        return False

    print()

    # Check domain health
    health_ok = check_domain_health(domain)
    if not health_ok:
        print("\n❌ Domain health check failed")
        print("Your Railway deployment may not be ready or domain not properly configured")
        return False

    print()

    # Test webhook endpoints
    webhook_ok = test_webhook_endpoints(domain)

    print("\n" + "=" * 50)

    if health_ok and webhook_ok:
        print("🎉 Custom domain configuration successful!")
        print("\n📋 Next steps:")
        print(f"1. Update WhatsApp Business API webhook URL to: https://{domain}/webhook")
        print("2. Test with a real WhatsApp message")
        print("3. Your domain is production-ready! 🚀")
        return True
    else:
        print("❌ Domain configuration has issues")
        print("\n🔧 Troubleshooting:")
        print("1. Wait 10-15 minutes for DNS propagation")
        print("2. Verify DNS records match Railway instructions")
        print("3. Check Railway deployment is healthy")
        print("4. Ensure domain SSL certificate has been issued")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
