"""
Database migration: Add person_count column to events table.
"""
import sqlite3
import sys
from pathlib import Path

def migrate():
    """Add person_count column to events table."""
    
    db_path = Path("/app/data/app.db")
    
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(events)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'person_count' in columns:
            print("✓ person_count column already exists")
            conn.close()
            return True
        
        # Add column
        print("Adding person_count column...")
        cursor.execute("""
            ALTER TABLE events 
            ADD COLUMN person_count INTEGER DEFAULT 1 NOT NULL
        """)
        
        conn.commit()
        conn.close()
        
        print("✓ Migration complete: person_count column added")
        return True
        
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)
