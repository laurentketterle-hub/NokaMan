"""Tests for writing cohesion/coherence rubric (Closes #66)."""
import pytest
from nokaman.rubrics.writing_cohesion import (
    score_writing_cohesion, score_writing_sample, SAMPLE_DOC,
)

class TestWritingCohesion:
    def test_score_returns_dict(self):
        result = score_writing_cohesion(SAMPLE_DOC)
        assert isinstance(result, dict)
        assert "score" in result
        assert "dimensions" in result
        assert 0 <= result["score"] <= 100

    def test_empty_text_raises(self):
        with pytest.raises(ValueError):
            score_writing_cohesion("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError):
            score_writing_cohesion("   ")

    def test_all_dimensions_present(self):
        result = score_writing_cohesion(SAMPLE_DOC)
        dims = result["dimensions"]
        for key in ["connector_density", "reference_cohesion", "paragraph_flow", "topic_consistency"]:
            assert key in dims
            assert 0 <= dims[key] <= 100

    def test_sample_with_id(self):
        result = score_writing_sample(SAMPLE_DOC, sample_id="test-123", duration_seconds=120)
        assert result["sample_id"] == "test-123"
        assert "estimated_wpm" in result

    def test_short_text_does_not_crash(self):
        result = score_writing_cohesion("Hello small text.")
        assert 0 <= result["score"] <= 100

    def test_metadata_present(self):
        result = score_writing_cohesion(SAMPLE_DOC)
        assert "metadata" in result
        assert result["metadata"]["rubric"] == "writing_cohesion_v1"

    def test_medium_text_scores_reasonable(self):
        text = "The study found important results. However, limitations exist. Therefore, more research is needed."
        result = score_writing_cohesion(text)
        assert 0 <= result["score"] <= 100
        assert result["word_count"] > 5
