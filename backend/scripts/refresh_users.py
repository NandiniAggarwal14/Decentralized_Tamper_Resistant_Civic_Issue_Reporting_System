"""
refresh_users.py
----------------
Utility script to wipe all non-admin user accounts from the database.

Deletes:
  - government_personnel (personnel profiles for ward/authority users)
  - All users whose role is NOT 'admin'
  - Resets ward_member_id to NULL on all wards

Preserves:
  - Admin accounts
  - Wards, departments, category maps
  - Issues (issues will lose their user_id FK link — columns become NULL)

Usage:
    python -m backend.scripts.refresh_users
"""
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.database import get_connection


def main() -> None:
    print("=" * 55)
    print("  NON-ADMIN USER DATA PURGE")
    print("=" * 55)
    print("WARNING: This will permanently delete ALL citizen,")
    print("         ward_member, and authority accounts.")
    print("         Admin accounts will be preserved.")
    print()

    confirm = input("Type 'yes' to confirm: ").strip().lower()
    if confirm != "yes":
        print("Aborted. No data was deleted.")
        sys.exit(0)

    with get_connection() as conn:
        with conn.cursor() as cur:
            # 1. Unassign ward members from all wards
            cur.execute("UPDATE wards SET ward_member_id = NULL;")
            print("  [OK] Unassigned all ward members from wards")

            # 2. Remove government_personnel entries for non-admin users
            cur.execute("""
                DELETE FROM government_personnel
                WHERE user_id IN (
                    SELECT id FROM users WHERE role != 'admin'
                );
            """)
            print("  [OK] Removed government personnel profiles")

            # 3. Remove all non-admin users
            cur.execute("DELETE FROM users WHERE role != 'admin' RETURNING username, role;")
            deleted = cur.fetchall()
            for u in deleted:
                print(f"  [OK] Deleted user: {u['username']} ({u['role']})")

            if not deleted:
                print("  [INFO] No non-admin users found.")

        conn.commit()

    print()
    print(f"Purged {len(deleted)} user account(s).")
    print("Admin accounts, wards, and departments remain intact.")


if __name__ == "__main__":
    main()
