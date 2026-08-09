from __future__ import annotations

import json

from typer.testing import CliRunner

from nokaman.cli import app


def test_eval_batch_writes_nested_output_path(tmp_path) -> None:
    out_path = tmp_path / "data" / "out" / "batch.json"
    result = CliRunner().invoke(
        app,
        ["eval", "batch", "--out", str(out_path), "--json-only"],
    )

    assert result.exit_code == 0, result.output
    assert out_path.exists()
    report = json.loads(out_path.read_text(encoding="utf-8"))
    assert report["n_samples"] >= 1
    assert "by_language" in report
    assert "rows" in report


def test_score_command_with_sample(tmp_path) -> None:
    """nokaman score --sample path outputs dimension table."""
    sample_path = tmp_path / "test_sample.json"
    sample_path.write_text(
        json.dumps({
            "id": "test_en_writing_a2",
            "language": "en",
            "skill": "writing",
            "expected_cefr": "A2",
            "text": "I like learning languages. It is fun and useful for travel and work.",
        }),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        ["score", "--sample", str(sample_path)],
    )

    assert result.exit_code == 0, result.output
    assert "Score" in result.output
    assert "CEFR" in result.output
    assert "Language" in result.output


def test_score_command_json_output(tmp_path) -> None:
    """nokaman score --sample path --json outputs valid JSON to stdout."""
    sample_path = tmp_path / "test_sample.json"
    sample_path.write_text(
        json.dumps({
            "id": "test_en_writing_b1",
            "language": "en",
            "skill": "writing",
            "text": "The restaurant was excellent and the service was impeccable.",
        }),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        ["score", "--sample", str(sample_path), "--json"],
    )

    assert result.exit_code == 0, result.output
    output = result.output.strip()
    # JSON output should contain key fields
    assert "language" in output
    assert "score" in output
    assert "cefr" in output
    data = json.loads(output)
    assert isinstance(data["score"], (int, float))


def test_score_with_expected_cefr(tmp_path) -> None:
    """nokaman score with expected_cefr shows band comparison."""
    sample_path = tmp_path / "test_sample.json"
    sample_path.write_text(
        json.dumps({
            "id": "test_ja_writing_n4",
            "language": "ja",
            "skill": "writing",
            "expected_cefr": "A2",
            "text": "日本語を勉強しています。毎日少しずつ練習しています。",
        }),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        ["score", "--sample", str(sample_path)],
    )

    assert result.exit_code == 0, result.output
    assert "Expected CEFR" in result.output
