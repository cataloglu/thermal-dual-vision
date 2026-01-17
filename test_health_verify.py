#!/usr/bin/env python3
"""Verification test for health_check() method."""

# Read the main.py file
with open('./src/main.py', 'r') as f:
    content = f.read()

# Check that health_check() method exists and is async
assert 'async def health_check(self) -> Dict[str, Any]:' in content, "health_check() method not found or not properly typed"
print("✓ health_check() method found with correct signature")

# Check that it returns a dict with 'status' key
assert '"status": "ok"' in content or "'status': 'ok'" in content, "health_check() doesn't initialize status key"
print("✓ health_check() initializes 'status' key")

# Check that it returns health dict
health_check_start = content.index('async def health_check(self)')
health_check_end = content.index('async def start(self)', health_check_start)
health_check_body = content[health_check_start:health_check_end]

assert 'return health' in health_check_body, "health_check() doesn't return health dict"
print("✓ health_check() returns health dict")

# Check for module checks
assert '"modules"' in health_check_body, "health_check() doesn't check modules"
print("✓ health_check() checks modules")

# Check for various module types
assert 'mqtt' in health_check_body, "health_check() doesn't check MQTT"
assert 'telegram' in health_check_body, "health_check() doesn't check Telegram"
assert 'llm' in health_check_body, "health_check() doesn't check LLM"
assert 'yolo' in health_check_body, "health_check() doesn't check YOLO"
assert 'motion' in health_check_body, "health_check() doesn't check Motion"
print("✓ health_check() checks all expected modules")

print("\nOK")
