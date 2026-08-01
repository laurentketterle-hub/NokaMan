from __future__ import annotations

import pytest
from nokaman.eval.metrics import batch_evaluate, placement_test, compute_metrics


def test_batch_evaluate() -> None:
    report = batch_evaluate()
    assert report["n_samples"] >= 1
    assert "rows" in report


def test_placement_test() -> None:
    result = placement_test(
        "en",
        [
            "I study English every day and write short notes.",
            "Hello my name is Sam.",
        ],
    )
    assert result["cefr"]
    assert result["n_items"] == 2


class TestComputeMetrics:
    def test_perfect_predictions(self) -> None:
        preds = [
            {"score": 85.0, "cefr": "B2", "expected_score": 85.0, "expected_cefr": "B2"},
            {"score": 45.0, "cefr": "A2", "expected_score": 45.0, "expected_cefr": "A2"},
        ]
        result = compute_metrics(preds)
        assert result["exact_cefr_hit_rate"] == 1.0
        assert result["adjacent_cefr_hit_rate"] == 1.0
        assert result["mae_score"] == 0.0
        assert result["n_labeled"] == 2

    def test_one_band_off(self) -> None:
        preds = [
            {"score": 55.0, "cefr": "B1", "expected_score": 65.0, "expected_cefr": "B2"},
        ]
        result = compute_metrics(preds)
        assert result["exact_cefr_hit_rate"] == 0.0
        assert result["adjacent_cefr_hit_rate"] == 1.0
        assert result["mae_score"] == 10.0
        assert result["n_labeled"] == 1

    def test_two_bands_off(self) -> None:
        preds = [
            {"score": 30.0, "cefr": "A1", "expected_score": 80.0, "expected_cefr": "B2"},
        ]
        result = compute_metrics(preds)
        assert result["exact_cefr_hit_rate"] == 0.0
        assert result["adjacent_cefr_hit_rate"] == 0.0
        assert result["mae_score"] == 50.0

    def test_mixed_predictions(self) -> None:
        preds = [
            {"score": 82.0, "cefr": "B2", "expected_score": 82.0, "expected_cefr": "B2"},   # exact
            {"score": 60.0, "cefr": "B1", "expected_score": 68.0, "expected_cefr": "B2"},   # adjacent
            {"score": 20.0, "cefr": "A1", "expected_score": 55.0, "expected_cefr": "B1"},   # off by 2
        ]
        result = compute_metrics(preds)
        assert result["exact_cefr_hit_rate"] == pytest.approx(1 / 3, abs=0.01)
        assert result["adjacent_cefr_hit_rate"] == pytest.approx(2 / 3, abs=0.01)
        expected_mae = (0.0 + 8.0 + 35.0) / 3
        assert result["mae_score"] == pytest.approx(expected_mae, abs=0.01)
        assert result["n_labeled"] == 3

    def test_empty_predictions(self) -> None:
        result = compute_metrics([])
        assert result["exact_cefr_hit_rate"] is None
        assert result["adjacent_cefr_hit_rate"] is None
        assert result["mae_score"] is None
        assert result["n_labeled"] == 0

    def test_unlabeled_predictions(self) -> None:
        preds = [
            {"score": 50.0, "cefr": "B1", "expected_score": None, "expected_cefr": None},
            {"score": 70.0, "cefr": "B2", "expected_score": None, "expected_cefr": None},
        ]
        result = compute_metrics(preds)
        assert result["n_labeled"] == 0
        assert result["exact_cefr_hit_rate"] is None

    def test_partial_labels(self) -> None:
        preds = [
            {"score": 50.0, "cefr": "B1", "expected_score": 50.0, "expected_cefr": "B1"},
            {"score": 70.0, "cefr": "B2", "expected_score": None, "expected_cefr": None},
        ]
        result = compute_metrics(preds)
        assert result["n_labeled"] == 1
        assert result["exact_cefr_hit_rate"] == 1.0
