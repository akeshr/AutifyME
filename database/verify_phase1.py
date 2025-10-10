"""Verify Phase 1 integration - check if outcomes are being tracked.

Usage:
    uv run python database/verify_phase1.py
"""

import sys
from pathlib import Path
from dotenv import load_dotenv
import os

# Load environment
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env")

def verify_phase1():
    """Verify Phase 1 integration is working."""
    print("\n" + "="*60)
    print("Phase 1 Integration Verification")
    print("="*60 + "\n")

    try:
        import psycopg
    except ImportError:
        print("ERROR: psycopg not installed")
        sys.exit(1)

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not found")
        sys.exit(1)

    print("Connecting to database...")

    try:
        with psycopg.connect(db_url, connect_timeout=5) as conn:
            print("Connected!\n")

            # Check tables exist
            print("1. Checking tables...")
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                      AND table_name IN ('workflow_outcomes', 'routing_history')
                    ORDER BY table_name
                """)
                tables = [row[0] for row in cur.fetchall()]

                if 'workflow_outcomes' in tables:
                    print("   [OK] workflow_outcomes table exists")
                else:
                    print("   [FAIL] workflow_outcomes table missing!")
                    return False

                if 'routing_history' in tables:
                    print("   [OK] routing_history table exists")
                else:
                    print("   [FAIL] routing_history table missing!")
                    return False

            # Check views exist
            print("\n2. Checking views...")
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT table_name
                    FROM information_schema.views
                    WHERE table_schema = 'public'
                      AND table_name LIKE 'v_%'
                    ORDER BY table_name
                """)
                views = [row[0] for row in cur.fetchall()]

                expected_views = ['v_success_rates', 'v_recent_failures', 'v_edge_cases']
                for view in expected_views:
                    if view in views:
                        print(f"   [OK] {view} view exists")
                    else:
                        print(f"   [FAIL] {view} view missing!")
                        return False

            # Check workflow_outcomes structure
            print("\n3. Checking workflow_outcomes structure...")
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'workflow_outcomes'
                    ORDER BY ordinal_position
                """)
                columns = [row[0] for row in cur.fetchall()]

                required_columns = [
                    'id', 'tracking_id', 'thread_id', 'sender_id',
                    'message_text', 'message_hash', 'success',
                    'duration_seconds', 'created_at'
                ]

                for col in required_columns:
                    if col in columns:
                        print(f"   [OK] {col} column exists")
                    else:
                        print(f"   [FAIL] {col} column missing!")
                        return False

            # Check if any data was tracked
            print("\n4. Checking for tracked workflows...")
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM workflow_outcomes")
                count = cur.fetchone()[0]

                if count > 0:
                    print(f"   [OK] Found {count} tracked workflow(s)")

                    # Show latest
                    cur.execute("""
                        SELECT tracking_id, sender_id, success, created_at
                        FROM workflow_outcomes
                        ORDER BY created_at DESC
                        LIMIT 1
                    """)
                    row = cur.fetchone()
                    print(f"\n   Latest tracked workflow:")
                    print(f"     Tracking ID: {row[0]}")
                    print(f"     Sender: {row[1]}")
                    print(f"     Success: {row[2]}")
                    print(f"     Tracked at: {row[3]}")
                else:
                    print("   [INFO] No workflows tracked yet (run a test to generate data)")

            print("\n" + "="*60)
            print("Phase 1 Integration: VERIFIED")
            print("="*60 + "\n")
            return True

    except psycopg.OperationalError as e:
        print(f"\nERROR: Database connection failed:")
        print(f"  {e}")
        return False
    except Exception as e:
        print(f"\nERROR: Verification failed:")
        print(f"  {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = verify_phase1()
    sys.exit(0 if success else 1)
