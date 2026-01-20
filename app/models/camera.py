"""
Camera models for Smart Motion Detector v2.

This module contains Pydantic models for camera-related operations.
"""
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


class CameraTestRequest(BaseModel):
    """Request model for camera connection test."""
    
    type: Literal["color", "thermal", "dual"] = Field(
        description="Camera type to test"
    )
    rtsp_url_thermal: Optional[str] = Field(
        default=None,
        description="RTSP URL for thermal camera"
    )
    rtsp_url_color: Optional[str] = Field(
        default=None,
        description="RTSP URL for color camera"
    )
    channel_thermal: Optional[int] = Field(
        default=None,
        description="Thermal camera channel number (e.g., 202)"
    )
    channel_color: Optional[int] = Field(
        default=None,
        description="Color camera channel number (e.g., 102)"
    )
    
    @model_validator(mode='after')
    def validate_urls(self):
        """Validate that required URLs are provided based on camera type."""
        if self.type in ["thermal", "dual"] and not self.rtsp_url_thermal:
            raise ValueError("rtsp_url_thermal is required for thermal or dual camera type")
        
        if self.type in ["color", "dual"] and not self.rtsp_url_color:
            raise ValueError("rtsp_url_color is required for color or dual camera type")
        
        return self


class CameraTestResponse(BaseModel):
    """Response model for camera connection test."""
    
    success: bool = Field(
        description="Whether the test was successful"
    )
    snapshot_base64: Optional[str] = Field(
        default=None,
        description="Base64 encoded snapshot (data:image/jpeg;base64,...)"
    )
    latency_ms: Optional[int] = Field(
        default=None,
        description="Connection latency in milliseconds"
    )
    error_reason: Optional[str] = Field(
        default=None,
        description="Error reason if test failed"
    )
