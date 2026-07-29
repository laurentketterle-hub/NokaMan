"""Extended Pydantic validators for NokaMan: BatchPayload, AssessmentResult,
ScoreBreakdown, QualityReport.

Adds comprehensive validation for batch evaluation inputs and outputs,
with clear error messages and cross-field validation rules.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, ValidationError, model_validator, field_validator

from nokaman.models.validators import SamplePayload, RubricPayload
from nokaman.rubrics.registry import CEFR_BANDS, SKILLS


# ── Score breakdown ──

class ScoreBreakdown(BaseModel):
    """Per-skill score breakdown with CEFR mapping."""
    vocabulary: float = Field(ge=0, le=100, description="Vocabulary score (0-100)")
    grammar: float = Field(ge=0, le=100, description="Grammar score (0-100)")
    reading: float = Field(ge=0, le=100, description="Reading score (0-100)")
    writing: float = Field(ge=0, le=100, description="Writing score (0-100)")
    listening: float = Field(ge=0, le=100, description="Listening score (0-100)")
    speaking: float = Field(ge=0, le=100, description="Speaking score (0-100)")

    @property
    def overall(self) -> float:
        """Weighted overall score."""
        return sum([
            self.vocabulary,
            self.grammar,
            self.reading,
            self.writing,
            self.listening,
            self.speaking,
        ]) / 6.0

    def to_cefr(self) -> str:
        """Map overall score to CEFR band."""
        s = self.overall
        if s >= 90:
            return "C2"
        elif s >= 80:
            return "C1"
        elif s >= 65:
            return "B2"
        elif s >= 50:
            return "B1"
        elif s >= 35:
            return "A2"
        return "A1"

    def dominant_skill(self) -> str:
        """Return the skill with the highest score."""
        scores = {
            "vocabulary": self.vocabulary,
            "grammar": self.grammar,
            "reading": self.reading,
            "writing": self.writing,
            "listening": self.listening,
            "speaking": self.speaking,
        }
        return max(scores, key=scores.get)

    def weakest_skill(self) -> str:
        """Return the skill with the lowest score."""
        scores = {
            "vocabulary": self.vocabulary,
            "grammar": self.grammar,
            "reading": self.reading,
            "writing": self.writing,
            "listening": self.listening,
            "speaking": self.speaking,
        }
        return min(scores, key=scores.get)


# ── Assessment result ──

class AssessmentResult(BaseModel):
    """Single assessment result for one sample."""
    sample_id: str = Field(min_length=1, description="Sample identifier")
    language: str = Field(min_length=2, max_length=10, description="Language code")
    predicted_cefr: str = Field(pattern=r"^(A1|A2|B1|B2|C1|C2)$", description="Predicted CEFR band")
    scores: ScoreBreakdown
    confidence: float = Field(ge=0.0, le=1.0, description="Model confidence (0-1)")
    timestamp: str | None = Field(default=None, description="ISO timestamp")
    model_version: str | None = Field(default=None, description="Model version")
    grader_notes: str = Field(default="", description="Grader commentary")

    @property
    def is_high_confidence(self) -> bool:
        return self.confidence >= 0.8

    @property
    def overall_score(self) -> float:
        return self.scores.overall


# ── Quality report ──

class QualityReport(BaseModel):
    """Quality assessment report for batch evaluations."""
    total_samples: int = Field(ge=0, description="Total samples assessed")
    valid_samples: int = Field(ge=0, description="Validly assessed samples")
    errors: int = Field(ge=0, description="Error count")
    average_confidence: float = Field(ge=0.0, le=1.0, description="Mean confidence")
    cefr_distribution: dict[str, int] = Field(
        default_factory=dict, description="CEFR band → count"
    )
    top_dominant_skills: dict[str, int] = Field(
        default_factory=dict, description="Skill → count of dominance"
    )
    warnings: list[str] = Field(default_factory=list, description="Warnings/issues")

    @model_validator(mode="after")
    def _check_totals_consistent(self) -> "QualityReport":
        if self.valid_samples + self.errors != self.total_samples:
            raise ValueError(
                f"valid_samples ({self.valid_samples}) + errors ({self.errors}) "
                f"!= total_samples ({self.total_samples})"
            )
        return self

    @property
    def error_rate(self) -> float:
        if self.total_samples == 0:
            return 0.0
        return self.errors / self.total_samples

    @property
    def validity_rate(self) -> float:
        if self.total_samples == 0:
            return 1.0
        return self.valid_samples / self.total_samples


# ── Batch payload ──

class BatchPayload(BaseModel):
    """Batch evaluation payload: multiple samples + rubric for assessment."""
    rubric: RubricPayload
    samples: list[SamplePayload] = Field(min_length=1, description="At least one sample required")
    batch_id: str = Field(default="", description="Optional batch identifier")
    batch_config: dict[str, Any] = Field(
        default_factory=dict, description="Extra config (e.g., model, prompt)"
    )

    @field_validator("samples")
    @classmethod
    def _check_language_consistency(cls, v: list[SamplePayload], info: Any) -> list[SamplePayload]:
        """All samples should match the rubric language."""
        rubric_lang = info.data.get("rubric")
        if rubric_lang and hasattr(rubric_lang, "language"):
            mismatches = [
                s.id for s in v if s.language != rubric_lang.language
            ]
            if mismatches:
                raise ValueError(
                    f"Sample language mismatch with rubric "
                    f"({rubric_lang.language}): {mismatches}"
                )
        return v

    @model_validator(mode="after")
    def _check_no_duplicate_ids(self) -> "BatchPayload":
        ids = [s.id for s in self.samples]
        dups = {i for i in ids if ids.count(i) > 1}
        if dups:
            raise ValueError(f"Duplicate sample IDs: {dups}")
        return self

    @property
    def sample_count(self) -> int:
        return len(self.samples)

    @property
    def languages_used(self) -> set[str]:
        return {s.language for s in self.samples}


# ── Batch result ──

class BatchResult(BaseModel):
    """Results for a batch evaluation."""
    batch_id: str = Field(min_length=1, description="Batch identifier")
    results: list[AssessmentResult] = Field(min_length=1, description="At least one result")
    quality: QualityReport

    @model_validator(mode="after")
    def _check_result_count_matches_report(self) -> "BatchResult":
        if self.quality.total_samples != len(self.results):
            raise ValueError(
                f"Report total_samples ({self.quality.total_samples}) "
                f"!= results count ({len(self.results)})"
            )
        return self

    @property
    def high_confidence_results(self) -> list[AssessmentResult]:
        return [r for r in self.results if r.is_high_confidence]

    @property
    def average_overall_score(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.overall_score for r in self.results) / len(self.results)

    def by_cefr(self) -> dict[str, list[AssessmentResult]]:
        """Group results by predicted CEFR band."""
        groups: dict[str, list[AssessmentResult]] = {}
        for r in self.results:
            groups.setdefault(r.predicted_cefr, []).append(r)
        return groups


# ── Public validation API ──

def validate_batch(data: dict[str, Any]) -> BatchPayload:
    """Validate a batch payload."""
    return BatchPayload.model_validate(data)


def validate_result(data: dict[str, Any]) -> AssessmentResult:
    """Validate a single assessment result."""
    return AssessmentResult.model_validate(data)


def validate_batch_result(data: dict[str, Any]) -> BatchResult:
    """Validate a batch result."""
    return BatchResult.model_validate(data)


def validate_batch_or_errors(data: dict[str, Any]) -> list[str]:
    """Return list of human-readable errors for a batch (empty = valid)."""
    try:
        validate_batch(data)
        return []
    except ValidationError as e:
        from nokaman.models.validators import _format_errors
        return _format_errors(e)


def validate_result_or_errors(data: dict[str, Any]) -> list[str]:
    """Return list of human-readable errors for a result (empty = valid)."""
    try:
        validate_result(data)
        return []
    except ValidationError as e:
        from nokaman.models.validators import _format_errors
        return _format_errors(e)


def validate_batch_result_or_errors(data: dict[str, Any]) -> list[str]:
    """Return list of human-readable errors for batch result (empty = valid)."""
    try:
        validate_batch_result(data)
        return []
    except ValidationError as e:
        from nokaman.models.validators import _format_errors
        return _format_errors(e)
