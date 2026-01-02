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

import argparse
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

# Checkpoint tables in order (writes first due to potential future FK constraints)
CHECKPOINT_TABLES = ["checkpoint_writes", "checkpoint_blobs", "checkpoints"]


def get_supabase_client() -> Client:
    """Initialize Supabase client."""
    load_dotenv(project_root / ".env")

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # Need service role for truncate

    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")

    return create_client(url, key)


def get_current_counts(client: Client) -> dict[str, int]:
    """Get current record counts using Supabase client."""
    counts: dict[str, int] = {}

    for table in CHECKPOINT_TABLES:
        result = client.table(table).select("*", count=CountMethod.exact, head=True).execute()
        counts[table] = result.count or 0

    return counts


def run_cleanup(client: Client) -> Any:
    """Execute cleanup via RPC function."""
    result = client.rpc("cleanup_checkpoint_tables").execute()
    return result.data


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Cleanup LangGraph checkpoint tables",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run python scripts/cleanup_checkpoints.py          # Run cleanup
  uv run python scripts/cleanup_checkpoints.py --count  # Show counts only
        """,
    )
    parser.add_argument(
        "--count",
        action="store_true",
        help="Only show current record counts, don't delete",
    )
    return parser.parse_args()


def main() -> int:
    """
    Main entry point - displays counts and requires confirmation.

    Returns exit codes:
        0 - Success
        1 - Aborted by user
        2 - Error
    """
    args = parse_args()

    print("\n" + "=" * 70)
    print("[CRITICAL] CHECKPOINT TABLES CLEANUP")
    print("=" * 70)
    print("\nThis will PERMANENTLY DELETE all data from:")
    for table in CHECKPOINT_TABLES:
        print(f"  - {table}")
    print("\nThis action CANNOT be undone.\n")

    try:
        client = get_supabase_client()
        counts = get_current_counts(client)

        # Show current counts
        print("Current record counts:")
        print("-" * 40)
        total = 0
        for table, count in counts.items():
            print(f"  {table}: {count:,} records")
            total += count
        print("-" * 40)
        print(f"  TOTAL: {total:,} records\n")

        # Count-only mode - exit after showing counts
        if args.count:
            return 0

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
