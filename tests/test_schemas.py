"""Tests for pydantic schema validation of rubrics and samples."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from nokaman.schemas import (
    FluencyObservations,
    LanguageRubric,
    ListeningPack,
    ListeningQuestion,
    SamplePayload,
    SkillRubric,
    validate_listening_pack,
    validate_rubric,
    validate_rubric_file,
    validate_sample,
    validate_sample_file,
)


# ── SkillRubric ──────────────────────────────────────────────────────
def test_skill_rubric_defaults() -> None:
    s = SkillRubric()
    assert s.weight == 1.0
    assert s.notes == ""


def test_skill_rubric_custom() -> None:
    s = SkillRubric(weight=2.5, notes="Custom notes")
    assert s.weight == 2.5
    assert s.notes == "Custom notes"


def test_skill_rubric_negative_weight_raises() -> None:
    with pytest.raises(ValidationError):
        SkillRubric(weight=-1.0)


# ── LanguageRubric ───────────────────────────────────────────────────
def test_language_rubric_validation() -> None:
    data = {
        "language": "en",
        "name": "English",
        "skills": {
            "vocabulary": {"weight": 1.0, "notes": "test"},
            "grammar": {"weight": 1.0, "notes": "test"},
        },
        "bands": ["A1", "A2", "B1", "B2", "C1", "C2"],
    }
    rubric = validate_rubric(data)
    assert rubric.language == "en"
    assert rubric.name == "English"
    assert "vocabulary" in rubric.skills
    assert rubric.bands == ["A1", "A2", "B1", "B2", "C1", "C2"]


def test_language_rubric_unknown_skill_raises() -> None:
    data = {
        "language": "en",
        "name": "English",
        "skills": {
            "bogus_skill": {"weight": 1.0, "notes": "bad"},
        },
        "bands": ["A1"],
    }
    with pytest.raises(ValidationError, match="Unknown rubric skills"):
        validate_rubric(data)


def test_language_rubric_unknown_band_raises() -> None:
    data = {
        "language": "en",
        "name": "English",
        "skills": {"vocabulary": {"weight": 1.0}},
        "bands": ["X1"],
    }
    with pytest.raises(ValidationError, match="Unknown CEFR bands"):
        validate_rubric(data)


def test_language_rubric_missing_language_raises() -> None:
    with pytest.raises(ValidationError):
        LanguageRubric.model_validate({"name": "Bad", "skills": {}, "bands": []})


def test_validate_rubric_file_validates_existing_fixtures() -> None:
    rubrics_dir = Path("data/rubrics")
    for path in sorted(rubrics_dir.glob("*.json")):
        rubric = validate_rubric_file(str(path))
        assert rubric.language == path.stem


# ── SamplePayload ────────────────────────────────────────────────────
def test_sample_validation() -> None:
    data = {
        "id": "en_writing_a1",
        "language": "en",
        "skill": "writing",
        "expected_cefr": "A1",
        "text": "Hello. My name is Ana.",
    }
    sample = validate_sample(data)
    assert sample.id == "en_writing_a1"
    assert sample.language == "en"
    assert sample.skill == "writing"
    assert sample.expected_cefr == "A1"


def test_sample_unknown_skill_raises() -> None:
    with pytest.raises(ValidationError, match="Unknown skill"):
        validate_sample({"language": "en", "skill": "bogus", "text": "hi"})


def test_sample_unknown_cefr_raises() -> None:
    with pytest.raises(ValidationError, match="Unknown CEFR level"):
        validate_sample({"language": "en", "skill": "writing", "expected_cefr": "D1", "text": "hi"})


def test_sample_with_fluency_observations() -> None:
    data = {
        "id": "en_speaking_b1",
        "language": "en",
        "skill": "speaking",
        "expected_cefr": "B1",
        "text": "Hello, I would like to describe my hometown.",
        "fluency_observations": {
            "duration_seconds": 45.5,
            "pause_count": 3,
            "filler_count": 2,
        },
    }
    sample = validate_sample(data)
    assert sample.fluency_observations is not None
    assert sample.fluency_observations.duration_seconds == 45.5
    assert sample.fluency_observations.pause_count == 3


def test_sample_fluency_negative_pause_raises() -> None:
    with pytest.raises(ValidationError):
        FluencyObservations(pause_count=-1)


def test_validate_sample_file_validates_existing_fixtures() -> None:
    samples_dir = Path("data/samples")
    count = 0
    for path in sorted(samples_dir.glob("*.json")):
        sample = validate_sample_file(str(path))
        assert sample.language
        assert sample.skill
        count += 1
    assert count >= 10


# ── ListeningPack ────────────────────────────────────────────────────
def test_listening_pack_validation() -> None:
    data = {
        "id": "en_listening_a2",
        "language": "en",
        "items": [
            {
                "prompt": "What is the main topic?",
                "options": ["A", "B", "C"],
                "correct_index": 0,
                "transcript": "The text...",
            }
        ],
    }
    pack = validate_listening_pack(data)
    assert pack.id == "en_listening_a2"
    assert len(pack.items) == 1
    assert pack.items[0].prompt == "What is the main topic?"
