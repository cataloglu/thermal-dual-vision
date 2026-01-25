#!/usr/bin/env python3
"""
Fix stream_roles for existing cameras.
Run this once to update all cameras with missing stream_roles.
"""
import sys
sys.path.insert(0, '/app')

from app.db.session import get_session
from app.db.models import Camera

def fix_stream_roles():
    """Add stream_roles to cameras that don't have it."""
    db = next(get_session())
    try:
        cameras = db.query(Camera).all()
        updated = 0
        
        for camera in cameras:
            # Check if stream_roles is None or empty
            if not camera.stream_roles:
                camera.stream_roles = ["detect", "live"]
                updated += 1
                print(f"✅ Updated camera {camera.id} ({camera.name})")
        
        db.commit()
        print(f"\n🎉 Updated {updated}/{len(cameras)} cameras")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_stream_roles()
