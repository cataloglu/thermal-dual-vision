"""
Camera service for Smart Motion Detector v2.

This service handles RTSP camera connections, snapshot capture,
and connection testing with proper error handling and retry logic.
"""
import base64
import logging
import time
import os
from typing import Dict, Optional

import cv2
import numpy as np


logger = logging.getLogger(__name__)


class CameraService:
    """Service for camera operations."""
    
    # RTSP connection settings
    DEFAULT_TIMEOUT = 10  # seconds
    MAX_RETRY_ATTEMPTS = 3
    RETRY_DELAYS = [1, 2, 4]  # Exponential backoff in seconds
    
    # OpenCV settings
    BUFFER_SIZE = 1  # Low latency
    JPEG_QUALITY = 85  # Snapshot quality
    
    @staticmethod
    def force_tcp_protocol(url: str) -> str:
        """
        Configure RTSP transport protocol.
        """
        # NOTE: We disabled forced TCP appending because cv2/ffmpeg handles
        # negotiation better automatically, and some servers reject explicit ?tcp
        return url
    
    def test_rtsp_connection(
        self,
        url: str,
        timeout: int = DEFAULT_TIMEOUT
    ) -> Dict[str, any]:
        """
        Test RTSP connection and capture snapshot.
        
        Implements retry logic with exponential backoff.
        Measures connection latency.
        
        Args:
            url: RTSP URL to test
            timeout: Connection timeout in seconds
            
        Returns:
            Dict containing:
                - success (bool): Connection success status
                - snapshot_base64 (str): Base64 encoded JPEG snapshot
                - latency_ms (int): Connection latency in milliseconds
                - error_reason (str): Error message if failed
        """
            # Force TCP protocol (Disabled for compatibility)
        # url = self.force_tcp_protocol(url)
        
        logger.info(f"Testing RTSP connection: {url}")
        
        # Retry loop
        for attempt in range(self.MAX_RETRY_ATTEMPTS):
            try:
                # Measure latency
                start_time = time.time()
                
                # Open video capture
                # Set FFMPEG timeout via env var for this thread/process
                os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "timeout;5000"
                
                cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
                
                # Optimization: Set smaller buffer
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                
                if not cap.isOpened():
                    raise ConnectionError("Failed to open video capture")
                
                # Read frame with timeout
                ret, frame = cap.read()
                
                if not ret or frame is None:
                    cap.release()
                    raise ValueError("Failed to read frame from camera")
                
                # Calculate latency
                latency_ms = int((time.time() - start_time) * 1000)
                
                # Optimization: Resize for snapshot if too large (save bandwidth)
                if frame.shape[1] > 1280:
                    height = int(frame.shape[0] * 1280 / frame.shape[1])
                    frame = cv2.resize(frame, (1280, height))
                
                # Encode frame to JPEG
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.JPEG_QUALITY]
                ret, buffer = cv2.imencode('.jpg', frame, encode_param)
                
                if not ret:
                    cap.release()
                    raise ValueError("Failed to encode frame to JPEG")
                
                # Convert to base64
                jpg_as_text = base64.b64encode(buffer).decode('utf-8')
                snapshot_base64 = f"data:image/jpeg;base64,{jpg_as_text}"
                
                # Clean up
                cap.release()
                
                logger.info(f"RTSP connection successful: {url} (latency: {latency_ms}ms)")
                
                return {
                    "success": True,
                    "snapshot_base64": snapshot_base64,
                    "latency_ms": latency_ms,
                    "error_reason": None
                }
                
            except Exception as e:
                logger.warning(
                    f"RTSP connection attempt {attempt + 1}/{self.MAX_RETRY_ATTEMPTS} failed: "
                    f"{url} - {str(e)}"
                )
                
                # Release capture if it was opened
                try:
                    if 'cap' in locals():
                        cap.release()
                except:
                    pass
                
                # If not last attempt, wait before retry
                if attempt < self.MAX_RETRY_ATTEMPTS - 1:
                    delay = self.RETRY_DELAYS[attempt]
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    # Last attempt failed
                    error_msg = f"Connection failed after {self.MAX_RETRY_ATTEMPTS} attempts: {str(e)}"
                    logger.error(f"RTSP connection failed: {url} - {error_msg}")
                    
                    return {
                        "success": False,
                        "snapshot_base64": None,
                        "latency_ms": None,
                        "error_reason": error_msg
                    }
        
        # Should never reach here, but just in case
        return {
            "success": False,
            "snapshot_base64": None,
            "latency_ms": None,
            "error_reason": "Unknown error"
        }
    
    def test_dual_camera(
        self,
        thermal_url: str,
        color_url: str,
        timeout: int = DEFAULT_TIMEOUT
    ) -> Dict[str, any]:
        """
        Test dual camera setup (thermal + color).
        
        Tests both channels and returns thermal snapshot as primary.
        
        Args:
            thermal_url: RTSP URL for thermal camera
            color_url: RTSP URL for color camera
            timeout: Connection timeout in seconds
            
        Returns:
            Dict containing test results (thermal snapshot returned)
        """
        logger.info("Testing dual camera setup")
        
        # Test thermal camera
        thermal_result = self.test_rtsp_connection(thermal_url, timeout)
        
        if not thermal_result["success"]:
            return {
                "success": False,
                "snapshot_base64": None,
                "latency_ms": None,
                "error_reason": f"Thermal camera failed: {thermal_result['error_reason']}"
            }
        
        # Test color camera
        color_result = self.test_rtsp_connection(color_url, timeout)
        
        if not color_result["success"]:
            return {
                "success": False,
                "snapshot_base64": None,
                "latency_ms": None,
                "error_reason": f"Color camera failed: {color_result['error_reason']}"
            }
        
        # Both cameras successful - combine snapshots side by side
        logger.info("Dual camera test successful, combining snapshots")
        
        try:
            # Decode base64 images
            thermal_b64 = thermal_result["snapshot_base64"].split(',')[1]
            color_b64 = color_result["snapshot_base64"].split(',')[1]
            
            thermal_bytes = base64.b64decode(thermal_b64)
            color_bytes = base64.b64decode(color_b64)
            
            # Convert to numpy arrays
            thermal_arr = np.frombuffer(thermal_bytes, dtype=np.uint8)
            color_arr = np.frombuffer(color_bytes, dtype=np.uint8)
            
            thermal_img = cv2.imdecode(thermal_arr, cv2.IMREAD_COLOR)
            color_img = cv2.imdecode(color_arr, cv2.IMREAD_COLOR)
            
            # Resize to same height if needed
            h1, w1 = thermal_img.shape[:2]
            h2, w2 = color_img.shape[:2]
            
            target_height = min(h1, h2)
            thermal_resized = cv2.resize(thermal_img, (int(w1 * target_height / h1), target_height))
            color_resized = cv2.resize(color_img, (int(w2 * target_height / h2), target_height))
            
            # Combine side by side (thermal left, color right)
            combined = np.hstack([thermal_resized, color_resized])
            
            # Add labels
            cv2.putText(combined, "THERMAL", (20, 40), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
            cv2.putText(combined, "COLOR", (thermal_resized.shape[1] + 20, 40), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
            
            # Encode combined image
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.JPEG_QUALITY]
            ret, buffer = cv2.imencode('.jpg', combined, encode_param)
            
            if not ret:
                raise ValueError("Failed to encode combined image")
            
            # Convert to base64
            combined_b64 = base64.b64encode(buffer).decode('utf-8')
            combined_snapshot = f"data:image/jpeg;base64,{combined_b64}"
            
            return {
                "success": True,
                "snapshot_base64": combined_snapshot,
                "latency_ms": max(thermal_result["latency_ms"], color_result["latency_ms"]),
                "error_reason": None
            }
            
        except Exception as e:
            logger.error(f"Failed to combine dual camera snapshots: {e}")
            # Fallback to thermal only
            return {
                "success": True,
                "snapshot_base64": thermal_result["snapshot_base64"],
                "latency_ms": thermal_result["latency_ms"],
                "error_reason": None
            }


# Global singleton instance
_camera_service: Optional[CameraService] = None


def get_camera_service() -> CameraService:
    """
    Get or create the global camera service instance.
    
    Returns:
        CameraService: Global camera service instance
    """
    global _camera_service
    if _camera_service is None:
        _camera_service = CameraService()
    return _camera_service
