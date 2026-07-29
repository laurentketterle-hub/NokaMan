"""Pydantic models for rubric + sample JSON validation with clear error messages."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, ValidationError, model_validator


# --- Sample Models ---

class SamplePayload(BaseModel):
    """Validates a NokaMan assessment sample JSON payload."""
    id: str = Field(min_length=1, description="Unique sample identifier")
    language: str = Field(min_length=2, max_length=10, description="ISO language code (e.g. 'en', 'ja')")
    skill: str = Field(default="writing", description="Assessed skill")
    text: str = Field(min_length=1, description="Text content to assess")
    expected_cefr: str | None = Field(
        default=None, pattern=r"^(A1|A2|B1|B2|C1|C2)$",
        description="Expected CEFR band if known"
    )

    @model_validator(mode="after")
    def _check_language_lower(self) -> "SamplePayload":
        if self.language != self.language.lower():
            raise ValueError(f"language must be lowercase; got {self.language!r}")
        return self


# --- Rubric Models ---

class SkillRubric(BaseModel):
    """A single skill rubric entry."""
    weight: float = Field(gt=0, description="Skill weight (>0)")
    notes: str = Field(default="", description="Skill descriptor")


class RubricPayload(BaseModel):
    """Validates a NokaMan rubric JSON payload."""
    language: str = Field(min_length=2, max_length=10, description="ISO language code")
    name: str = Field(default="", description="Display name")
    skills: dict[str, SkillRubric] = Field(default_factory=dict, description="Skill name → rubric")
    bands: list[str] = Field(
        default_factory=lambda: ["A1", "A2", "B1", "B2", "C1", "C2"],
        description="CEFR bands"
    )

    @model_validator(mode="after")
    def _check_language_lower(self) -> "RubricPayload":
        if self.language != self.language.lower():
            raise ValueError(f"language must be lowercase; got {self.language!r}")
        return self

    @model_validator(mode="after")
    def _check_bands_known(self) -> "RubricPayload":
        known = {"A1", "A2", "B1", "B2", "C1", "C2"}
        unknown = [b for b in self.bands if b not in known]
        if unknown:
            raise ValueError(
                f"Unknown CEFR band(s): {unknown}. Must be one of {sorted(known)}"
            )
        return self

    @model_validator(mode="after")
    def _check_no_empty_skills(self) -> "RubricPayload":
        if not self.skills:
            raise ValueError("rubric must have at least one skill")
        return self


# --- Public API ---

def validate_sample(data: dict[str, Any]) -> SamplePayload:
    """Validate a sample dict. Returns the parsed model or raises ValidationError."""
    return SamplePayload.model_validate(data)


def validate_rubric(data: dict[str, Any]) -> RubricPayload:
    """Validate a rubric dict. Returns the parsed model or raises ValidationError."""
    return RubricPayload.model_validate(data)


def validate_sample_or_errors(data: dict[str, Any]) -> list[str]:
    """Return a list of human-readable validation errors for a sample (empty = valid)."""
    try:
        validate_sample(data)
        return []
    except ValidationError as e:
        return _format_errors(e)


def validate_rubric_or_errors(data: dict[str, Any]) -> list[str]:
    """Return a list of human-readable validation errors for a rubric (empty = valid)."""
    try:
        validate_rubric(data)
        return []
    except ValidationError as e:
        return _format_errors(e)


def _format_errors(exc: ValidationError) -> list[str]:
    """Format pydantic ValidationError into human-readable messages."""
    messages: list[str] = []
    for err in exc.errors():
        loc = " → ".join(str(p) for p in err["loc"]) if err["loc"] else "root"
        msg = err["msg"]
        ctx = err.get("ctx", {})
        
        # Make messages more helpful
        if err["type"] == "string_too_short":
            msg = f"must be at least {ctx.get('min_length', '?')} character(s)"
        elif err["type"] == "string_too_long":
            msg = f"must be at most {ctx.get('max_length', '?')} characters"
        elif err["type"] == "missing":
            msg = "is required"
        elif err["type"] == "string_pattern_mismatch":
            msg = f"must match pattern {ctx.get('pattern', '?')}"
        elif err["type"] == "greater_than":
            msg = f"must be greater than {ctx.get('gt', '?')}"
        
        messages.append(f"{loc}: {msg}")
    return messages
