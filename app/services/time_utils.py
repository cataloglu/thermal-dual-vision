"""
Time utilities for Smart Motion Detector v2.

This module provides time-based utilities for auto detection source selection.
"""
from datetime import datetime
from typing import Literal


# Default sunrise and sunset times (configurable)
DEFAULT_SUNRISE_HOUR = 6  # 06:00
DEFAULT_SUNSET_HOUR = 20  # 20:00


def is_daytime(
    sunrise_hour: int = DEFAULT_SUNRISE_HOUR,
    sunset_hour: int = DEFAULT_SUNSET_HOUR
) -> bool:
    """
    Check if current time is daytime.
    
    Args:
        sunrise_hour: Hour when day starts (default: 6)
        sunset_hour: Hour when night starts (default: 20)
        
    Returns:
        True if daytime, False if nighttime
    """
    current_hour = datetime.now().hour
    return sunrise_hour <= current_hour < sunset_hour


def get_detection_source(
    camera_detection_source: str,
    sunrise_hour: int = DEFAULT_SUNRISE_HOUR,
    sunset_hour: int = DEFAULT_SUNSET_HOUR
) -> Literal["color", "thermal"]:
    """
    Get detection source based on camera setting and time.
    
    If camera detection_source is "auto", automatically selects:
    - Color during daytime (better detail)
    - Thermal during nighttime (better visibility)
    
    Args:
        camera_detection_source: Camera's detection source setting
        sunrise_hour: Hour when day starts (default: 6)
        sunset_hour: Hour when night starts (default: 20)
        
    Returns:
        "color" or "thermal"
    """
    if camera_detection_source == "auto":
        if is_daytime(sunrise_hour, sunset_hour):
            return "color"
        else:
            return "thermal"
    
    return camera_detection_source  # type: ignore
