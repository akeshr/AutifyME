"""Database migration runner for AutifyME.

This script applies SQL migrations to the database.

Usage:
    uv run python database/apply_migration.py database/migrations/001_workflow_outcomes.sql
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env")


def apply_migration(migration_file: Path) -> None:
    """Apply a SQL migration file to the database.

    Args:
        migration_file: Path to SQL migration file
    """
    print(f"\n{'=' * 60}")
    print(f"Applying Migration: {migration_file.name}")
    print(f"{'=' * 60}\n")

    # Read migration SQL
    if not migration_file.exists():
        print(f"ERROR: Migration file not found: {migration_file}")
        sys.exit(1)

    sql = migration_file.read_text(encoding="utf-8")
    print(f"Migration size: {len(sql)} characters\n")

    # Connect to database
    try:
        import psycopg
    except ImportError:
        print("ERROR: psycopg not installed. Installing...")
        import subprocess

        subprocess.run([sys.executable, "-m", "pip", "install", "psycopg[binary]"], check=True)
        import psycopg

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not found in environment")
        sys.exit(1)

    print("Connecting to database...")

    try:
        with psycopg.connect(db_url) as conn:
            print("Connected successfully!\n")

            # Check existing tables before migration
            print("Checking existing tables...")
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """)
                tables_before = [row[0] for row in cur.fetchall()]
                print(f"  Found {len(tables_before)} tables")

            # Apply migration
            print("\nApplying migration SQL...")
            with conn.cursor() as cur:
                cur.execute(sql)

            conn.commit()
            print("Migration committed successfully!\n")

            # Check tables after migration
            print("Checking tables after migration...")
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """)
                tables_after = [row[0] for row in cur.fetchall()]
                print(f"  Found {len(tables_after)} tables")

            # Show new tables
            new_tables = set(tables_after) - set(tables_before)
            if new_tables:
                print("\nNew tables created:")
                for table in sorted(new_tables):
                    print(f"  + {table}")

            # Check views created
            print("\nChecking views created...")
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT table_name
                    FROM information_schema.views
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """)
                views = [row[0] for row in cur.fetchall()]
                print(f"  Found {len(views)} views:")
                for view in views:
                    print(f"    - {view}")

            # Verify workflow_outcomes table structure
            print("\nVerifying workflow_outcomes table structure...")
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = 'workflow_outcomes'
                    ORDER BY ordinal_position
                """)
                columns = cur.fetchall()
                print(f"  Columns ({len(columns)}):")
                for col_name, col_type in columns[:10]:  # Show first 10
                    print(f"    - {col_name}: {col_type}")
                if len(columns) > 10:
                    print(f"    ... and {len(columns) - 10} more columns")

            print(f"\n{'=' * 60}")
            print("Migration applied successfully!")
            print(f"{'=' * 60}\n")

    except psycopg.Error as e:
        print("\nERROR: Database error occurred:")
        print(f"  {e}")
        sys.exit(1)
    except Exception as e:
        print("\nERROR: Unexpected error:")
        print(f"  {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nAvailable migrations:")
        migrations_dir = Path(__file__).parent / "migrations"
        if migrations_dir.exists():
            for migration in sorted(migrations_dir.glob("*.sql")):
                print(f"  - {migration.name}")
        sys.exit(1)

    migration_file = Path(sys.argv[1])
    apply_migration(migration_file)


if __name__ == "__main__":
    main()
