"""
Unit tests for optimized inference service.

Tests YOLO optimization, CLAHE, and filtering logic.
"""
import pytest
import numpy as np
from app.services.inference import InferenceService


class TestInferenceService:
    """Test suite for InferenceService."""
    
    def test_aspect_ratio_filter_person(self):
        """Test aspect ratio filter accepts person-shaped detections."""
        service = InferenceService()
        
        # Person-shaped bbox (width/height = 0.5)
        detections = [
            {"bbox": [100, 100, 150, 200], "confidence": 0.9, "class_id": 0}
        ]
        
        filtered = service.filter_by_aspect_ratio(
            detections,
            min_ratio=0.2,
            max_ratio=1.2
        )
        
        assert len(filtered) == 1
        assert filtered[0]["aspect_ratio"] == 0.5
    
    def test_aspect_ratio_filter_tree(self):
        """Test aspect ratio filter rejects tree-shaped detections."""
        service = InferenceService()
        
        # Tree-shaped bbox (width/height = 2.0)
        detections = [
            {"bbox": [100, 100, 300, 200], "confidence": 0.9, "class_id": 0}
        ]
        
        filtered = service.filter_by_aspect_ratio(
            detections,
            min_ratio=0.2,
            max_ratio=1.2
        )
        
        assert len(filtered) == 0  # Rejected
    
    def test_temporal_consistency_pass(self):
        """Test temporal consistency passes for stable detections."""
        service = InferenceService()
        
        # Current detection
        current = [{"bbox": [100, 100, 150, 200]}]
        
        # History: 3 frames with detections
        history = [
            [{"bbox": [100, 100, 150, 200]}],
            [{"bbox": [100, 100, 150, 200]}],
            [{"bbox": [100, 100, 150, 200]}],
        ]
        
        result = service.check_temporal_consistency(
            current,
            history,
            min_consecutive_frames=3,
            max_gap_frames=1
        )
        
        assert result is True
    
    def test_temporal_consistency_fail_flickering(self):
        """Test temporal consistency fails for flickering detections."""
        service = InferenceService()
        
        # Current detection
        current = [{"bbox": [100, 100, 150, 200]}]
        
        # History: Flickering (on-off-on pattern)
        history = [
            [],
            [{"bbox": [100, 100, 150, 200]}],
            [],
        ]
        
        result = service.check_temporal_consistency(
            current,
            history,
            min_consecutive_frames=3,
            max_gap_frames=1
        )
        
        assert result is False  # Should fail (too many gaps)
    
    def test_kurtosis_clahe_low_contrast(self):
        """Test kurtosis CLAHE for low contrast images."""
        service = InferenceService()
        
        # Low contrast image (narrow histogram)
        frame = np.random.randint(100, 120, (480, 640), dtype=np.uint8)
        
        params = service.get_kurtosis_based_clahe_params(frame)
        
        # Low contrast → aggressive enhancement
        assert params["clip_limit"] >= 3.0
        assert params["tile_size"][0] >= 10
    
    def test_kurtosis_clahe_high_contrast(self):
        """Test kurtosis CLAHE for high contrast images."""
        service = InferenceService()
        
        # High contrast image (bimodal histogram)
        frame = np.concatenate([
            np.full((480, 320), 50, dtype=np.uint8),
            np.full((480, 320), 200, dtype=np.uint8)
        ], axis=1)
        
        params = service.get_kurtosis_based_clahe_params(frame)
        
        # High contrast → gentle enhancement
        assert params["clip_limit"] <= 2.0
    
    def test_point_in_polygon_inside(self):
        """Test point-in-polygon for point inside."""
        service = InferenceService()
        
        # Square polygon
        polygon = [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]
        
        # Point inside
        result = service._point_in_polygon((0.5, 0.5), polygon)
        
        assert result is True
    
    def test_point_in_polygon_outside(self):
        """Test point-in-polygon for point outside."""
        service = InferenceService()
        
        # Square polygon
        polygon = [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]
        
        # Point outside
        result = service._point_in_polygon((1.5, 1.5), polygon)
        
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
