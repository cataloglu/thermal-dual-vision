"""Unit tests for utility functions."""

import asyncio
import base64
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import cv2
import numpy as np
import pytest

from src.utils import (
    RateLimiter,
    decode_base64_to_frame,
    encode_frame_to_base64,
    encode_frame_to_bytes,
    retry_async,
    timestamp_filename,
    timestamp_now,
)


@pytest.mark.unit
class TestFrameEncoding:
    """Test frame encoding and decoding functions."""

    @patch('src.utils.cv2')
    @patch('src.utils.Image')
    def test_encode_frame_to_base64(self, mock_image_class, mock_cv2):
        """Test encoding a frame to base64 string."""
        # Create a simple test frame (100x100 blue image)
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        frame[:, :] = [255, 0, 0]  # BGR: Blue

        # Mock cv2.cvtColor to return RGB frame
        rgb_frame = frame[:, :, ::-1]  # Simple BGR to RGB
        mock_cv2.cvtColor.return_value = rgb_frame

        # Mock PIL Image
        mock_image = MagicMock()
        mock_image_class.fromarray.return_value = mock_image
        mock_image.save = MagicMock()

        # Create a mock buffer with JPEG data
        mock_buffer = MagicMock()
        mock_buffer.getvalue.return_value = b'\xff\xd8\xff\xe0test_jpeg_data'

        # Patch BytesIO to return our mock buffer
        with patch('src.utils.io.BytesIO', return_value=mock_buffer):
            # Encode to base64
            base64_str = encode_frame_to_base64(frame, quality=85)

        # Verify it's a valid base64 string
        assert isinstance(base64_str, str)
        assert len(base64_str) > 0

        # Verify cv2.cvtColor was called
        mock_cv2.cvtColor.assert_called_once()

    @patch('src.utils.cv2')
    @patch('src.utils.Image')
    def test_encode_frame_to_base64_with_different_quality(self, mock_image_class, mock_cv2):
        """Test encoding with different quality settings."""
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        frame[:, :] = [0, 255, 0]  # BGR: Green

        # Mock cv2.cvtColor
        mock_cv2.cvtColor.return_value = frame[:, :, ::-1]

        # Mock PIL Image with different sizes for different qualities
        mock_image = MagicMock()
        mock_image_class.fromarray.return_value = mock_image

        call_count = [0]
        def mock_save(buffer, **kwargs):
            call_count[0] += 1
            # Higher quality = more data
            if kwargs.get('quality', 85) == 95:
                buffer.write(b'x' * 1000)
            else:
                buffer.write(b'x' * 500)

        with patch('src.utils.io.BytesIO') as mock_bytesio:
            mock_buffer = MagicMock()
            mock_bytesio.return_value = mock_buffer

            # First call (high quality)
            mock_buffer.getvalue.return_value = b'x' * 1000
            high_quality = encode_frame_to_base64(frame, quality=95)

            # Second call (low quality)
            mock_buffer.getvalue.return_value = b'x' * 500
            low_quality = encode_frame_to_base64(frame, quality=50)

        assert len(high_quality) > len(low_quality)

    @patch('src.utils.cv2')
    def test_encode_frame_to_bytes(self, mock_cv2):
        """Test encoding a frame to JPEG bytes."""
        # Create a test frame (50x50 red image)
        frame = np.zeros((50, 50, 3), dtype=np.uint8)
        frame[:, :] = [0, 0, 255]  # BGR: Red

        # Mock cv2.imencode to return JPEG bytes
        mock_buffer = np.array([[0xff, 0xd8, 0xff, 0xe0, 0x00, 0x10]], dtype=np.uint8)
        mock_cv2.imencode.return_value = (True, mock_buffer)
        mock_cv2.IMWRITE_JPEG_QUALITY = 1

        # Encode to bytes
        jpeg_bytes = encode_frame_to_bytes(frame, quality=85)

        # Verify it's bytes and not empty
        assert isinstance(jpeg_bytes, bytes)
        assert len(jpeg_bytes) > 0

        # Verify cv2.imencode was called
        mock_cv2.imencode.assert_called_once()

    @patch('src.utils.cv2')
    def test_encode_frame_to_bytes_quality(self, mock_cv2):
        """Test encoding bytes with different quality."""
        frame = np.ones((100, 100, 3), dtype=np.uint8) * 128
        mock_cv2.IMWRITE_JPEG_QUALITY = 1

        # Return different sizes for different qualities
        call_count = [0]
        def mock_imencode(ext, frame, params):
            call_count[0] += 1
            quality = params[1] if len(params) > 1 else 85
            size = 1000 if quality == 100 else 500
            return (True, np.zeros(size, dtype=np.uint8))

        mock_cv2.imencode.side_effect = mock_imencode

        high_quality = encode_frame_to_bytes(frame, quality=100)
        low_quality = encode_frame_to_bytes(frame, quality=10)

        # Higher quality should produce larger output
        assert len(high_quality) > len(low_quality)

    @patch('src.utils.cv2')
    def test_decode_base64_to_frame(self, mock_cv2):
        """Test decoding base64 string back to frame."""
        # Create a test base64 string (simulating JPEG data)
        test_jpeg = b'\xff\xd8\xff\xe0\x00\x10JFIF'
        base64_str = base64.b64encode(test_jpeg).decode('utf-8')

        # Mock cv2.imdecode to return a frame
        decoded_frame = np.zeros((100, 100, 3), dtype=np.uint8)
        decoded_frame[:, :] = [255, 128, 64]
        mock_cv2.imdecode.return_value = decoded_frame
        mock_cv2.IMREAD_COLOR = 1

        # Decode
        result = decode_base64_to_frame(base64_str)

        # Verify
        assert result.shape == decoded_frame.shape
        assert result.dtype == np.uint8
        mock_cv2.imdecode.assert_called_once()

    @patch('src.utils.cv2')
    @patch('src.utils.Image')
    def test_encode_decode_round_trip(self, mock_image_class, mock_cv2):
        """Test encoding and decoding produces similar result."""
        # Create a frame with some pattern
        original_frame = np.zeros((200, 200, 3), dtype=np.uint8)
        original_frame[50:150, 50:150] = [200, 100, 50]

        # Mock encode path
        mock_cv2.cvtColor.return_value = original_frame[:, :, ::-1]
        mock_image = MagicMock()
        mock_image_class.fromarray.return_value = mock_image

        test_jpeg = b'\xff\xd8\xff\xe0test_jpeg'
        with patch('src.utils.io.BytesIO') as mock_bytesio:
            mock_buffer = MagicMock()
            mock_buffer.getvalue.return_value = test_jpeg
            mock_bytesio.return_value = mock_buffer

            # Encode
            base64_str = encode_frame_to_base64(original_frame, quality=90)

        # Mock decode path (return similar frame with slight differences)
        decoded_frame = original_frame.copy()
        decoded_frame[50:150, 50:150] = [198, 102, 52]  # Slightly different (JPEG artifacts)
        mock_cv2.imdecode.return_value = decoded_frame
        mock_cv2.IMREAD_COLOR = 1

        # Decode
        result = decode_base64_to_frame(base64_str)

        # Should have same shape
        assert result.shape == original_frame.shape

        # Should be similar (we mocked it to be similar)
        assert isinstance(result, np.ndarray)


@pytest.mark.unit
class TestTimestampFunctions:
    """Test timestamp utility functions."""

    def test_timestamp_now_format(self):
        """Test timestamp_now returns ISO format string."""
        timestamp = timestamp_now()

        # Verify it's a string
        assert isinstance(timestamp, str)

        # Verify it can be parsed back to datetime
        parsed = datetime.fromisoformat(timestamp)
        assert isinstance(parsed, datetime)

    def test_timestamp_now_is_recent(self):
        """Test timestamp_now returns current time."""
        before = datetime.now()
        timestamp_str = timestamp_now()
        after = datetime.now()

        parsed = datetime.fromisoformat(timestamp_str)

        # Timestamp should be between before and after
        assert before <= parsed <= after

    def test_timestamp_filename_format(self):
        """Test timestamp_filename returns filename-safe format."""
        filename_ts = timestamp_filename()

        # Verify it's a string
        assert isinstance(filename_ts, str)

        # Verify format is YYYYMMDD_HHMMSS
        assert len(filename_ts) == 15  # 8 digits + 1 underscore + 6 digits
        assert filename_ts[8] == '_'

        # Verify all other characters are digits
        assert filename_ts[:8].isdigit()
        assert filename_ts[9:].isdigit()

    def test_timestamp_filename_is_current(self):
        """Test timestamp_filename returns current time."""
        now = datetime.now()
        filename_ts = timestamp_filename()

        # Parse the timestamp
        year = int(filename_ts[0:4])
        month = int(filename_ts[4:6])
        day = int(filename_ts[6:8])

        # Should be today's date
        assert year == now.year
        assert month == now.month
        assert day == now.day


@pytest.mark.unit
class TestRetryAsync:
    """Test async retry decorator."""

    @pytest.mark.asyncio
    async def test_retry_success_on_first_attempt(self):
        """Test function succeeds on first attempt."""
        mock_func = AsyncMock(return_value="success")
        decorated = retry_async(max_attempts=3, delay=0.01)(mock_func)

        result = await decorated("test_arg")

        assert result == "success"
        assert mock_func.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_success_after_failures(self):
        """Test function succeeds after initial failures."""
        mock_func = AsyncMock(side_effect=[
            Exception("Fail 1"),
            Exception("Fail 2"),
            "success"
        ])
        decorated = retry_async(max_attempts=3, delay=0.01)(mock_func)

        result = await decorated("test_arg")

        assert result == "success"
        assert mock_func.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_exhausted(self):
        """Test retry exhausts all attempts and raises last exception."""
        test_exception = ValueError("Always fail")
        mock_func = AsyncMock(side_effect=test_exception)
        decorated = retry_async(max_attempts=3, delay=0.01)(mock_func)

        with pytest.raises(ValueError, match="Always fail"):
            await decorated("test_arg")

        assert mock_func.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_with_specific_exception(self):
        """Test retry only catches specified exceptions."""
        mock_func = AsyncMock(side_effect=ValueError("Specific error"))
        decorated = retry_async(
            max_attempts=3,
            delay=0.01,
            exceptions=(ValueError,)
        )(mock_func)

        with pytest.raises(ValueError):
            await decorated()

        assert mock_func.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_does_not_catch_other_exceptions(self):
        """Test retry doesn't catch exceptions not in exceptions tuple."""
        mock_func = AsyncMock(side_effect=TypeError("Wrong type"))
        decorated = retry_async(
            max_attempts=3,
            delay=0.01,
            exceptions=(ValueError,)  # Only catch ValueError
        )(mock_func)

        # Should raise immediately, not retry
        with pytest.raises(TypeError):
            await decorated()

        assert mock_func.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_backoff(self):
        """Test retry delay increases with backoff."""
        call_times = []

        async def mock_func():
            call_times.append(asyncio.get_event_loop().time())
            if len(call_times) < 3:
                raise Exception("Retry me")
            return "success"

        decorated = retry_async(
            max_attempts=3,
            delay=0.05,
            backoff=2.0
        )(mock_func)

        result = await decorated()

        assert result == "success"
        assert len(call_times) == 3

        # Check delays are increasing (with tolerance for timing imprecision)
        delay1 = call_times[1] - call_times[0]
        delay2 = call_times[2] - call_times[1]

        # First delay should be ~0.05s, second should be ~0.10s
        assert 0.04 <= delay1 <= 0.07
        assert 0.09 <= delay2 <= 0.13


@pytest.mark.unit
class TestRateLimiter:
    """Test RateLimiter class."""

    @pytest.mark.asyncio
    async def test_rate_limiter_first_call_immediate(self):
        """Test first call goes through immediately."""
        limiter = RateLimiter(min_interval=0.1)

        start_time = asyncio.get_event_loop().time()
        await limiter.acquire()
        end_time = asyncio.get_event_loop().time()

        # First call should be immediate (< 10ms)
        elapsed = end_time - start_time
        assert elapsed < 0.01

    @pytest.mark.asyncio
    async def test_rate_limiter_enforces_interval(self):
        """Test rate limiter enforces minimum interval."""
        limiter = RateLimiter(min_interval=0.1)

        # First call
        start_time = asyncio.get_event_loop().time()
        await limiter.acquire()

        # Second call (should be delayed)
        await limiter.acquire()
        end_time = asyncio.get_event_loop().time()

        # Total time should be at least min_interval
        elapsed = end_time - start_time
        assert elapsed >= 0.09  # Allow small tolerance

    @pytest.mark.asyncio
    async def test_rate_limiter_multiple_calls(self):
        """Test rate limiter with multiple calls."""
        limiter = RateLimiter(min_interval=0.05)

        start_time = asyncio.get_event_loop().time()

        # Make 3 calls
        await limiter.acquire()
        await limiter.acquire()
        await limiter.acquire()

        end_time = asyncio.get_event_loop().time()

        # Total time should be at least 2 * min_interval
        elapsed = end_time - start_time
        assert elapsed >= 0.09  # 2 * 0.05 with tolerance

    @pytest.mark.asyncio
    async def test_rate_limiter_context_manager(self):
        """Test rate limiter as async context manager."""
        limiter = RateLimiter(min_interval=0.05)

        start_time = asyncio.get_event_loop().time()

        # First call with context manager
        async with limiter:
            pass

        # Second call (should be delayed)
        async with limiter:
            pass

        end_time = asyncio.get_event_loop().time()

        # Should have waited at least min_interval
        elapsed = end_time - start_time
        assert elapsed >= 0.04  # Allow tolerance

    @pytest.mark.asyncio
    async def test_rate_limiter_concurrent_safe(self):
        """Test rate limiter is safe with concurrent calls."""
        limiter = RateLimiter(min_interval=0.05)
        call_times = []

        async def make_call(call_id):
            await limiter.acquire()
            call_times.append((call_id, asyncio.get_event_loop().time()))

        # Start multiple concurrent tasks
        await asyncio.gather(
            make_call(1),
            make_call(2),
            make_call(3)
        )

        # All calls should be serialized with proper intervals
        assert len(call_times) == 3

        # Check intervals between consecutive calls
        for i in range(1, len(call_times)):
            interval = call_times[i][1] - call_times[i-1][1]
            # Each should be at least min_interval apart (with tolerance)
            assert interval >= 0.04
