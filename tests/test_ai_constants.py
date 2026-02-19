"""Tests for AI response parsing constants."""
from app.services.ai_constants import AI_NEGATIVE_MARKERS, AI_POSITIVE_MARKERS


def test_negative_markers_not_empty():
    assert len(AI_NEGATIVE_MARKERS) > 0


def test_positive_markers_not_empty():
    assert len(AI_POSITIVE_MARKERS) > 0


def test_no_overlap():
    overlap = set(AI_NEGATIVE_MARKERS) & set(AI_POSITIVE_MARKERS)
    assert overlap == set(), f"Marker conflict: {overlap}"
