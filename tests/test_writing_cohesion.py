from __future__ import annotations

import pytest

from nokaman.rubrics.writing_cohesion import (
    score_writing_cohesion,
    score_writing_sample,
)


def test_writing_cohesion_good_text() -> None:
    result = score_writing_cohesion(
        "The project was carefully planned and executed. "
        "However, some challenges arose during implementation. "
        "Therefore, we adapted our approach and successfully delivered. "
        "Moreover, the team learned valuable lessons from the experience."
    )
    assert 0 <= result["score"] <= 100
    assert set(result["dimensions"]) == {
        "cohesion",
        "grammar_proxies",
        "length_norms",
        "lexical_diversity",
    }
    assert result["observations"]["word_count"] > 0
    assert result["observations"]["sentence_count"] >= 2
    assert "type_token_ratio" in result["observations"]
    assert any("not a certified CEFR" in item for item in result["limitations"])


def test_writing_cohesion_poor_text() -> None:
    result = score_writing_cohesion("hello world. i am here. teh cat is nice. hello world.")
    # Poor cohesion and grammar should score lower
    assert result["score"] < 80
    assert result["dimensions"]["grammar_proxies"] < 90  # has errors


def test_writing_cohesion_empty_raises() -> None:
    with pytest.raises(ValueError, match="empty"):
        score_writing_cohesion("")


def test_writing_cohesion_no_words_raises() -> None:
    with pytest.raises(ValueError, match="words"):
        score_writing_cohesion("... !!! ???")


def test_writing_sample_requires_writing_skill() -> None:
    with pytest.raises(ValueError, match="writing"):
        score_writing_sample({"skill": "speaking", "text": "hello"})


def test_writing_sample_scores_dict() -> None:
    result = score_writing_sample({
        "skill": "writing",
        "text": "The analysis revealed several patterns. First, the data showed correlation. Second, the model confirmed our hypothesis.",
    })
    assert 50 <= result["score"] <= 100


def test_writing_cohesion_short_text_warns() -> None:
    result = score_writing_cohesion("Hi there.")
    assert any("Short text" in item for item in result["limitations"])


def test_lexical_diversity_repetition_penalty() -> None:
    result = score_writing_cohesion("the the the the the the the the the the the the the the the the")
    assert result["dimensions"]["lexical_diversity"] < 50


def test_grammar_proxies_detect_repeated_words() -> None:
    result = score_writing_cohesion("This is is a test of of repeated words.")
    assert result["dimensions"]["grammar_proxies"] < 95
