"""Unit tests for MotionDetector module."""

import time
import threading
from unittest.mock import Mock, MagicMock, patch, call
import numpy as np
import pytest

from src.motion_detector import MotionDetector, map_sensitivity_to_params
from src.config import CameraConfig, MotionConfig


class MockVideoCapture:
    """Mock VideoCapture for testing without real camera."""

    def __init__(self, url, *args, **kwargs):
        """Initialize mock VideoCapture."""
        self.url = url
        self._opened = True
        self._frame_count = 0
        self._should_fail = False
        self._frame_shape = (480, 640, 3)

    def isOpened(self):
        """Check if capture is opened."""
        return self._opened

    def read(self):
        """Read a frame from mock camera."""
        if self._should_fail or not self._opened:
            return False, None

        self._frame_count += 1
        # Create a simple test frame (black image)
        frame = np.zeros(self._frame_shape, dtype=np.uint8)
        return True, frame

    def set(self, prop_id, value):
        """Set VideoCapture property."""
        return True

    def release(self):
        """Release the capture."""
        self._opened = False

    def simulate_disconnect(self):
        """Simulate camera disconnection."""
        self._opened = False

    def simulate_reconnect(self):
        """Simulate camera reconnection."""
        self._opened = True

    def set_fail_mode(self, should_fail):
        """Set whether read() should fail."""
        self._should_fail = should_fail


@pytest.fixture
def mock_cv2():
    """Fixture to mock cv2 module."""
    with patch('src.motion_detector.cv2') as mock:
        # Mock VideoCapture
        mock.VideoCapture = MockVideoCapture

        # Mock BackgroundSubtractor
        mock_subtractor = MagicMock()
        mock_subtractor.apply.return_value = np.zeros((480, 640), dtype=np.uint8)
        mock.createBackgroundSubtractorMOG2.return_value = mock_subtractor

        # Mock other cv2 functions
        mock.getStructuringElement.return_value = np.ones((5, 5), dtype=np.uint8)
        mock.erode.return_value = np.zeros((480, 640), dtype=np.uint8)
        mock.dilate.return_value = np.zeros((480, 640), dtype=np.uint8)
        mock.findContours.return_value = ([], None)
        mock.contourArea.return_value = 0

        # Mock constants
        mock.CAP_PROP_OPEN_TIMEOUT_MSEC = 1
        mock.CAP_PROP_READ_TIMEOUT_MSEC = 2
        mock.MORPH_ELLIPSE = 2
        mock.RETR_EXTERNAL = 0
        mock.CHAIN_APPROX_SIMPLE = 2

        yield mock


@pytest.fixture
def camera_config():
    """Fixture for camera configuration."""
    return CameraConfig(
        url="rtsp://test.camera/stream",
        fps=5,
        resolution=(640, 480),
        retry_max_attempts=3,
        retry_initial_delay=0.1,  # Shorter for testing
        retry_backoff=2.0
    )


@pytest.fixture
def motion_config():
    """Fixture for motion configuration."""
    return MotionConfig(
        sensitivity=5,
        min_area=500,
        cooldown_seconds=1  # Shorter for testing
    )


@pytest.fixture
def detector(mock_cv2, camera_config, motion_config):
    """Fixture for MotionDetector instance."""
    detector = MotionDetector(camera_config, motion_config)
    yield detector
    # Cleanup: stop detector if running
    if detector.is_running:
        detector.stop()


class TestSensitivityMapping:
    """Test sensitivity parameter mapping."""

    def test_sensitivity_range_1(self):
        """Test sensitivity level 1 (most sensitive)."""
        var_threshold, min_area = map_sensitivity_to_params(1)
        assert var_threshold == 8
        assert min_area == 100

    def test_sensitivity_range_5(self):
        """Test sensitivity level 5 (balanced)."""
        var_threshold, min_area = map_sensitivity_to_params(5)
        # Mid-range values
        assert 8 <= var_threshold <= 50
        assert 100 <= min_area <= 2000

    def test_sensitivity_range_10(self):
        """Test sensitivity level 10 (least sensitive)."""
        var_threshold, min_area = map_sensitivity_to_params(10)
        assert var_threshold == 50
        assert min_area == 1999  # int(100 + 9 * 211.11) = 1999

    def test_sensitivity_invalid_low(self):
        """Test invalid sensitivity below range."""
        with pytest.raises(ValueError, match="must be between 1 and 10"):
            map_sensitivity_to_params(0)

    def test_sensitivity_invalid_high(self):
        """Test invalid sensitivity above range."""
        with pytest.raises(ValueError, match="must be between 1 and 10"):
            map_sensitivity_to_params(11)

    def test_sensitivity_linear_interpolation(self):
        """Test that sensitivity values are linearly interpolated."""
        # Test multiple points to verify linear progression
        results = [map_sensitivity_to_params(i) for i in range(1, 11)]

        var_thresholds = [r[0] for r in results]
        min_areas = [r[1] for r in results]

        # Verify var_threshold increases with sensitivity
        for i in range(len(var_thresholds) - 1):
            assert var_thresholds[i] < var_thresholds[i + 1], \
                f"varThreshold should increase: {var_thresholds[i]} >= {var_thresholds[i + 1]}"

        # Verify min_area increases with sensitivity
        for i in range(len(min_areas) - 1):
            assert min_areas[i] < min_areas[i + 1], \
                f"min_area should increase: {min_areas[i]} >= {min_areas[i + 1]}"

    def test_sensitivity_mid_range_values(self):
        """Test specific mid-range sensitivity values for consistency."""
        # Test sensitivity 3
        var_threshold_3, min_area_3 = map_sensitivity_to_params(3)
        assert 8 < var_threshold_3 < 50
        assert 100 < min_area_3 < 2000

        # Test sensitivity 7
        var_threshold_7, min_area_7 = map_sensitivity_to_params(7)
        assert var_threshold_3 < var_threshold_7
        assert min_area_3 < min_area_7

    def test_sensitivity_consistent_mapping(self):
        """Test that calling map_sensitivity_to_params multiple times returns same values."""
        for sensitivity in [1, 5, 10]:
            result1 = map_sensitivity_to_params(sensitivity)
            result2 = map_sensitivity_to_params(sensitivity)
            assert result1 == result2, f"Mapping should be consistent for sensitivity {sensitivity}"


class TestMotionDetectorInit:
    """Test MotionDetector initialization."""

    def test_init_default_config(self, mock_cv2, camera_config, motion_config):
        """Test initialization with default configuration."""
        detector = MotionDetector(camera_config, motion_config)

        assert detector.camera_config == camera_config
        assert detector.motion_config == motion_config
        assert detector.capture is None
        assert not detector.is_running
        assert detector._thread is None

    def test_init_sensitivity_mapping(self, mock_cv2, camera_config):
        """Test that sensitivity is properly mapped during init."""
        config = MotionConfig(sensitivity=5, min_area=500)
        detector = MotionDetector(camera_config, config)

        # Verify background subtractor was created
        mock_cv2.createBackgroundSubtractorMOG2.assert_called_once()
        call_kwargs = mock_cv2.createBackgroundSubtractorMOG2.call_args[1]
        assert 'varThreshold' in call_kwargs
        assert 8 <= call_kwargs['varThreshold'] <= 50

    def test_init_custom_min_area(self, mock_cv2, camera_config):
        """Test initialization with custom min_area overrides mapping."""
        config = MotionConfig(sensitivity=5, min_area=1500)  # Custom value
        detector = MotionDetector(camera_config, config)

        # Custom min_area should be preserved
        assert detector.motion_config.min_area == 1500


class TestConnectionManagement:
    """Test camera connection management."""

    def test_connect_success(self, detector):
        """Test successful camera connection."""
        result = detector.connect()

        assert result is True
        assert detector.is_connected

    def test_connect_no_url(self, mock_cv2, motion_config):
        """Test connection fails without camera URL."""
        config = CameraConfig(url="")
        detector = MotionDetector(config, motion_config)

        with pytest.raises(ValueError, match="Camera URL is required"):
            detector.connect()

    def test_disconnect(self, detector):
        """Test camera disconnection."""
        detector.connect()
        assert detector.is_connected

        detector.disconnect()
        assert not detector.is_connected
        assert detector.capture is None

    def test_connect_retry_on_failure(self, mock_cv2, detector):
        """Test connection retry mechanism."""
        # Make first attempt fail, second succeed
        original_capture = mock_cv2.VideoCapture

        def side_effect_factory(url, *args, **kwargs):
            mock = original_capture(url, *args, **kwargs)
            if not hasattr(side_effect_factory, 'call_count'):
                side_effect_factory.call_count = 0
            side_effect_factory.call_count += 1

            # Fail first attempt
            if side_effect_factory.call_count == 1:
                mock.set_fail_mode(True)
            return mock

        mock_cv2.VideoCapture = side_effect_factory

        result = detector.connect()
        assert result is True


class TestLifecycleManagement:
    """Test lifecycle methods (start, stop, is_running)."""

    def test_start_detector(self, detector):
        """Test starting motion detector."""
        detector.connect()
        detector.start()

        assert detector.is_running
        assert detector._thread is not None
        assert detector._thread.is_alive()

        # Cleanup
        detector.stop()

    def test_start_already_running(self, detector):
        """Test starting detector when already running."""
        detector.connect()
        detector.start()

        with pytest.raises(RuntimeError, match="already running"):
            detector.start()

        detector.stop()

    def test_stop_detector(self, detector):
        """Test stopping motion detector."""
        detector.connect()
        detector.start()
        assert detector.is_running

        detector.stop()

        assert not detector.is_running
        assert detector.capture is None

    def test_stop_not_running(self, detector):
        """Test stopping detector when not running."""
        # Should not raise error
        detector.stop()
        assert not detector.is_running

    def test_is_running_property(self, detector):
        """Test is_running property."""
        assert not detector.is_running

        detector.connect()
        detector.start()
        assert detector.is_running

        detector.stop()
        assert not detector.is_running

    def test_context_manager(self, detector):
        """Test context manager support."""
        detector.connect()

        assert not detector.is_running

        with detector as d:
            assert d is detector
            assert detector.is_running

        assert not detector.is_running


class TestFrameCapture:
    """Test frame capture functionality."""

    def test_get_frame_no_capture(self, detector):
        """Test get_frame when no frame available."""
        frame = detector.get_frame()
        assert frame is None

    def test_get_frame_returns_copy(self, detector):
        """Test that get_frame returns a copy of the frame."""
        detector.connect()
        detector.start()

        # Wait a bit for frame to be captured
        time.sleep(0.3)

        frame1 = detector.get_frame()
        assert frame1 is not None

        frame2 = detector.get_frame()
        assert frame2 is not None

        # Should be separate copies
        assert frame1 is not frame2

        detector.stop()


class TestCallbackMechanism:
    """Test callback registration and invocation."""

    def test_on_motion_registration(self, detector):
        """Test callback registration."""
        callback = Mock()
        detector.on_motion(callback)

        # Callback should be in the list
        assert callback in detector._callbacks

    def test_multiple_callbacks(self, detector):
        """Test multiple callback registration."""
        callback1 = Mock()
        callback2 = Mock()

        detector.on_motion(callback1)
        detector.on_motion(callback2)

        assert len(detector._callbacks) == 2
        assert callback1 in detector._callbacks
        assert callback2 in detector._callbacks

    def test_callback_invoked_on_motion(self, detector, mock_cv2):
        """Test that callback is invoked when motion is detected."""
        # Setup: Create contours that will trigger motion
        mock_contour = np.array([[[0, 0]], [[100, 0]], [[100, 100]], [[0, 100]]])
        mock_cv2.findContours.return_value = ([mock_contour], None)
        mock_cv2.contourArea.return_value = 600  # Above min_area threshold

        callback = Mock()
        detector.on_motion(callback)

        detector.connect()
        detector.start()

        # Wait for motion detection and callback
        time.sleep(0.3)

        detector.stop()

        # Verify callback was invoked at least once
        assert callback.call_count >= 1

    def test_callback_receives_correct_parameters(self, detector, mock_cv2):
        """Test that callback receives frame and contours."""
        # Setup motion detection
        mock_contour = np.array([[[0, 0]], [[100, 0]], [[100, 100]], [[0, 100]]])
        mock_cv2.findContours.return_value = ([mock_contour], None)
        mock_cv2.contourArea.return_value = 600

        callback = Mock()
        detector.on_motion(callback)

        detector.connect()
        detector.start()

        # Wait for callback
        time.sleep(0.3)

        detector.stop()

        # Verify callback was called with correct parameters
        assert callback.call_count >= 1
        call_args = callback.call_args[0]

        # First argument should be a frame (numpy array)
        assert isinstance(call_args[0], np.ndarray)
        assert len(call_args[0].shape) == 3  # Should be a BGR image

        # Second argument should be a list of contours
        assert isinstance(call_args[1], list)

    def test_multiple_callbacks_all_invoked(self, detector, mock_cv2):
        """Test that all registered callbacks are invoked."""
        # Setup motion detection
        mock_contour = np.array([[[0, 0]], [[100, 0]], [[100, 100]], [[0, 100]]])
        mock_cv2.findContours.return_value = ([mock_contour], None)
        mock_cv2.contourArea.return_value = 600

        callback1 = Mock()
        callback2 = Mock()
        callback3 = Mock()

        detector.on_motion(callback1)
        detector.on_motion(callback2)
        detector.on_motion(callback3)

        detector.connect()
        detector.start()

        # Wait for callbacks
        time.sleep(0.3)

        detector.stop()

        # All callbacks should be invoked
        assert callback1.call_count >= 1
        assert callback2.call_count >= 1
        assert callback3.call_count >= 1

    def test_callback_error_doesnt_break_detection(self, detector, mock_cv2):
        """Test that error in one callback doesn't prevent others from running."""
        # Setup motion detection
        mock_contour = np.array([[[0, 0]], [[100, 0]], [[100, 100]], [[0, 100]]])
        mock_cv2.findContours.return_value = ([mock_contour], None)
        mock_cv2.contourArea.return_value = 600

        # First callback raises exception
        callback1 = Mock(side_effect=RuntimeError("Test error"))
        # Second callback should still run
        callback2 = Mock()

        detector.on_motion(callback1)
        detector.on_motion(callback2)

        detector.connect()
        detector.start()

        # Wait for callbacks
        time.sleep(0.3)

        detector.stop()

        # Both callbacks should be invoked despite error in first one
        assert callback1.call_count >= 1
        assert callback2.call_count >= 1

    def test_no_callback_when_no_motion(self, detector, mock_cv2):
        """Test that callbacks are not invoked when no motion detected."""
        # Setup: No motion (empty contours)
        mock_cv2.findContours.return_value = ([], None)

        callback = Mock()
        detector.on_motion(callback)

        detector.connect()
        detector.start()

        # Wait a bit
        time.sleep(0.3)

        detector.stop()

        # Callback should not be invoked
        assert callback.call_count == 0

    def test_callback_receives_frame_copy(self, detector, mock_cv2):
        """Test that callback receives a copy of the frame, not the original."""
        # Setup motion detection
        mock_contour = np.array([[[0, 0]], [[100, 0]], [[100, 100]], [[0, 100]]])
        mock_cv2.findContours.return_value = ([mock_contour], None)
        mock_cv2.contourArea.return_value = 600

        received_frames = []

        def callback(frame, contours):
            received_frames.append(frame)

        detector.on_motion(callback)

        detector.connect()
        detector.start()

        # Wait for callbacks
        time.sleep(0.4)

        detector.stop()

        # Should have received at least one frame
        assert len(received_frames) >= 1

        # If multiple frames received, they should be different objects
        if len(received_frames) >= 2:
            assert received_frames[0] is not received_frames[1]


class TestMotionDetection:
    """Test motion detection logic."""

    def test_detect_motion_no_motion(self, detector, mock_cv2):
        """Test motion detection when no motion present."""
        # Mock returns empty contours
        mock_cv2.findContours.return_value = ([], None)

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        contours = detector._detect_motion(frame)

        assert len(contours) == 0

    def test_detect_motion_with_motion(self, detector, mock_cv2):
        """Test motion detection when motion is present."""
        # Create mock contours with areas above threshold
        mock_contour1 = np.array([[[0, 0]], [[100, 0]], [[100, 100]], [[0, 100]]])
        mock_contour2 = np.array([[[200, 200]], [[300, 200]], [[300, 300]], [[200, 300]]])

        mock_cv2.findContours.return_value = ([mock_contour1, mock_contour2], None)
        mock_cv2.contourArea.side_effect = [600, 700]  # Both above min_area

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        contours = detector._detect_motion(frame)

        assert len(contours) == 2

    def test_detect_motion_filters_small_areas(self, detector, mock_cv2):
        """Test that small contours are filtered out."""
        mock_contour1 = np.array([[[0, 0]], [[10, 0]], [[10, 10]], [[0, 10]]])
        mock_contour2 = np.array([[[200, 200]], [[300, 200]], [[300, 300]], [[200, 300]]])

        mock_cv2.findContours.return_value = ([mock_contour1, mock_contour2], None)
        # First contour too small, second one OK
        mock_cv2.contourArea.side_effect = [50, 700]

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        contours = detector._detect_motion(frame)

        # Only the large contour should be returned
        assert len(contours) == 1

    def test_detect_motion_high_sensitivity_detects_small_objects(self, mock_cv2, camera_config):
        """Test that high sensitivity (low value) detects small objects."""
        # Sensitivity 1 = most sensitive, min_area should be 100
        config = MotionConfig(sensitivity=1, cooldown_seconds=1)
        detector = MotionDetector(camera_config, config)

        # Verify min_area was set correctly
        assert detector.motion_config.min_area == 100

        # Create contour with area between 100-500 (would be filtered at default sensitivity)
        small_contour = np.array([[[0, 0]], [[15, 0]], [[15, 15]], [[0, 15]]])
        mock_cv2.findContours.return_value = ([small_contour], None)
        mock_cv2.contourArea.return_value = 150  # Above min_area for sensitivity 1

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        contours = detector._detect_motion(frame)

        # Should detect the small object
        assert len(contours) == 1

    def test_detect_motion_low_sensitivity_filters_small_objects(self, mock_cv2, camera_config):
        """Test that low sensitivity (high value) filters out small objects."""
        # Sensitivity 10 = least sensitive, min_area should be 1999
        config = MotionConfig(sensitivity=10, cooldown_seconds=1)
        detector = MotionDetector(camera_config, config)

        # Verify min_area was set correctly
        assert detector.motion_config.min_area == 1999  # int(100 + 9 * 211.11) = 1999

        # Create contour with area below 1999
        small_contour = np.array([[[0, 0]], [[40, 0]], [[40, 40]], [[0, 40]]])
        mock_cv2.findContours.return_value = ([small_contour], None)
        mock_cv2.contourArea.return_value = 1500  # Below min_area for sensitivity 10

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        contours = detector._detect_motion(frame)

        # Should NOT detect the small object
        assert len(contours) == 0

    def test_detect_motion_sensitivity_boundary_case(self, mock_cv2, camera_config):
        """Test motion detection at exact min_area boundary."""
        config = MotionConfig(sensitivity=5, cooldown_seconds=1)
        detector = MotionDetector(camera_config, config)

        min_area = detector.motion_config.min_area

        # Test with contour exactly at min_area
        boundary_contour = np.array([[[0, 0]], [[20, 0]], [[20, 20]], [[0, 20]]])
        mock_cv2.findContours.return_value = ([boundary_contour], None)
        mock_cv2.contourArea.return_value = min_area  # Exactly at threshold

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        contours = detector._detect_motion(frame)

        # Should detect (>= threshold)
        assert len(contours) == 1

        # Test with contour just below min_area
        mock_cv2.contourArea.return_value = min_area - 1
        contours = detector._detect_motion(frame)

        # Should NOT detect (< threshold)
        assert len(contours) == 0

    def test_detect_motion_multiple_contours_different_sizes(self, mock_cv2, camera_config):
        """Test motion detection with multiple contours of varying sizes."""
        config = MotionConfig(sensitivity=5, cooldown_seconds=1)
        detector = MotionDetector(camera_config, config)

        min_area = detector.motion_config.min_area

        # Create multiple contours: too small, at boundary, large
        contour1 = np.array([[[0, 0]], [[10, 0]], [[10, 10]], [[0, 10]]])
        contour2 = np.array([[[50, 50]], [[100, 50]], [[100, 100]], [[50, 100]]])
        contour3 = np.array([[[200, 200]], [[400, 200]], [[400, 400]], [[200, 400]]])

        mock_cv2.findContours.return_value = ([contour1, contour2, contour3], None)
        # Areas: too small, at boundary, large
        mock_cv2.contourArea.side_effect = [min_area - 50, min_area, min_area + 1000]

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        contours = detector._detect_motion(frame)

        # Should detect 2 contours (boundary and large, not the small one)
        assert len(contours) == 2

    def test_detect_motion_sensitivity_affects_var_threshold(self, mock_cv2, camera_config):
        """Test that sensitivity affects background subtractor varThreshold."""
        # Test with high sensitivity (low varThreshold)
        config_high = MotionConfig(sensitivity=1, cooldown_seconds=1)
        detector_high = MotionDetector(camera_config, config_high)

        # Test with low sensitivity (high varThreshold)
        config_low = MotionConfig(sensitivity=10, cooldown_seconds=1)
        detector_low = MotionDetector(camera_config, config_low)

        # Verify that background subtractors were created with different varThresholds
        calls = mock_cv2.createBackgroundSubtractorMOG2.call_args_list
        assert len(calls) >= 2

        # Extract varThreshold from the last two calls
        var_threshold_high = calls[-2][1]['varThreshold']
        var_threshold_low = calls[-1][1]['varThreshold']

        # High sensitivity should have lower varThreshold
        assert var_threshold_high < var_threshold_low
        assert var_threshold_high == 8  # Sensitivity 1
        assert var_threshold_low == 50  # Sensitivity 10

    def test_detect_motion_respects_custom_min_area_over_sensitivity(self, mock_cv2, camera_config):
        """Test that explicit min_area overrides sensitivity mapping."""
        # Set sensitivity=1 (would map to min_area=100) but override with custom value
        config = MotionConfig(sensitivity=1, min_area=1000, cooldown_seconds=1)
        detector = MotionDetector(camera_config, config)

        # Custom min_area should be used
        assert detector.motion_config.min_area == 1000

        # Contour with area 150 (would pass sensitivity 1 default, but not custom min_area)
        contour = np.array([[[0, 0]], [[15, 0]], [[15, 15]], [[0, 15]]])
        mock_cv2.findContours.return_value = ([contour], None)
        mock_cv2.contourArea.return_value = 150

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        contours = detector._detect_motion(frame)

        # Should NOT detect (below custom min_area)
        assert len(contours) == 0


class TestCooldownTimer:
    """Test cooldown timer functionality."""

    def test_cooldown_prevents_spam(self, detector, mock_cv2):
        """Test that cooldown prevents callback spam."""
        # Setup: Create contours that will trigger motion
        mock_contour = np.array([[[0, 0]], [[100, 0]], [[100, 100]], [[0, 100]]])
        mock_cv2.findContours.return_value = ([mock_contour], None)
        mock_cv2.contourArea.return_value = 600

        callback = Mock()
        detector.on_motion(callback)

        detector.connect()
        detector.start()

        # Wait for first callback (less than cooldown period)
        time.sleep(0.5)

        detector.stop()

        # With 1 second cooldown and 0.5 second wait, callback should be called only once
        # Even though motion is continuously detected
        assert callback.call_count == 1

    def test_callback_invoked_immediately_first_time(self, detector, mock_cv2):
        """Test that callback is invoked immediately on first motion detection."""
        # Setup motion detection
        mock_contour = np.array([[[0, 0]], [[100, 0]], [[100, 100]], [[0, 100]]])
        mock_cv2.findContours.return_value = ([mock_contour], None)
        mock_cv2.contourArea.return_value = 600

        callback = Mock()
        detector.on_motion(callback)

        # Verify last_motion_time is 0 (no cooldown active)
        assert detector._last_motion_time == 0.0

        detector.connect()
        detector.start()

        # Wait just enough for one frame
        time.sleep(0.3)

        detector.stop()

        # Callback should be invoked immediately (not blocked by cooldown)
        assert callback.call_count == 1

    def test_cooldown_blocks_during_period(self, detector, mock_cv2):
        """Test that callbacks are blocked during cooldown period."""
        # Use shorter cooldown for faster testing
        detector.motion_config.cooldown_seconds = 0.5

        # Setup motion detection
        mock_contour = np.array([[[0, 0]], [[100, 0]], [[100, 100]], [[0, 100]]])
        mock_cv2.findContours.return_value = ([mock_contour], None)
        mock_cv2.contourArea.return_value = 600

        callback = Mock()
        detector.on_motion(callback)

        detector.connect()
        detector.start()

        # Wait for less than cooldown period
        time.sleep(0.3)

        detector.stop()

        # Should only be called once (first motion), subsequent detections blocked
        assert callback.call_count == 1

    def test_cooldown_allows_after_expiry(self, detector, mock_cv2):
        """Test that callbacks are invoked again after cooldown expires."""
        # Use shorter cooldown for faster testing
        detector.motion_config.cooldown_seconds = 0.5

        # Setup motion detection
        mock_contour = np.array([[[0, 0]], [[100, 0]], [[100, 100]], [[0, 100]]])
        mock_cv2.findContours.return_value = ([mock_contour], None)
        mock_cv2.contourArea.return_value = 600

        callback = Mock()
        detector.on_motion(callback)

        detector.connect()
        detector.start()

        # Wait for cooldown to expire plus a bit more
        time.sleep(1.0)

        detector.stop()

        # Should be called at least twice (first motion + after cooldown)
        assert callback.call_count >= 2

    def test_cooldown_timer_updates_after_callback(self, detector, mock_cv2):
        """Test that cooldown timer is updated after callback invocation."""
        # Setup motion detection
        mock_contour = np.array([[[0, 0]], [[100, 0]], [[100, 100]], [[0, 100]]])
        mock_cv2.findContours.return_value = ([mock_contour], None)
        mock_cv2.contourArea.return_value = 600

        callback = Mock()
        detector.on_motion(callback)

        initial_time = detector._last_motion_time
        assert initial_time == 0.0

        detector.connect()
        detector.start()

        # Wait for callback
        time.sleep(0.3)

        detector.stop()

        # Last motion time should be updated
        assert detector._last_motion_time > initial_time
        assert detector._last_motion_time > 0.0

    def test_cooldown_with_multiple_motion_events(self, detector, mock_cv2):
        """Test cooldown behavior with multiple motion events."""
        # Use shorter cooldown for testing
        detector.motion_config.cooldown_seconds = 0.4

        # Setup motion detection
        mock_contour = np.array([[[0, 0]], [[100, 0]], [[100, 100]], [[0, 100]]])
        mock_cv2.findContours.return_value = ([mock_contour], None)
        mock_cv2.contourArea.return_value = 600

        callback = Mock()
        detector.on_motion(callback)

        detector.connect()
        detector.start()

        # Let detector run for 1.2 seconds
        # With 0.4s cooldown and ~0.2s frame delay:
        # - t=0.0s: First callback
        # - t=0.2-0.4s: Motion detected but blocked by cooldown
        # - t=0.5s: Cooldown expired, second callback
        # - t=0.7-0.9s: Motion detected but blocked by cooldown
        # - t=1.0s: Cooldown expired, third callback potentially
        time.sleep(1.2)

        detector.stop()

        # Should have multiple callbacks (at least 2, possibly 3)
        assert callback.call_count >= 2

    def test_zero_cooldown_allows_all_events(self, mock_cv2, camera_config):
        """Test that zero cooldown allows all motion events through."""
        # Create config with zero cooldown
        motion_config = MotionConfig(
            sensitivity=5,
            min_area=500,
            cooldown_seconds=0  # No cooldown
        )
        detector = MotionDetector(camera_config, motion_config)

        # Setup motion detection
        mock_contour = np.array([[[0, 0]], [[100, 0]], [[100, 100]], [[0, 100]]])
        mock_cv2.findContours.return_value = ([mock_contour], None)
        mock_cv2.contourArea.return_value = 600

        callback = Mock()
        detector.on_motion(callback)

        detector.connect()
        detector.start()

        # Wait for multiple frames
        time.sleep(0.5)

        detector.stop()

        # With no cooldown, callback should be invoked frequently
        # At 5 FPS over 0.5 seconds, expect ~2-3 calls minimum
        assert callback.call_count >= 2

    def test_cooldown_respects_configured_value(self, mock_cv2, camera_config):
        """Test that cooldown respects the configured value."""
        # Test with custom cooldown value
        motion_config = MotionConfig(
            sensitivity=5,
            min_area=500,
            cooldown_seconds=2.0  # 2 second cooldown
        )
        detector = MotionDetector(camera_config, motion_config)

        # Setup motion detection
        mock_contour = np.array([[[0, 0]], [[100, 0]], [[100, 100]], [[0, 100]]])
        mock_cv2.findContours.return_value = ([mock_contour], None)
        mock_cv2.contourArea.return_value = 600

        callback = Mock()
        detector.on_motion(callback)

        detector.connect()
        detector.start()

        # Wait less than cooldown period
        time.sleep(1.0)

        detector.stop()

        # Should only be called once due to long cooldown
        assert callback.call_count == 1


class TestThreadSafety:
    """Test thread safety of MotionDetector."""

    def test_concurrent_callback_registration(self, detector):
        """Test concurrent callback registration."""
        callbacks = []

        def register_callbacks():
            for i in range(10):
                callback = Mock()
                callback.__name__ = f"callback_{i}"
                detector.on_motion(callback)
                callbacks.append(callback)

        # Register callbacks from multiple threads
        threads = [threading.Thread(target=register_callbacks) for _ in range(3)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # All callbacks should be registered
        assert len(detector._callbacks) == 30

    def test_get_frame_thread_safe(self, detector):
        """Test that get_frame is thread-safe."""
        detector.connect()
        detector.start()

        time.sleep(0.3)

        frames = []

        def get_frames():
            for _ in range(10):
                frame = detector.get_frame()
                if frame is not None:
                    frames.append(frame)
                time.sleep(0.01)

        threads = [threading.Thread(target=get_frames) for _ in range(3)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        detector.stop()

        # Should have retrieved some frames without errors
        assert len(frames) > 0
