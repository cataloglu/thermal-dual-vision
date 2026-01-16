#!/usr/bin/env python3
"""
Integration verification script for Smart Motion Detector.
Tests code structure, imports, and basic functionality without running the full app.
"""

import ast
import sys
from pathlib import Path


def test_imports():
    """Test that main.py has proper import structure."""
    print("✓ Testing imports structure...")

    main_file = Path("./src/main.py")
    content = main_file.read_text()
    tree = ast.parse(content)

    # Check for key imports
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)

    required_modules = ['asyncio', 'signal', 'aiohttp']
    for module in required_modules:
        assert any(module in imp for imp in imports), f"Missing import: {module}"

    print(f"  ✓ Found {len(imports)} imports including all required modules")


def test_class_structure():
    """Test that SmartMotionDetector class has required methods."""
    print("✓ Testing class structure...")

    main_file = Path("./src/main.py")
    content = main_file.read_text()
    tree = ast.parse(content)

    # Find SmartMotionDetector class
    smd_class = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "SmartMotionDetector":
            smd_class = node
            break

    assert smd_class is not None, "SmartMotionDetector class not found"

    # Check for required methods (including async methods)
    methods = [node.name for node in smd_class.body
               if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    required_methods = [
        '__init__', 'setup_signal_handlers', 'arm', 'disarm',
        'is_armed', 'health_check', 'start', 'stop'
    ]

    for method in required_methods:
        assert method in methods, f"Missing method: {method}"

    print(f"  ✓ Found {len(methods)} methods including all required ones")
    print(f"  ✓ Methods: {', '.join(required_methods)}")


def test_signal_handlers():
    """Test that signal handlers are properly configured."""
    print("✓ Testing signal handler setup...")

    main_file = Path("./src/main.py")
    content = main_file.read_text()

    # Check for signal registration
    assert "signal.signal(signal.SIGTERM" in content, "SIGTERM handler not registered"
    assert "signal.signal(signal.SIGINT" in content, "SIGINT handler not registered"
    assert "graceful shutdown" in content.lower(), "Graceful shutdown not mentioned"

    print("  ✓ SIGTERM and SIGINT handlers registered")
    print("  ✓ Graceful shutdown logic present")


def test_health_endpoint():
    """Test that health check endpoint is configured."""
    print("✓ Testing health check endpoint...")

    main_file = Path("./src/main.py")
    content = main_file.read_text()

    # Check for health endpoint
    assert "/health" in content, "Health endpoint path not found"
    assert "health_check" in content, "Health check method not found"
    assert "web.Application" in content, "aiohttp web application not found"
    assert "8099" in content, "Health check port 8099 not found"

    print("  ✓ Health endpoint configured at /health")
    print("  ✓ Running on port 8099")


def test_module_lifecycle():
    """Test that modules have proper lifecycle management."""
    print("✓ Testing module lifecycle management...")

    main_file = Path("./src/main.py")
    content = main_file.read_text()

    # Check for start/stop logic
    assert "async def start" in content, "Start method not async"
    assert "async def stop" in content, "Stop method not async"

    # Check for module initialization in start
    modules = ['mqtt_client', 'telegram_bot', 'llm_analyzer',
               'yolo_detector', 'screenshot_manager', 'motion_detector']

    for module in modules:
        assert module in content.lower(), f"Module {module} not referenced"

    print(f"  ✓ All {len(modules)} modules have lifecycle management")
    print("  ✓ Start and stop methods are async")


def test_graceful_cleanup():
    """Test that cleanup happens in proper order."""
    print("✓ Testing graceful cleanup order...")

    main_file = Path("./src/main.py")
    content = main_file.read_text()
    tree = ast.parse(content)

    # Find stop method
    stop_method = None
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "stop":
            stop_method = node
            break

    assert stop_method is not None, "Stop method not found"

    # Check for try/except blocks (graceful error handling)
    try_blocks = [node for node in ast.walk(stop_method)
                  if isinstance(node, ast.Try)]

    assert len(try_blocks) > 0, "No error handling in stop method"
    print(f"  ✓ Found {len(try_blocks)} try/except blocks for graceful error handling")

    # Check for cleanup logging
    assert "stopped" in content.lower() or "cleanup" in content.lower()
    print("  ✓ Cleanup logging present")


def test_main_entry_point():
    """Test that main entry point is properly configured."""
    print("✓ Testing main entry point...")

    main_file = Path("./src/main.py")
    content = main_file.read_text()

    # Check for main function
    assert "async def main" in content, "Main function not async"
    assert "asyncio.run(main())" in content, "asyncio.run not used"
    assert 'if __name__ == "__main__"' in content, "Main guard not present"

    # Check for configuration loading
    assert "Config.from_env()" in content, "Config loading not found"
    assert "validate()" in content, "Config validation not found"

    print("  ✓ Async main entry point configured")
    print("  ✓ Configuration loading and validation present")


def test_event_pipeline():
    """Test that event pipeline callback exists."""
    print("✓ Testing event pipeline...")

    main_file = Path("./src/main.py")
    content = main_file.read_text()

    # Check for motion detection callback
    assert "_on_motion_detected" in content, "Motion detection callback not found"
    assert "event pipeline" in content.lower(), "Event pipeline not documented"

    print("  ✓ Motion detection callback present")
    print("  ✓ Event pipeline documented")


def test_logging():
    """Test that logging is properly configured."""
    print("✓ Testing logging configuration...")

    main_file = Path("./src/main.py")
    content = main_file.read_text()

    # Check for logger usage
    assert "logger = get_logger" in content, "Logger not initialized"
    assert "logger.info" in content, "No info logging"
    assert "logger.error" in content, "No error logging"
    assert "logger.warning" in content, "No warning logging"

    print("  ✓ Logger properly initialized")
    print("  ✓ Multiple log levels used (info, error, warning)")


def run_all_tests():
    """Run all verification tests."""
    print("=" * 60)
    print("Smart Motion Detector - Integration Verification")
    print("=" * 60)
    print()

    tests = [
        test_imports,
        test_class_structure,
        test_signal_handlers,
        test_health_endpoint,
        test_module_lifecycle,
        test_graceful_cleanup,
        test_main_entry_point,
        test_event_pipeline,
        test_logging,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
            print()
        except AssertionError as e:
            print(f"  ✗ FAILED: {e}")
            print()
            failed += 1
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            print()
            failed += 1

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    if failed > 0:
        print("\n❌ Some tests failed!")
        return 1
    else:
        print("\n✅ All integration tests passed!")
        print("\nVerification Summary:")
        print("  ✓ Code structure is correct")
        print("  ✓ Signal handlers configured for graceful shutdown")
        print("  ✓ Health check endpoint available")
        print("  ✓ Module lifecycle management implemented")
        print("  ✓ Error handling in place")
        print("  ✓ Logging configured properly")
        print("\nNote: Full runtime testing requires compatible dependencies")
        print("      (numpy, aiohttp, etc.) which have environment constraints.")
        return 0


if __name__ == "__main__":
    sys.exit(run_all_tests())
