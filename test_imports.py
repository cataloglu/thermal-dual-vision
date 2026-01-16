#!/usr/bin/env python3
"""Quick import verification for all optimized components."""

import sys

def test_imports():
    """Test that all components can be imported."""
    errors = []

    tests = [
        ("src.metrics", ["PerformanceMetrics", "MetricsCollector"]),
        ("src.health_endpoint", ["HealthEndpoint"]),
        ("src.motion_detector", ["MotionDetector"]),
        ("src.screenshot_manager", ["ScreenshotManager"]),
        ("src.yolo_detector", ["YOLODetector"]),
        ("src.llm_analyzer", ["LLMAnalyzer"]),
        ("src.mqtt_client", ["MQTTClient"]),
        ("src.telegram_bot", ["TelegramBot"]),
        ("src.config", ["Config", "OptimizationConfig"]),
        ("src.main", ["SmartMotionDetector"]),
    ]

    for module_name, classes in tests:
        try:
            module = __import__(module_name, fromlist=classes)
            for cls in classes:
                if not hasattr(module, cls):
                    errors.append(f"✗ {module_name}.{cls} not found")
                else:
                    print(f"✓ {module_name}.{cls}")
        except Exception as e:
            errors.append(f"✗ {module_name}: {e}")

    if errors:
        print("\nErrors:")
        for error in errors:
            print(error)
        return False

    print("\n✓ All components import successfully!")
    return True

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
