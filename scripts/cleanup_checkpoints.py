"""
Checkpoint Tables Cleanup Script
================================

Truncates ALL LangGraph checkpoint tables via RPC.

Usage:
  uv run python scripts/cleanup_checkpoints.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

project_root = Path(__file__).parent.parent


def main() -> int:
    """Execute cleanup via RPC function."""
    load_dotenv(project_root / ".env")

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")

    if not url or not key:
        print("ERROR: SUPABASE_URL and SUPABASE_ANON_KEY must be set in .env")
        return 1

    # Call RPC directly via HTTP to avoid Supabase client parsing issues
    response = httpx.post(
        f"{url}/rest/v1/rpc/cleanup_checkpoint_tables",
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        json={},
    )

    if response.status_code == 200:
        result = response.json()
        print("Cleanup complete:")
        print(json.dumps(result, indent=2))
        return 0
    else:
        print(f"ERROR: {response.status_code} - {response.text}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
