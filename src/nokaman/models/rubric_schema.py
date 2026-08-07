"""Pydantic models for rubric schema validation (#4).

Validates rubric JSON files (data/rubrics/*.json) against a strict schema,
ensuring language codes, skill weights, CEFR bands, and required fields
are all present and well-formed.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

# Known CEFR bands
CEFR_BANDS = frozenset({"A1", "A2", "B1", "B2", "C1", "C2"})

# Valid language codes with at least one rubric
VALID_LANGS = frozenset({
    "en", "ko", "ja", "vi", "zh", "es", "fr", "de", "pt", "it",
    "nl", "sv", "pl", "tr", "id", "th", "hi", "ar", "ru", "uk",
    "cs", "ro", "el", "hu", "fi", "nb", "da", "sk",
})

# Allowed skill names
ALLOWED_SKILLS = frozenset({
    "vocabulary", "grammar", "reading", "writing", "listening", "speaking",
})


class SkillWeight(BaseModel):
    """A single skill entry in a rubric."""

    weight: float = Field(..., gt=0.0, le=5.0, description="Relative weight of this skill (0 < w ≤ 5)")
    notes: str = Field(default="", description="Descriptor or note about this skill")

    @field_validator("notes")
    @classmethod
    def notes_not_empty_strip(cls, v: str) -> str:
        return v.strip()


class RubricSchema(BaseModel):
    """Full rubric schema for one language.

    Validates:
      - language: iso code present and recognised
      - name: non-empty display name
      - skills: at least one skill with valid name and positive weight
      - bands: list of CEFR levels, at least one, all from the canonical set
    """

    language: str = Field(..., min_length=2, max_length=8, description="ISO language code (e.g. en, ko, ja)")
    name: str = Field(default="", min_length=1, max_length=128, description="Display name of the language")
    skills: dict[str, SkillWeight] = Field(..., min_length=1, description="Skill name → weight mapping")
    bands: list[str] = Field(default_factory=lambda: ["A1", "A2", "B1", "B2", "C1", "C2"])

    @field_validator("language")
    @classmethod
    def language_must_be_known(cls, v: str) -> str:
        code = v.strip().lower()
        if code not in VALID_LANGS:
            raise ValueError(
                f"Unknown language code {code!r}. Known: {sorted(VALID_LANGS)}"
            )
        return code

    @field_validator("name")
    @classmethod
    def name_non_empty(cls, v: str, info: Any) -> str:
        v = (v or "").strip()
        if not v:
            # fall back to language code if name missing
            lang = str(info.data.get("language") or "?")
            return lang
        return v

    @field_validator("skills")
    @classmethod
    def skills_valid_names(cls, v: dict[str, Any]) -> dict[str, Any]:
        for skill_name in v:
            if skill_name.lower() not in ALLOWED_SKILLS:
                raise ValueError(
                    f"Unknown skill {skill_name!r}. Allowed: {sorted(ALLOWED_SKILLS)}"
                )
        if not v:
            raise ValueError("At least one skill is required")
        return v

    @field_validator("bands")
    @classmethod
    def bands_valid(cls, v: list[str]) -> list[str]:
        for band in v:
            if band.strip() not in CEFR_BANDS:
                raise ValueError(
                    f"Unknown CEFR band {band!r}. Allowed: {sorted(CEFR_BANDS)}"
                )
        if not v:
            raise ValueError("At least one CEFR band is required")
        return v

    @model_validator(mode="after")
    def check_name_language_consistency(self) -> "RubricSchema":
        # If name equals the language code and it looks like a code (2-3 chars),
        # that's a sign it was never properly filled — warn but don't block.
        return self


class RubricValidationResult(BaseModel):
    """Result of validating a rubric file."""

    path: str
    valid: bool
    errors: list[str] = Field(default_factory=list)
    rubric: dict[str, Any] | None = None


def validate_rubric_file(path: str) -> RubricValidationResult:
    """Load and validate a single rubric JSON file against the schema."""
    import json
    from pathlib import Path

    pp = Path(path)
    errors: list[str] = []
    raw: dict[str, Any] = {}

    try:
        raw = json.loads(pp.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return RubricValidationResult(path=str(pp), valid=False, errors=[str(exc)])

    try:
        RubricSchema.model_validate(raw)
    except Exception as exc:
        errors.append(str(exc))
        return RubricValidationResult(path=str(pp), valid=False, errors=errors, rubric=raw)

    return RubricValidationResult(path=str(pp), valid=True, errors=[], rubric=raw)


def validate_all_rubrics(rubrics_dir: str | None = None) -> list[RubricValidationResult]:
    """Validate every rubric JSON in the rubrics directory."""
    from pathlib import Path

    from nokaman.config import RUBRICS_DIR

    root = Path(rubrics_dir) if rubrics_dir else RUBRICS_DIR
    results: list[RubricValidationResult] = []
    for path in sorted(root.glob("*.json")):
        results.append(validate_rubric_file(str(path)))
    return results
