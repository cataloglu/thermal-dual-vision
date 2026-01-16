"""Test script for health_check method."""
import asyncio
from src.main import SmartMotionDetector
from src.config import Config

async def test_health_check():
    app = SmartMotionDetector(Config())
    health = await app.health_check()
    assert 'status' in health, "Missing 'status' key in health check"
    print('OK')
    return health

if __name__ == "__main__":
    asyncio.run(test_health_check())
