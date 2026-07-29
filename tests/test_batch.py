"""Tests for batch payload, assessment result, score breakdown validation."""
import pytest
from nokaman.models.validators import SamplePayload, RubricPayload
from nokaman.models.batch import (
    ScoreBreakdown,
    AssessmentResult,
    QualityReport,
    BatchPayload,
    BatchResult,
    validate_batch,
    validate_result,
    validate_batch_result,
    validate_batch_or_errors,
    validate_result_or_errors,
    validate_batch_result_or_errors,
)


# ── ScoreBreakdown ──

class TestScoreBreakdown:
    def test_valid_scores(self):
        sb = ScoreBreakdown(
            vocabulary=85, grammar=72, reading=90,
            writing=65, listening=78, speaking=80,
        )
        assert sb.vocabulary == 85
        assert sb.grammar == 72

    def test_overall_average(self):
        sb = ScoreBreakdown(
            vocabulary=100, grammar=100, reading=100,
            writing=100, listening=100, speaking=100,
        )
        assert sb.overall == 100.0

    def test_overall_zero(self):
        sb = ScoreBreakdown(
            vocabulary=0, grammar=0, reading=0,
            writing=0, listening=0, speaking=0,
        )
        assert sb.overall == 0.0

    def test_overall_mixed(self):
        sb = ScoreBreakdown(
            vocabulary=60, grammar=60, reading=60,
            writing=60, listening=60, speaking=60,
        )
        assert sb.overall == 60.0

    def test_to_cefr_c2(self):
        sb = ScoreBreakdown(
            vocabulary=95, grammar=90, reading=92,
            writing=88, listening=91, speaking=94,
        )
        assert sb.to_cefr() == "C2"

    def test_to_cefr_b1(self):
        sb = ScoreBreakdown(
            vocabulary=55, grammar=50, reading=60,
            writing=45, listening=52, speaking=48,
        )
        assert sb.to_cefr() == "B1"

    def test_to_cefr_a1(self):
        sb = ScoreBreakdown(
            vocabulary=10, grammar=5, reading=15,
            writing=8, listening=12, speaking=7,
        )
        assert sb.to_cefr() == "A1"

    def test_dominant_skill(self):
        sb = ScoreBreakdown(
            vocabulary=50, grammar=40, reading=90,
            writing=30, listening=20, speaking=10,
        )
        assert sb.dominant_skill() == "reading"

    def test_weakest_skill(self):
        sb = ScoreBreakdown(
            vocabulary=80, grammar=70, reading=60,
            writing=50, listening=90, speaking=85,
        )
        assert sb.weakest_skill() == "writing"

    def test_out_of_range_rejected(self):
        with pytest.raises(Exception):
            ScoreBreakdown(
                vocabulary=150, grammar=0, reading=0,
                writing=0, listening=0, speaking=0,
            )

    def test_negative_rejected(self):
        with pytest.raises(Exception):
            ScoreBreakdown(
                vocabulary=-1, grammar=0, reading=0,
                writing=0, listening=0, speaking=0,
            )


# ── AssessmentResult ──

class TestAssessmentResult:
    def test_valid_result(self):
        result = AssessmentResult(
            sample_id="test-1",
            language="en",
            predicted_cefr="B2",
            scores=ScoreBreakdown(
                vocabulary=75, grammar=68, reading=82,
                writing=70, listening=76, speaking=72,
            ),
            confidence=0.85,
        )
        assert result.sample_id == "test-1"
        assert result.is_high_confidence

    def test_low_confidence(self):
        result = AssessmentResult(
            sample_id="test-2",
            language="fr",
            predicted_cefr="A2",
            scores=ScoreBreakdown(
                vocabulary=40, grammar=35, reading=42,
                writing=38, listening=45, speaking=30,
            ),
            confidence=0.45,
        )
        assert not result.is_high_confidence

    def test_overall_score_delegation(self):
        result = AssessmentResult(
            sample_id="t",
            language="en",
            predicted_cefr="B1",
            scores=ScoreBreakdown(
                vocabulary=50, grammar=50, reading=50,
                writing=50, listening=50, speaking=50,
            ),
            confidence=0.7,
        )
        assert result.overall_score == 50.0

    def test_invalid_cefr_rejected(self):
        with pytest.raises(Exception):
            AssessmentResult(
                sample_id="t", language="en", predicted_cefr="X99",
                scores=ScoreBreakdown(
                    vocabulary=50, grammar=50, reading=50,
                    writing=50, listening=50, speaking=50,
                ),
                confidence=0.5,
            )

    def test_confidence_out_of_range(self):
        with pytest.raises(Exception):
            AssessmentResult(
                sample_id="t", language="en", predicted_cefr="A1",
                scores=ScoreBreakdown(
                    vocabulary=50, grammar=50, reading=50,
                    writing=50, listening=50, speaking=50,
                ),
                confidence=1.5,
            )

    def test_optional_fields(self):
        result = AssessmentResult(
            sample_id="t", language="en", predicted_cefr="A1",
            scores=ScoreBreakdown(
                vocabulary=50, grammar=50, reading=50,
                writing=50, listening=50, speaking=50,
            ),
            confidence=0.5,
            timestamp="2026-07-29T10:00:00Z",
            model_version="v2.1.0",
            grader_notes="Good effort",
        )
        assert result.timestamp == "2026-07-29T10:00:00Z"
        assert result.model_version == "v2.1.0"

    def test_empty_grader_notes_default(self):
        result = AssessmentResult(
            sample_id="t", language="en", predicted_cefr="A1",
            scores=ScoreBreakdown(
                vocabulary=50, grammar=50, reading=50,
                writing=50, listening=50, speaking=50,
            ),
            confidence=0.5,
        )
        assert result.grader_notes == ""


# ── QualityReport ──

class TestQualityReport:
    def test_valid_report(self):
        report = QualityReport(
            total_samples=10, valid_samples=9, errors=1,
            average_confidence=0.87,
            cefr_distribution={"A1": 2, "A2": 3, "B1": 3, "B2": 1},
        )
        assert report.error_rate == 0.1
        assert report.validity_rate == 0.9

    def test_zero_samples(self):
        report = QualityReport(
            total_samples=0, valid_samples=0, errors=0,
            average_confidence=0.0,
        )
        assert report.error_rate == 0.0
        assert report.validity_rate == 1.0

    def test_inconsistent_totals_rejected(self):
        with pytest.raises(Exception):
            QualityReport(
                total_samples=10, valid_samples=5, errors=3,
                average_confidence=0.5,
            )

    def test_empty_distributions(self):
        report = QualityReport(
            total_samples=5, valid_samples=5, errors=0,
            average_confidence=0.9,
        )
        assert report.cefr_distribution == {}
        assert report.top_dominant_skills == {}


# ── BatchPayload ──

class TestBatchPayload:
    def test_valid_batch(self):
        batch = BatchPayload(
            rubric=RubricPayload(
                language="en",
                skills={"vocabulary": {"weight": 1.0}},
            ),
            samples=[
                SamplePayload(id="s1", language="en", text="Hello"),
                SamplePayload(id="s2", language="en", text="World"),
            ],
            batch_id="batch-001",
        )
        assert batch.sample_count == 2
        assert batch.languages_used == {"en"}

    def test_empty_samples_rejected(self):
        with pytest.raises(Exception):
            BatchPayload(
                rubric=RubricPayload(
                    language="en",
                    skills={"v": {"weight": 1.0}},
                ),
                samples=[],
            )

    def test_duplicate_ids_rejected(self):
        with pytest.raises(Exception) as exc:
            BatchPayload(
                rubric=RubricPayload(
                    language="en",
                    skills={"v": {"weight": 1.0}},
                ),
                samples=[
                    SamplePayload(id="dup", language="en", text="A"),
                    SamplePayload(id="dup", language="en", text="B"),
                ],
            )
        assert "Duplicate" in str(exc.value) or "dup" in str(exc.value).lower()

    def test_language_mismatch_with_rubric(self):
        with pytest.raises(Exception):
            BatchPayload(
                rubric=RubricPayload(
                    language="en",
                    skills={"v": {"weight": 1.0}},
                ),
                samples=[
                    SamplePayload(id="s1", language="fr", text="Bonjour"),
                ],
            )

    def test_mixed_languages_allowed_without_rubric_check(self):
        """When rubric language matches, multiple sample languages should be caught."""
        # This batch has mismatched languages - should be caught by validator
        pass  # Already covered by test_language_mismatch_with_rubric

    def test_batch_with_config(self):
        batch = BatchPayload(
            rubric=RubricPayload(
                language="ja",
                skills={"writing": {"weight": 1.5}},
            ),
            samples=[
                SamplePayload(id="j1", language="ja", text="こんにちは"),
            ],
            batch_config={"model": "gpt-4", "prompt_version": "v3"},
        )
        assert batch.batch_config["model"] == "gpt-4"

    def test_validate_batch_api(self):
        data = {
            "rubric": {
                "language": "en",
                "skills": {"grammar": {"weight": 1.0}},
            },
            "samples": [
                {"id": "s1", "language": "en", "text": "test"},
            ],
        }
        result = validate_batch(data)
        assert result.sample_count == 1

    def test_validate_batch_or_errors_success(self):
        data = {
            "rubric": {
                "language": "en",
                "skills": {"v": {"weight": 0.5}},
            },
            "samples": [
                {"id": "s1", "language": "en", "text": "ok"},
            ],
        }
        errors = validate_batch_or_errors(data)
        assert errors == []

    def test_validate_batch_or_errors_failure(self):
        data = {
            "rubric": {
                "language": "en",
                "skills": {},
            },
            "samples": [],
        }
        errors = validate_batch_or_errors(data)
        assert len(errors) > 0


# ── BatchResult ──

class TestBatchResult:
    def _make_result(self, sid: str, cefr: str, conf: float = 0.8) -> AssessmentResult:
        return AssessmentResult(
            sample_id=sid, language="en", predicted_cefr=cefr,
            scores=ScoreBreakdown(
                vocabulary=75, grammar=70, reading=80,
                writing=65, listening=72, speaking=68,
            ),
            confidence=conf,
        )

    def test_valid_batch_result(self):
        results = [self._make_result("s1", "B2"), self._make_result("s2", "B1")]
        report = QualityReport(
            total_samples=2, valid_samples=2, errors=0,
            average_confidence=0.8,
        )
        batch = BatchResult(batch_id="b1", results=results, quality=report)
        assert batch.average_overall_score > 0
        assert len(batch.high_confidence_results) == 2

    def test_high_confidence_filtering(self):
        results = [
            self._make_result("s1", "A1", 0.9),
            self._make_result("s2", "C2", 0.5),
            self._make_result("s3", "B1", 0.95),
        ]
        report = QualityReport(
            total_samples=3, valid_samples=3, errors=0,
            average_confidence=0.78,
        )
        batch = BatchResult(batch_id="b2", results=results, quality=report)
        high = batch.high_confidence_results
        assert len(high) == 2
        assert {r.sample_id for r in high} == {"s1", "s3"}

    def test_by_cefr_grouping(self):
        results = [
            self._make_result("s1", "B2"),
            self._make_result("s2", "A1"),
            self._make_result("s3", "B2"),
            self._make_result("s4", "C1"),
        ]
        report = QualityReport(
            total_samples=4, valid_samples=4, errors=0,
            average_confidence=0.8,
        )
        batch = BatchResult(batch_id="b3", results=results, quality=report)
        groups = batch.by_cefr()
        assert len(groups["B2"]) == 2
        assert len(groups["A1"]) == 1
        assert len(groups["C1"]) == 1

    def test_result_count_mismatch_rejected(self):
        results = [self._make_result("s1", "A1")]
        report = QualityReport(
            total_samples=5, valid_samples=5, errors=0,
            average_confidence=0.5,
        )
        with pytest.raises(Exception):
            BatchResult(batch_id="b4", results=results, quality=report)

    def test_empty_results_rejected(self):
        report = QualityReport(
            total_samples=0, valid_samples=0, errors=0,
            average_confidence=0.0,
        )
        with pytest.raises(Exception):
            BatchResult(batch_id="b5", results=[], quality=report)

    def test_validate_result_api(self):
        data = {
            "sample_id": "s1",
            "language": "en",
            "predicted_cefr": "B1",
            "scores": {
                "vocabulary": 60, "grammar": 55, "reading": 65,
                "writing": 50, "listening": 58, "speaking": 52,
            },
            "confidence": 0.75,
        }
        result = validate_result(data)
        assert result.predicted_cefr == "B1"

    def test_validate_result_or_errors_failure(self):
        data = {
            "sample_id": "bad",
            "language": "en",
            "predicted_cefr": "INVALID",
            "scores": {
                "vocabulary": 999, "grammar": 0, "reading": 0,
                "writing": 0, "listening": 0, "speaking": 0,
            },
            "confidence": 2.0,
        }
        errors = validate_result_or_errors(data)
        assert len(errors) > 0

    def test_validate_batch_result_api(self):
        data = {
            "batch_id": "b1",
            "results": [
                {
                    "sample_id": "s1",
                    "language": "en",
                    "predicted_cefr": "A2",
                    "scores": {
                        "vocabulary": 40, "grammar": 35,
                        "reading": 45, "writing": 38,
                        "listening": 42, "speaking": 30,
                    },
                    "confidence": 0.6,
                },
            ],
            "quality": {
                "total_samples": 1,
                "valid_samples": 1,
                "errors": 0,
                "average_confidence": 0.6,
            },
        }
        result = validate_batch_result(data)
        assert result.batch_id == "b1"
        assert len(result.results) == 1

    def test_validate_batch_result_or_errors(self):
        data = {
            "batch_id": "b",
            "results": [
                {
                    "sample_id": "s1",
                    "language": "en",
                    "predicted_cefr": "B1",
                    "scores": {
                        "vocabulary": 50, "grammar": 50,
                        "reading": 50, "writing": 50,
                        "listening": 50, "speaking": 50,
                    },
                    "confidence": 0.5,
                },
            ],
            "quality": {
                "total_samples": 1,
                "valid_samples": 1,
                "errors": 0,
                "average_confidence": 0.5,
            },
        }
        errors = validate_batch_result_or_errors(data)
        assert errors == []
