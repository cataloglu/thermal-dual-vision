"""Integration tests for motion detection to LLM analysis flow."""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from src.config import LLMConfig
from src.llm_analyzer import AnalysisResult, LLMAnalyzer, ScreenshotSet
from tests.mocks.mock_camera import MockCamera
from tests.mocks.mock_openai import MockOpenAI


@pytest.mark.integration
class TestMotionToLLMIntegration:
    """Integration tests for motion detection to LLM analysis pipeline."""

    @pytest.mark.asyncio
    @patch("src.llm_analyzer.AsyncOpenAI")
    async def test_complete_motion_to_llm_flow(
        self,
        mock_openai_class,
        llm_config
    ):
        """Test complete flow from motion detection to LLM analysis."""
        # Setup mock camera
        camera = MockCamera(width=1280, height=720)

        # Capture screenshot set (simulate motion detection)
        # Before: static frame
        success1, before_frame = camera.read()
        assert success1 is True
        assert before_frame is not None

        # Now: frame with motion
        now_frame = camera.generate_motion_frame(motion_type="person")
        assert now_frame is not None

        # After: another frame with motion
        after_frame = camera.generate_motion_frame(motion_type="person")
        assert after_frame is not None

        # Create screenshot set
        screenshot_set = ScreenshotSet(
            before=before_frame,
            now=now_frame,
            after=after_frame,
            timestamp=datetime.now()
        )

        # Setup mock OpenAI client
        mock_response_json = MockOpenAI.create_valid_motion_response(
            gercek_hareket=True,
            guven_skoru=0.92,
            nesneler=["insan"],
            tehdit="dusuk"
        )

        mock_client = MockOpenAI(response_json=mock_response_json)
        mock_openai_class.return_value = mock_client

        # Create analyzer and analyze screenshots
        analyzer = LLMAnalyzer(llm_config)
        result = await analyzer.analyze(screenshot_set)

        # Verify analysis result
        assert isinstance(result, AnalysisResult)
        assert result.gercek_hareket is True
        assert result.guven_skoru == 0.92
        assert "insan" in result.tespit_edilen_nesneler
        assert result.tehdit_seviyesi == "dusuk"
        assert result.processing_time > 0

        # Verify OpenAI was called
        mock_client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.llm_analyzer.AsyncOpenAI")
    async def test_motion_detection_with_no_motion_result(
        self,
        mock_openai_class,
        llm_config
    ):
        """Test motion detection that LLM determines is false positive."""
        # Setup mock camera
        camera = MockCamera(width=640, height=480)

        # Capture three similar frames (false positive motion detection)
        success1, frame1 = camera.read()
        success2, frame2 = camera.read()
        success3, frame3 = camera.read()

        assert success1 and success2 and success3

        # Create screenshot set
        screenshot_set = ScreenshotSet(
            before=frame1,
            now=frame2,
            after=frame3,
            timestamp=datetime.now()
        )

        # Setup mock OpenAI to return "no real motion"
        mock_response_json = MockOpenAI.create_no_motion_response()
        mock_client = MockOpenAI(response_json=mock_response_json)
        mock_openai_class.return_value = mock_client

        # Analyze
        analyzer = LLMAnalyzer(llm_config)
        result = await analyzer.analyze(screenshot_set)

        # Verify LLM determined no real motion
        assert isinstance(result, AnalysisResult)
        assert result.gercek_hareket is False
        assert result.guven_skoru >= 0.9  # High confidence it's not real motion
        assert result.tespit_edilen_nesneler == []
        assert result.tehdit_seviyesi == "yok"

    @pytest.mark.asyncio
    @patch("src.llm_analyzer.AsyncOpenAI")
    async def test_motion_with_high_threat_detection(
        self,
        mock_openai_class,
        llm_config
    ):
        """Test motion detection with high threat level response."""
        # Setup camera with motion
        camera = MockCamera()
        before_frame = camera.generate_motion_frame(motion_type="rectangle")
        now_frame = camera.generate_motion_frame(motion_type="person")
        after_frame = camera.generate_motion_frame(motion_type="person")

        screenshot_set = ScreenshotSet(
            before=before_frame,
            now=now_frame,
            after=after_frame,
            timestamp=datetime.now()
        )

        # Setup mock OpenAI with high threat response
        mock_response_json = MockOpenAI.create_valid_motion_response(
            gercek_hareket=True,
            guven_skoru=0.95,
            nesneler=["insan", "silah"],
            tehdit="yuksek"
        )
        mock_client = MockOpenAI(response_json=mock_response_json)
        mock_openai_class.return_value = mock_client

        # Analyze
        analyzer = LLMAnalyzer(llm_config)
        result = await analyzer.analyze(screenshot_set)

        # Verify high threat detection
        assert result.gercek_hareket is True
        assert result.guven_skoru == 0.95
        assert result.tehdit_seviyesi == "yuksek"
        assert "insan" in result.tespit_edilen_nesneler
        assert "silah" in result.tespit_edilen_nesneler

    @pytest.mark.asyncio
    @patch("src.llm_analyzer.AsyncOpenAI")
    async def test_motion_without_after_screenshot(
        self,
        mock_openai_class,
        llm_config
    ):
        """Test motion analysis when after screenshot is not yet available."""
        # Setup camera
        camera = MockCamera()
        before_frame = camera.generate_motion_frame(motion_type="rectangle")
        now_frame = camera.generate_motion_frame(motion_type="person")

        # Create screenshot set without after frame
        screenshot_set = ScreenshotSet(
            before=before_frame,
            now=now_frame,
            after=None,  # After frame not yet captured
            timestamp=datetime.now()
        )

        # Setup mock OpenAI
        mock_response_json = MockOpenAI.create_valid_motion_response()
        mock_client = MockOpenAI(response_json=mock_response_json)
        mock_openai_class.return_value = mock_client

        # Analyze
        analyzer = LLMAnalyzer(llm_config)
        result = await analyzer.analyze(screenshot_set)

        # Verify analysis still works with only 2 frames
        assert isinstance(result, AnalysisResult)
        assert result.gercek_hareket is True
        mock_client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.llm_analyzer.AsyncOpenAI")
    async def test_multiple_motion_events_in_sequence(
        self,
        mock_openai_class,
        llm_config
    ):
        """Test analyzing multiple motion events in sequence."""
        camera = MockCamera()

        # Setup mock OpenAI
        mock_client = MockOpenAI()
        mock_openai_class.return_value = mock_client

        analyzer = LLMAnalyzer(llm_config)

        # First motion event - person detected
        screenshot_set_1 = ScreenshotSet(
            before=camera.read()[1],
            now=camera.generate_motion_frame(motion_type="person"),
            after=camera.generate_motion_frame(motion_type="person"),
            timestamp=datetime.now()
        )
        mock_client.set_response_json(
            MockOpenAI.create_valid_motion_response(
                gercek_hareket=True,
                nesneler=["insan"]
            )
        )
        result_1 = await analyzer.analyze(screenshot_set_1)

        # Second motion event - no real motion
        screenshot_set_2 = ScreenshotSet(
            before=camera.read()[1],
            now=camera.read()[1],
            after=camera.read()[1],
            timestamp=datetime.now()
        )
        mock_client.set_response_json(MockOpenAI.create_no_motion_response())
        result_2 = await analyzer.analyze(screenshot_set_2)

        # Verify both analyses
        assert result_1.gercek_hareket is True
        assert "insan" in result_1.tespit_edilen_nesneler

        assert result_2.gercek_hareket is False
        assert result_2.tespit_edilen_nesneler == []

        # Verify rate limiter was used (2 calls)
        assert mock_client.chat.completions.create.call_count == 2

    @pytest.mark.asyncio
    @patch("src.llm_analyzer.AsyncOpenAI")
    async def test_motion_to_llm_with_different_resolutions(
        self,
        mock_openai_class,
        llm_config
    ):
        """Test motion analysis with different camera resolutions."""
        # Test with various resolutions
        resolutions = [
            (640, 480),    # VGA
            (1280, 720),   # HD
            (1920, 1080),  # Full HD
        ]

        mock_client = MockOpenAI()
        mock_openai_class.return_value = mock_client

        analyzer = LLMAnalyzer(llm_config)

        for width, height in resolutions:
            camera = MockCamera(width=width, height=height)

            screenshot_set = ScreenshotSet(
                before=camera.read()[1],
                now=camera.generate_motion_frame(motion_type="person"),
                after=camera.generate_motion_frame(motion_type="person"),
                timestamp=datetime.now()
            )

            result = await analyzer.analyze(screenshot_set)

            # Verify analysis works for all resolutions
            assert isinstance(result, AnalysisResult)
            assert result.processing_time > 0

    @pytest.mark.asyncio
    @patch("src.llm_analyzer.AsyncOpenAI")
    async def test_motion_detection_timing(
        self,
        mock_openai_class,
        llm_config
    ):
        """Test that processing time is tracked correctly."""
        camera = MockCamera()

        screenshot_set = ScreenshotSet(
            before=camera.read()[1],
            now=camera.generate_motion_frame(motion_type="person"),
            after=camera.generate_motion_frame(motion_type="person"),
            timestamp=datetime.now()
        )

        # Setup mock with slight delay simulation
        mock_client = MockOpenAI()
        mock_openai_class.return_value = mock_client

        analyzer = LLMAnalyzer(llm_config)
        result = await analyzer.analyze(screenshot_set)

        # Verify timing was recorded
        assert result.processing_time > 0
        assert result.processing_time < 10  # Should be fast with mocking
        assert isinstance(result.processing_time, float)

    @pytest.mark.asyncio
    @patch("src.llm_analyzer.AsyncOpenAI")
    async def test_motion_with_various_object_detections(
        self,
        mock_openai_class,
        llm_config
    ):
        """Test motion detection with various detected objects."""
        camera = MockCamera()

        test_cases = [
            (["insan"], "dusuk"),
            (["insan", "köpek"], "dusuk"),
            (["araba"], "dusuk"),
            (["insan", "silah"], "yuksek"),
            ([], "yok"),
        ]

        mock_client = MockOpenAI()
        mock_openai_class.return_value = mock_client

        analyzer = LLMAnalyzer(llm_config)

        for objects, expected_threat in test_cases:
            screenshot_set = ScreenshotSet(
                before=camera.read()[1],
                now=camera.generate_motion_frame(motion_type="person"),
                after=camera.generate_motion_frame(motion_type="person"),
                timestamp=datetime.now()
            )

            mock_client.set_response_json(
                MockOpenAI.create_valid_motion_response(
                    gercek_hareket=(len(objects) > 0),
                    nesneler=objects,
                    tehdit=expected_threat
                )
            )

            result = await analyzer.analyze(screenshot_set)

            assert result.tespit_edilen_nesneler == objects
            assert result.tehdit_seviyesi == expected_threat
