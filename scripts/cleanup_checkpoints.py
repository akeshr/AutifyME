"""
Checkpoint Tables Cleanup Script
================================

[CRITICAL] DESTRUCTIVE OPERATION - READ BEFORE RUNNING

This script truncates ALL LangGraph checkpoint tables:
- checkpoint_blobs
- checkpoint_writes
- checkpoints

This action is IRREVERSIBLE. All workflow state, conversation history,
and checkpoint data will be permanently deleted.

-------------------------------------------------------------------------------
CLAUDE CODE GUIDELINES - DO NOT VIOLATE
-------------------------------------------------------------------------------

1. NEVER run this script proactively or as part of any other task
2. ONLY run when user EXPLICITLY asks to "clean checkpoints" or "cleanup checkpoints"
3. ALWAYS ask for confirmation before running, showing current record counts
4. If user says anything other than explicit "yes" or "confirm", ABORT

Example valid triggers:
- "run the cleanup checkpoints script"
- "clean up the checkpoint tables"
- "truncate checkpoints"

Example INVALID triggers (do NOT run):
- "the checkpoints table is getting big" (just informational)
- "we should clean up soon" (not a direct request)
- "delete some old data" (ambiguous)

-------------------------------------------------------------------------------
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from postgrest.types import CountMethod
from supabase import Client, create_client

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "agents" / "src"))


def get_supabase_client() -> Client:
    """Initialize Supabase client."""
    load_dotenv(project_root / ".env")

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # Need service role for truncate

    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")

    return create_client(url, key)


def get_current_counts(client: Client) -> dict[str, int]:
    """Get current record counts for all checkpoint tables."""
    counts: dict[str, int] = {}

    for table in ["checkpoint_blobs", "checkpoint_writes", "checkpoints"]:
        result = client.table(table).select("*", count=CountMethod.exact, head=True).execute()
        counts[table] = result.count or 0

    return counts


def run_cleanup(client: Client) -> Any:
    """Execute the cleanup function via RPC."""
    result = client.rpc("cleanup_checkpoint_tables").execute()
    return result.data


def main() -> int:
    """
    Main entry point - displays counts and requires confirmation.

    Returns exit codes:
        0 - Success
        1 - Aborted by user
        2 - Error
    """
    print("\n" + "=" * 70)
    print("[CRITICAL] CHECKPOINT TABLES CLEANUP")
    print("=" * 70)
    print("\nThis will PERMANENTLY DELETE all data from:")
    print("  - checkpoint_blobs")
    print("  - checkpoint_writes")
    print("  - checkpoints")
    print("\nThis action CANNOT be undone.\n")

    try:
        client = get_supabase_client()

        # Show current counts
        print("Current record counts:")
        print("-" * 40)
        counts = get_current_counts(client)
        total = 0
        for table, count in counts.items():
            print(f"  {table}: {count:,} records")
            total += count
        print("-" * 40)
        print(f"  TOTAL: {total:,} records will be deleted\n")

        if total == 0:
            print("Tables are already empty. Nothing to do.")
            return 0

        # Require explicit confirmation
        print("Type 'DELETE ALL CHECKPOINTS' to confirm (case-sensitive):")
        confirmation = input("> ").strip()

        if confirmation != "DELETE ALL CHECKPOINTS":
            print("\nAborted. Confirmation text did not match.")
            return 1

        # Execute cleanup
        print("\nExecuting cleanup...")
        result = run_cleanup(client)

        print("\n" + "=" * 70)
        print("CLEANUP COMPLETE")
        print("=" * 70)
        print(f"\nResult: {result}")

        return 0

    except Exception as e:
        print(f"\nERROR: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
