"""Tests for writing cohesion/coherence rubric."""

import pytest
from nokaman.rubrics.writing_cohesion import (
    score_writing_cohesion,
    score_writing_sample,
    DIMENSION_WEIGHTS,
)


def test_empty_text_raises():
    with pytest.raises(ValueError, match="must not be empty"):
        score_writing_cohesion("")


def test_text_without_words_raises():
    with pytest.raises(ValueError, match="must contain words"):
        score_writing_cohesion("... !!! ???")


def test_basic_cohesion_scoring():
    text = (
        "I enjoy learning languages. It helps me meet new people. "
        "However, it can be challenging. Therefore, I practice every day."
    )
    result = score_writing_cohesion(text)
    assert "score" in result
    assert "dimensions" in result
    assert "observations" in result
    assert "limitations" in result
    assert 0 <= result["score"] <= 100
    assert set(result["dimensions"].keys()) == set(DIMENSION_WEIGHTS.keys())
    for name, val in result["dimensions"].items():
        assert 0 <= val <= 100, f"{name}={val} out of range"


def test_well_structured_paragraphs():
    text = (
        "Learning a new language opens many doors. It allows you to connect with people from different cultures. "
        "Moreover, it improves cognitive abilities and memory.\n\n"
        "However, language learning can be difficult. It requires consistent practice and dedication. "
        "Therefore, it is important to set realistic goals. Additionally, finding a study partner can help.\n\n"
        "In conclusion, the benefits of language learning far outweigh the challenges. "
        "With the right approach and mindset, anyone can succeed."
    )
    result = score_writing_cohesion(text)
    assert result["observations"]["paragraph_count"] == 3
    assert result["observations"]["sentence_count"] >= 5
    assert result["dimensions"]["paragraph_structure"] >= 30


def test_short_text():
    text = "I like cats."
    result = score_writing_cohesion(text)
    assert 0 <= result["score"] <= 100
    assert result["observations"]["word_count"] == 3
    assert result["observations"]["sentence_count"] == 1


def test_cohesive_devices_detected():
    text = (
        "She went to the store. However, she forgot her wallet. "
        "Therefore, she had to go back home. This was frustrating."
    )
    result = score_writing_cohesion(text)
    assert result["observations"]["pronoun_count"] >= 2
    assert result["observations"]["connective_count"] >= 2


def test_score_writing_sample():
    sample = {
        "skill": "writing",
        "text": "I enjoy learning languages. It helps me communicate with others.",
        "language": "en",
    }
    result = score_writing_sample(sample)
    assert 0 <= result["score"] <= 100


def test_score_writing_sample_wrong_skill():
    sample = {"skill": "speaking", "text": "Hello"}
    with pytest.raises(ValueError, match="sample skill must be writing"):
        score_writing_sample(sample)


def test_transition_quality():
    text = (
        "First, I woke up. Then, I ate breakfast. Next, I went to work. "
        "However, I forgot my keys. Therefore, I had to go back. Finally, I arrived late."
    )
    result = score_writing_cohesion(text)
    assert result["dimensions"]["transition_quality"] >= 40
