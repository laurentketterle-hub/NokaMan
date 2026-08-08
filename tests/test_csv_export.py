"""Tests for batch evaluate CSV export (Closes #32)."""
import tempfile
from pathlib import Path
from nokaman.csv_export import results_to_csv, batch_evaluate_csv, format_csv_preview


def dummy_evaluate(text):
    return {
        "score": 85.5,
        "dimensions": {"fluency": 90, "accuracy": 80},
        "word_count": len(text.split()),
    }


class TestResultsToCsv:
    def test_empty_results(self):
        csv_out = results_to_csv([])
        assert "sample_id" in csv_out

    def test_single_result(self):
        results = [{"sample_id": "s1", "score": 90, "word_count": 100, "dimensions": {"fluency": 92}}]
        csv_out = results_to_csv(results)
        assert "s1" in csv_out
        assert "90" in csv_out
        assert "fluency" in csv_out

    def test_multiple_dimensions(self):
        results = [
            {"sample_id": "a", "score": 80, "word_count": 50, "dimensions": {"fluency": 85, "accuracy": 75}},
            {"sample_id": "b", "score": 90, "word_count": 60, "dimensions": {"fluency": 95, "accuracy": 88}},
        ]
        csv_out = results_to_csv(results)
        lines = csv_out.strip().split("\n")
        assert len(lines) == 3  # header + 2 data rows

    def test_write_to_file(self, tmp_path):
        results = [{"sample_id": "x", "score": 70, "word_count": 30, "dimensions": {}}]
        outpath = tmp_path / "results.csv"
        msg = results_to_csv(results, str(outpath))
        assert "CSV written" in msg
        assert outpath.exists()

    def test_missing_dimensions_handled(self):
        results = [{"sample_id": "only_id"}]
        csv_out = results_to_csv(results)
        assert "only_id" in csv_out


class TestBatchEvaluateCsv:
    def test_batch_with_evaluate_fn(self):
        samples = [
            {"sample_id": "s1", "text": "Hello world"},
            {"sample_id": "s2", "text": "Another test"},
        ]
        csv_out = batch_evaluate_csv(samples, dummy_evaluate)
        assert "s1" in csv_out
        assert "s2" in csv_out
        assert "85.5" in csv_out

    def test_batch_error_handling(self):
        def failing_eval(text):
            raise ValueError("test error")
        samples = [{"sample_id": "bad", "text": "x"}]
        csv_out = batch_evaluate_csv(samples, failing_eval)
        assert "ERROR" in csv_out


class TestFormatCsvPreview:
    def test_preview_with_data(self):
        csv_content = "sample_id,score\ns1,90\ns2,80\ns3,70"
        preview = format_csv_preview(csv_content, max_rows=2)
        assert "s1" in preview
        assert "s2" in preview
        assert "more rows" in preview

    def test_preview_no_data(self):
        preview = format_csv_preview("sample_id\n")
        assert "No data" in preview
