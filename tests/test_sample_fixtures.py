"""Test that all sample fixtures are well-formed and valid."""
from __future__ import annotations

import json
from pathlib import Path

SAMPLES_DIR = Path(__file__).resolve().parents[1] / "data" / "samples"

REQUIRED_KEYS = {"id", "language", "skill", "expected_cefr", "text"}
VALID_LANGUAGES = {"en", "ko", "ja"}
VALID_SKILLS = {"writing", "speaking", "reading", "listening"}
VALID_CEFR = {"A1", "A2", "B1", "B2", "C1", "C2"}


def test_all_sample_files_are_valid_json() -> None:
    """Every .json file in data/samples must parse and contain required keys."""
    json_files = sorted(SAMPLES_DIR.glob("*.json"))
    assert len(json_files) >= 60, f"Expected >=60 samples, found {len(json_files)}"

    for path in json_files:
        data = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict), f"{path.name}: expected dict"
        for key in REQUIRED_KEYS:
            assert key in data, f"{path.name}: missing key '{key}'"


def test_en_samples_20_or_more() -> None:
    """At least 20 English samples."""
    en = sorted(SAMPLES_DIR.glob("en_*.json")) + sorted(SAMPLES_DIR.glob("english_*.json"))
    assert len(en) >= 20, f"Expected >=20 EN samples, found {len(en)}"


def test_ko_samples_20_or_more() -> None:
    """At least 20 Korean samples."""
    ko = sorted(SAMPLES_DIR.glob("ko_*.json")) + sorted(SAMPLES_DIR.glob("korean_*.json"))
    assert len(ko) >= 20, f"Expected >=20 KO samples, found {len(ko)}"


def test_ja_samples_20_or_more() -> None:
    """At least 20 Japanese samples."""
    ja = sorted(SAMPLES_DIR.glob("ja_*.json")) + sorted(SAMPLES_DIR.glob("japanese_*.json"))
    assert len(ja) >= 20, f"Expected >=20 JA samples, found {len(ja)}"


def test_languages_and_skills_valid() -> None:
    """Language, skill, and expected_cefr values must be from known sets."""
    for path in SAMPLES_DIR.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["language"] in VALID_LANGUAGES, f"{path.name}: unknown language '{data['language']}'"
        assert data["skill"] in VALID_SKILLS, f"{path.name}: unknown skill '{data['skill']}'"
        assert data["expected_cefr"] in VALID_CEFR, f"{path.name}: unknown CEFR '{data['expected_cefr']}'"


def test_text_is_not_empty() -> None:
    """Every sample must have non-empty text."""
    for path in SAMPLES_DIR.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        assert len(data["text"].strip()) > 0, f"{path.name}: empty text"


def test_ids_match_filenames() -> None:
    """The 'id' field must match the filename (without .json)."""
    for path in SAMPLES_DIR.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        expected_id = path.stem
        assert data["id"] == expected_id, f"{path.name}: id '{data['id']}' != '{expected_id}'"
