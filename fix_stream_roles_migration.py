"""
Database migration: Set stream_roles for cameras with empty/null.
Standalone script - no app imports, safe for run.sh before app starts.
"""
import json
import sqlite3
import sys
from pathlib import Path

DEFAULT_ROLES = ["detect", "live"]


def migrate():
    """Set stream_roles to default for cameras with empty/null."""
    db_path = Path("/app/data/app.db")
    if not db_path.exists():
        return True  # No DB yet, skip
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT id, stream_roles FROM cameras")
        rows = cursor.fetchall()
        updated = 0
        for cam_id, roles_json in rows:
            if roles_json is None or roles_json.strip() in ("", "[]", "null"):
                cursor.execute(
                    "UPDATE cameras SET stream_roles = ? WHERE id = ?",
                    (json.dumps(DEFAULT_ROLES), cam_id),
                )
                updated += 1
            else:
                try:
                    parsed = json.loads(roles_json)
                    if not isinstance(parsed, list) or len(parsed) == 0:
                        cursor.execute(
                            "UPDATE cameras SET stream_roles = ? WHERE id = ?",
                            (json.dumps(DEFAULT_ROLES), cam_id),
                        )
                        updated += 1
                except (json.JSONDecodeError, TypeError):
                    cursor.execute(
                        "UPDATE cameras SET stream_roles = ? WHERE id = ?",
                        (json.dumps(DEFAULT_ROLES), cam_id),
                    )
                    updated += 1
        conn.commit()
        conn.close()
        if updated > 0:
            print(f"Updated {updated}/{len(rows)} cameras (stream_roles)")
        return True
    except Exception as e:
        print(f"Migration skipped: {e}")
        return True  # Don't fail startup


if __name__ == "__main__":
    migrate()
    sys.exit(0)
