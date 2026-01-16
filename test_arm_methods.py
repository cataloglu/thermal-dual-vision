#!/usr/bin/env python3
"""Test arm(), disarm(), and is_armed() methods."""

from src.main import SmartMotionDetector
from src.config import Config

# Create app instance
app = SmartMotionDetector(Config())

# Test arm()
app.arm()
assert app.is_armed(), "Expected is_armed() to return True after arm()"

# Test disarm()
app.disarm()
assert not app.is_armed(), "Expected is_armed() to return False after disarm()"

print("OK")
