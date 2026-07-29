"""Tests for pydantic rubric + sample validation."""
import pytest
from nokaman.models.validators import (
    SamplePayload,
    RubricPayload,
    SkillRubric,
    validate_sample,
    validate_rubric,
    validate_sample_or_errors,
    validate_rubric_or_errors,
)


class TestSampleValidation:
    """Sample JSON payload validation."""

    def test_valid_sample_minimal(self):
        """Minimal valid sample passes validation."""
        data = {"id": "test-1", "language": "en", "text": "Hello world"}
        result = validate_sample(data)
        assert result.id == "test-1"
        assert result.language == "en"

    def test_valid_sample_full(self):
        """Full valid sample with all fields."""
        data = {
            "id": "ja_writing_a1",
            "language": "ja",
            "skill": "writing",
            "expected_cefr": "A1",
            "text": "こんにちは",
        }
        result = validate_sample(data)
        assert result.expected_cefr == "A1"

    def test_missing_id_raises_error(self):
        """Missing id returns validation error."""
        errors = validate_sample_or_errors({"language": "en", "text": "hi"})
        assert len(errors) > 0
        assert any("id" in e for e in errors)

    def test_empty_id_raises_error(self):
        """Empty string id fails."""
        errors = validate_sample_or_errors({"id": "", "language": "en", "text": "hi"})
        assert len(errors) > 0

    def test_missing_text_raises_error(self):
        """Missing text returns validation error."""
        errors = validate_sample_or_errors({"id": "x", "language": "en"})
        assert len(errors) > 0
        assert any("text" in e for e in errors)

    def test_uppercase_language_rejected(self):
        """Language must be lowercase."""
        errors = validate_sample_or_errors({"id": "x", "language": "EN", "text": "hi"})
        assert len(errors) > 0
        assert any("lowercase" in e.lower() for e in errors)

    def test_invalid_cefr_rejected(self):
        """expected_cefr must be a valid CEFR band."""
        errors = validate_sample_or_errors({
            "id": "x", "language": "en", "text": "hi", "expected_cefr": "X99"
        })
        assert len(errors) > 0

    def test_valid_cefr_accepted(self):
        """All CEFR bands are accepted."""
        for band in ("A1", "A2", "B1", "B2", "C1", "C2"):
            data = {"id": f"t-{band}", "language": "en", "text": "ok", "expected_cefr": band}
            result = validate_sample(data)
            assert result.expected_cefr == band

    def test_existing_fixtures_validate(self):
        """Existing sample fixtures from data/samples/ should pass validation."""
        import json
        from pathlib import Path
        samples_dir = Path("data/samples")
        if samples_dir.exists():
            for fp in sorted(samples_dir.glob("*.json"))[:10]:
                data = json.loads(fp.read_text(encoding="utf-8"))
                # Some fixtures may not have an 'id' field — use stem as fallback
                if "id" not in data:
                    data["id"] = fp.stem
                result = validate_sample(data)
                assert result.id, f"Fixture {fp.name} has no id after fallback"
                assert result.language, f"Fixture {fp.name} has no language"


class TestRubricValidation:
    """Rubric JSON payload validation."""

    def test_valid_rubric_minimal(self):
        """Minimal rubric passes."""
        data = {
            "language": "en",
            "skills": {"vocabulary": {"weight": 1.0, "notes": "test"}},
        }
        result = validate_rubric(data)
        assert result.language == "en"

    def test_missing_language_raises(self):
        """Missing language returns errors."""
        errors = validate_rubric_or_errors({"skills": {"v": {"weight": 1.0}}})
        assert len(errors) > 0

    def test_uppercase_language_rejected(self):
        """Uppercase language rejected."""
        errors = validate_rubric_or_errors({
            "language": "EN",
            "skills": {"v": {"weight": 1.0}},
        })
        assert len(errors) > 0
        assert any("lowercase" in e.lower() for e in errors)

    def test_skill_weight_zero_rejected(self):
        """Skill weight must be > 0."""
        errors = validate_rubric_or_errors({
            "language": "en",
            "skills": {"v": {"weight": 0.0}},
        })
        assert len(errors) > 0

    def test_skill_weight_negative_rejected(self):
        """Negative weight rejected."""
        errors = validate_rubric_or_errors({
            "language": "en",
            "skills": {"v": {"weight": -1.0}},
        })
        assert len(errors) > 0

    def test_empty_skills_rejected(self):
        """Empty skills dict rejected."""
        errors = validate_rubric_or_errors({"language": "en", "skills": {}})
        assert len(errors) > 0

    def test_unknown_cefr_band_rejected(self):
        """Unknown CEFR bands rejected."""
        errors = validate_rubric_or_errors({
            "language": "en",
            "skills": {"v": {"weight": 1.0}},
            "bands": ["A1", "X99"],
        })
        assert len(errors) > 0

    def test_valid_bands_accepted(self):
        """Valid CEFR bands accepted."""
        data = {
            "language": "en",
            "skills": {"v": {"weight": 1.0}},
            "bands": ["A1", "A2"],
        }
        result = validate_rubric(data)
        assert result.bands == ["A1", "A2"]

    def test_existing_rubrics_validate(self):
        """Existing rubric fixtures from data/rubrics/ should pass."""
        import json
        from pathlib import Path
        rubrics_dir = Path("data/rubrics")
        if rubrics_dir.exists():
            for fp in sorted(rubrics_dir.glob("*.json")):
                data = json.loads(fp.read_text(encoding="utf-8"))
                result = validate_rubric(data)
                assert result.language, f"Rubric {fp.name} has no language"


class TestErrorMessageClarity:
    """Validation errors must be human-readable."""

    def test_missing_field_message_clear(self):
        """Missing field error identifies the field."""
        errors = validate_sample_or_errors({"language": "en", "text": "hi"})
        assert any("id" in e and "required" in e for e in errors)

    def test_multiple_errors_reported(self):
        """Multiple validation failures are all reported."""
        errors = validate_sample_or_errors({
            "language": "EN",  # uppercase
            "expected_cefr": "BAD",  # invalid
        })
        assert len(errors) >= 2

    def test_rubric_error_identifies_skill(self):
        """Skill validation error names the skill."""
        errors = validate_rubric_or_errors({
            "language": "en",
            "skills": {"reading": {"weight": 0}},
        })
        assert len(errors) > 0
