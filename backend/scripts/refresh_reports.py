"""
refresh_reports.py
------------------
Utility script to wipe all civic report data from the database.

Deletes:
  - issue_votes
  - issue_status_history
  - failed_blockchain_txns
  - issues (CASCADE)

Preserves:
  - users, wards, departments, government_personnel, category_department_map

Usage:
    python -m backend.scripts.refresh_reports
"""
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.database import get_connection


def main() -> None:
    print("=" * 55)
    print("  CIVIC REPORTS DATA PURGE")
    print("=" * 55)
    print("WARNING: This will permanently delete ALL reported issues,")
    print("         votes, status history, and blockchain tx logs.")
    print()

    confirm = input("Type 'yes' to confirm: ").strip().lower()
    if confirm != "yes":
        print("Aborted. No data was deleted.")
        sys.exit(0)

    tables = [
        ("issue_votes",               "Vote records"),
        ("issue_status_history",      "Status audit trail"),
        ("failed_blockchain_txns",    "Failed blockchain transaction queue"),
        ("issues",                    "Issue reports (CASCADE)"),
    ]

    with get_connection() as conn:
        with conn.cursor() as cur:
            for table, label in tables:
                cur.execute(f"DELETE FROM {table};")
                print(f"  [OK] Purged: {label} ({table})")
        conn.commit()

    print()
    print("All report data has been wiped successfully.")
    print("Users, wards, departments, and system config are intact.")


if __name__ == "__main__":
    main()
