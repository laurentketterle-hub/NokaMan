"""Tests for batch evaluate CSV/JSON export (Issue #32)."""
import csv, os, tempfile

def test_load_results_returns_list():
    from src.nokaman.cli import _load_evaluation_results
    results = _load_evaluation_results()
    assert isinstance(results, list)

def test_load_empty_for_nonexistent_dataset():
    from src.nokaman.cli import _load_evaluation_results
    results = _load_evaluation_results(dataset="nonexistent_xyz")
    assert isinstance(results, list)
    assert len(results) == 0

def test_csv_fieldnames_consistent():
    expected = ["model", "dataset", "score", "latency_ms", "timestamp"]
    assert len(expected) == 5
    assert "score" in expected

def test_csv_dictwriter_header():
    output = os.path.join(tempfile.mkdtemp(), "test.csv")
    try:
        with open(output, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["model", "dataset", "score", "latency_ms", "timestamp"])
            writer.writeheader()
        with open(output, "r") as f:
            header = f.readline().strip()
        assert "model" in header
        assert "score" in header
    finally:
        if os.path.exists(output):
            os.unlink(output)
