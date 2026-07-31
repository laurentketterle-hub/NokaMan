"""Tests for writing cohesion/coherence offline scorer."""

from __future__ import annotations

import pytest

from nokaman.rubrics.writing_cohesion import (
    score_writing_cohesion,
    score_writing_sample,
)


class TestScoreWritingCohesion:
    """Test suite for score_writing_cohesion()."""

    # ── Happy path ─────────────────────────────────────────────────

    def test_well_structured_essay_scores_high(self) -> None:
        text = (
            "Climate change is a pressing global issue. "
            "First, rising temperatures have led to more frequent heatwaves. "
            "Furthermore, melting ice caps contribute to sea-level rise. "
            "In addition, extreme weather events have become more common. "
            "Therefore, urgent action is needed to mitigate these effects."
        )
        result = score_writing_cohesion(text)
        assert 40 <= result["score"] <= 95
        assert "cohesion" in result["dimensions"]
        assert "coherence" in result["dimensions"]
        assert "sentence_variety" in result["dimensions"]
        assert result["observations"]["sentence_count"] >= 3
        assert result["observations"]["word_count"] > 0

    def test_single_sentence_returns_low_scores(self) -> None:
        result = score_writing_cohesion("This is a very short piece of writing here.")
        assert 0 <= result["score"] <= 100
        assert result["observations"]["sentence_count"] == 1

    def test_long_text_with_paragraphs(self) -> None:
        text = (
            "Artificial intelligence has transformed many industries.\n\n"
            "However, concerns about bias and fairness remain significant. "
            "Moreover, the lack of transparency in some models is worrying. "
            "Consequently, regulators are starting to act.\n\n"
            "Finally, the future of AI depends on responsible development. "
            "This means considering ethics from the start."
        )
        result = score_writing_cohesion(text)
        assert result["observations"]["paragraph_count"] >= 2
        assert result["observations"]["transition_sentence_count"] >= 1
        assert all(0 <= v <= 100 for v in result["dimensions"].values())

    # ── Error cases ─────────────────────────────────────────────────

    def test_empty_text_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            score_writing_cohesion("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            score_writing_cohesion("   \n  \t  ")

    def test_no_words_raises(self) -> None:
        with pytest.raises(ValueError, match="must contain words"):
            score_writing_cohesion("... ! ? 123")

    # ── Optional overrides ──────────────────────────────────────────

    def test_external_paragraph_count(self) -> None:
        text = "First sentence. Second sentence. Third sentence."
        result = score_writing_cohesion(text, paragraph_count=3)
        assert result["observations"]["paragraph_count"] == 3

    def test_external_transition_count(self) -> None:
        text = "First sentence. However, second sentence. Therefore, third."
        result = score_writing_cohesion(text, transition_count=5)
        assert result["observations"]["transition_sentence_count"] == 5

    # ── Limitations always present ──────────────────────────────────

    def test_limitations_included(self) -> None:
        result = score_writing_cohesion("Test sentence for limitations check.")
        assert len(result["limitations"]) >= 4
        assert any("heuristics" in lim for lim in result["limitations"])
        assert any("surface-level" in lim for lim in result["limitations"])


class TestScoreWritingSample:
    """Test suite for score_writing_sample()."""

    def test_valid_writing_sample(self) -> None:
        sample = {
            "skill": "writing",
            "text": "This is a test. Furthermore, it has transitions. Therefore, it should score.",
        }
        result = score_writing_sample(sample)
        assert 0 <= result["score"] <= 100

    def test_wrong_skill_raises(self) -> None:
        with pytest.raises(ValueError, match="skill must be 'writing'"):
            score_writing_sample({"skill": "speaking", "text": "hello"})

    def test_missing_skill_raises(self) -> None:
        with pytest.raises(ValueError, match="skill must be 'writing'"):
            score_writing_sample({"text": "hello"})

    def test_with_observations(self) -> None:
        sample: dict = {
            "skill": "writing",
            "text": "Test. Another test. Final test.",
            "cohesion_observations": {
                "paragraph_count": 2,
                "transition_count": 3,
            },
        }
        result = score_writing_sample(sample)
        assert result["observations"]["paragraph_count"] == 2
        assert result["observations"]["transition_sentence_count"] == 3

    def test_bad_observations_type_raises(self) -> None:
        with pytest.raises(ValueError, match="cohesion_observations must be an object"):
            score_writing_sample({
                "skill": "writing",
                "text": "test",
                "cohesion_observations": "not-an-object",
            })
