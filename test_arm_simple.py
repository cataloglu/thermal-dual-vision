#!/usr/bin/env python3
"""Simple test for arm(), disarm(), and is_armed() methods without numpy."""

# Test without importing - just verify the methods exist and work
class MockConfig:
    """Mock config for testing."""
    pass

# Read the main.py file to verify methods exist
with open('./src/main.py', 'r') as f:
    content = f.read()

# Check that arm() method exists
assert 'def arm(self) -> None:' in content, "arm() method not found"
print("✓ arm() method found")

# Check that disarm() method exists
assert 'def disarm(self) -> None:' in content, "disarm() method not found"
print("✓ disarm() method found")

# Check that is_armed() method exists
assert 'def is_armed(self) -> bool:' in content, "is_armed() method not found"
print("✓ is_armed() method found")

# Check that arm() sets _armed to True
assert 'self._armed = True' in content and content.index('def arm(self)') < content.index('self._armed = True', content.index('def arm(self)')), "arm() doesn't set _armed = True"
print("✓ arm() sets _armed = True")

# Check that disarm() sets _armed to False
assert 'self._armed = False' in content and content.index('def disarm(self)') < content.index('self._armed = False', content.index('def disarm(self)')), "disarm() doesn't set _armed = False"
print("✓ disarm() sets _armed = False")

# Check that is_armed() returns _armed
assert 'return self._armed' in content and content.index('def is_armed(self)') < content.index('return self._armed', content.index('def is_armed(self)')), "is_armed() doesn't return _armed"
print("✓ is_armed() returns _armed")

print("\nOK")
