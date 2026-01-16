"""Simple test for health_check method without numpy dependency."""
import sys
import ast

# Read the main.py file and parse it
with open('./src/main.py', 'r') as f:
    tree = ast.parse(f.read())

# Find the SmartMotionDetector class
found_class = False
found_health_check = False
health_check_is_async = False
health_check_has_return_annotation = False

for node in ast.walk(tree):
    if isinstance(node, ast.ClassDef) and node.name == 'SmartMotionDetector':
        found_class = True
        for item in node.body:
            if isinstance(item, ast.AsyncFunctionDef) and item.name == 'health_check':
                found_health_check = True
                health_check_is_async = True
                # Check return annotation
                if item.returns:
                    health_check_has_return_annotation = True
            elif isinstance(item, ast.FunctionDef) and item.name == 'health_check':
                found_health_check = True

assert found_class, "SmartMotionDetector class not found"
assert found_health_check, "health_check method not found in SmartMotionDetector"
assert health_check_is_async, "health_check method should be async"
assert health_check_has_return_annotation, "health_check should have return type annotation"

print("OK - health_check method is properly defined")
print("  - Method is async: ✓")
print("  - Has return type annotation: ✓")
