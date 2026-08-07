"""Pydantic schema validation for NokaMan rubrics, samples, and listening packs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, ValidationError, model_validator

CEFR_VALUES = {"A1", "A2", "B1", "B2", "C1", "C2"}
VALID_SKILLS = {"vocabulary", "grammar", "reading", "writing", "listening", "speaking"}
VALID_LANGUAGES = {
    "en", "ko", "ja", "vi", "zh", "es", "fr", "de", "pt", "it",
    "nl", "sv", "pl", "tr", "id", "th", "hi", "ar", "ru", "uk",
    "cs", "ro", "el", "hu", "fi", "nb", "da", "sk",
}


class SkillRubric(BaseModel):
    """A single skill entry within a language rubric."""

    weight: float = Field(default=1.0, ge=0.0, le=10.0)
    notes: str = ""


class LanguageRubric(BaseModel):
    """Full rubric for one language, loaded from data/rubrics/<code>.json."""

    language: str = Field(min_length=2, max_length=8)
    name: str = ""
    skills: dict[str, SkillRubric] = Field(default_factory=dict)
    bands: list[str] = Field(default_factory=lambda: list(CEFR_VALUES))

    @model_validator(mode="after")
    def _validate_skills(self) -> LanguageRubric:
        unknown = set(self.skills) - VALID_SKILLS
        if unknown:
            raise ValueError(f"Unknown rubric skills: {sorted(unknown)}. Valid: {sorted(VALID_SKILLS)}")
        return self

    @model_validator(mode="after")
    def _validate_bands(self) -> LanguageRubric:
        unknown = set(self.bands) - CEFR_VALUES
        if unknown:
            raise ValueError(f"Unknown CEFR bands: {sorted(unknown)}. Valid: {sorted(CEFR_VALUES)}")
        return self


class FluencyObservations(BaseModel):
    """Optional fluency observations in a speaking sample."""

    duration_seconds: float | None = Field(default=None, gt=0)
    pause_count: int | None = Field(default=None, ge=0)
    filler_count: int | None = Field(default=None, ge=0)


class SamplePayload(BaseModel):
    """A single language sample (writing or speaking)."""

    id: str = ""
    language: str = Field(default="en", min_length=2, max_length=8)
    skill: str = Field(default="writing")
    expected_cefr: str | None = None
    text: str = ""
    fluency_observations: FluencyObservations | None = None

    @model_validator(mode="after")
    def _validate_skill(self) -> SamplePayload:
        if self.skill not in VALID_SKILLS:
            raise ValueError(
                f"Unknown skill {self.skill!r}. Valid: {sorted(VALID_SKILLS)}"
            )
        return self

    @model_validator(mode="after")
    def _validate_cefr(self) -> SamplePayload:
        if self.expected_cefr is not None and self.expected_cefr not in CEFR_VALUES:
            raise ValueError(
                f"Unknown CEFR level {self.expected_cefr!r}. Valid: {sorted(CEFR_VALUES)}"
            )
        return self


class ListeningQuestion(BaseModel):
    """A single question in a listening pack."""

    prompt: str = ""
    options: list[str] = Field(default_factory=list)
    correct_index: int | None = None
    transcript: str = ""


class ListeningPack(BaseModel):
    """A listening comprehension pack."""

    id: str = ""
    language: str = Field(default="en", min_length=2, max_length=8)
    items: list[ListeningQuestion] = Field(default_factory=list)


def validate_rubric(data: dict[str, Any]) -> LanguageRubric:
    """Validate a rubric payload, returning the parsed model or raising ValidationError."""
    return LanguageRubric.model_validate(data)


def validate_sample(data: dict[str, Any]) -> SamplePayload:
    """Validate a sample payload, returning the parsed model or raising ValidationError."""
    return SamplePayload.model_validate(data)


def validate_listening_pack(data: dict[str, Any]) -> ListeningPack:
    """Validate a listening pack payload, returning the parsed model or raising ValidationError."""
    return ListeningPack.model_validate(data)


def validate_rubric_file(path: str) -> LanguageRubric:
    """Load and validate a rubric JSON file."""
    import json
    from pathlib import Path

    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_rubric(raw)


def validate_sample_file(path: str) -> SamplePayload:
    """Load and validate a sample JSON file."""
    import json
    from pathlib import Path

    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_sample(raw)
