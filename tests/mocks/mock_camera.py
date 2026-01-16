"""Mock camera for testing video feed functionality."""

from typing import Optional, Tuple

import numpy as np


class MockCamera:
    """
    Mock camera that simulates an RTSP video stream for testing.

    Provides controllable fake video frames with options for generating
    frames with and without motion, different resolutions, and error conditions.
    """

    def __init__(
        self,
        width: int = 1280,
        height: int = 720,
        fps: int = 5,
        fail_read: bool = False
    ):
        """
        Initialize mock camera.

        Args:
            width: Frame width in pixels
            height: Frame height in pixels
            fps: Frames per second (stored but not enforced)
            fail_read: If True, read() will return (False, None)
        """
        self.width = width
        self.height = height
        self.fps = fps
        self.fail_read = fail_read
        self._frame_count = 0
        self._is_opened = True

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Read a frame from the mock camera.

        Mimics cv2.VideoCapture.read() behavior.

        Returns:
            Tuple of (success, frame) where:
                - success: bool indicating if frame was read successfully
                - frame: numpy array in BGR format, or None if failed
        """
        if self.fail_read or not self._is_opened:
            return False, None

        # Generate a simple static frame (gray)
        frame = np.ones((self.height, self.width, 3), dtype=np.uint8) * 128
        self._frame_count += 1

        return True, frame

    def generate_motion_frame(
        self,
        motion_type: str = "rectangle",
        motion_color: Tuple[int, int, int] = (255, 255, 255)
    ) -> np.ndarray:
        """
        Generate a frame with simulated motion.

        Creates a frame with a specific pattern or object to simulate
        motion detection scenarios.

        Args:
            motion_type: Type of motion to generate:
                - "rectangle": White rectangle in center
                - "person": Person-shaped blob
                - "gradient": Moving gradient pattern
            motion_color: BGR color for the motion object

        Returns:
            numpy array frame in BGR format with motion
        """
        # Create base frame (dark gray)
        frame = np.ones((self.height, self.width, 3), dtype=np.uint8) * 50

        if motion_type == "rectangle":
            # Draw a rectangle in the center
            x1 = self.width // 3
            y1 = self.height // 3
            x2 = 2 * self.width // 3
            y2 = 2 * self.height // 3
            frame[y1:y2, x1:x2] = motion_color

        elif motion_type == "person":
            # Simulate a person-shaped blob (oval)
            center_x = self.width // 2
            center_y = self.height // 2
            radius_x = self.width // 8
            radius_y = self.height // 4

            y, x = np.ogrid[:self.height, :self.width]
            mask = ((x - center_x) ** 2 / radius_x ** 2 +
                    (y - center_y) ** 2 / radius_y ** 2 <= 1)
            frame[mask] = motion_color

        elif motion_type == "gradient":
            # Create a moving gradient pattern
            offset = (self._frame_count * 10) % self.width
            for i in range(self.width):
                intensity = int(((i + offset) % self.width) / self.width * 255)
                frame[:, i] = [intensity, intensity, intensity]

        return frame

    def release(self) -> None:
        """Release the camera (mimics cv2.VideoCapture.release())."""
        self._is_opened = False

    def isOpened(self) -> bool:
        """Check if camera is opened (mimics cv2.VideoCapture.isOpened())."""
        return self._is_opened

    def set(self, prop_id: int, value: float) -> bool:
        """
        Set camera property (mimics cv2.VideoCapture.set()).

        Args:
            prop_id: Property ID (e.g., cv2.CAP_PROP_FPS)
            value: Value to set

        Returns:
            True if property was set successfully
        """
        # Mock implementation - just return True
        return True

    def get(self, prop_id: int) -> float:
        """
        Get camera property (mimics cv2.VideoCapture.get()).

        Args:
            prop_id: Property ID (e.g., cv2.CAP_PROP_FPS, cv2.CAP_PROP_FRAME_WIDTH)

        Returns:
            Property value as float
        """
        # Mock implementation - return sensible defaults
        # CAP_PROP_FRAME_WIDTH = 3, CAP_PROP_FRAME_HEIGHT = 4, CAP_PROP_FPS = 5
        if prop_id == 3:  # Width
            return float(self.width)
        elif prop_id == 4:  # Height
            return float(self.height)
        elif prop_id == 5:  # FPS
            return float(self.fps)
        return 0.0
