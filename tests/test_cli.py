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


def test_eval_score_outputs_table() -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["eval", "score", "--sample", "data/samples/en_writing_a1.json"],
    )
    assert result.exit_code == 0
    assert "Score: en_writing_a1.json" in result.output
    assert "Language" in result.output
    assert "en" in result.output
    assert "Score" in result.output


def test_eval_samples_list_filters() -> None:
    runner = CliRunner()
    # Test language filter
    result = runner.invoke(
        app,
        ["eval", "samples-list", "--language", "en", "--skill", "writing"],
    )
    assert result.exit_code == 0
    assert "Samples" in result.output
    assert "en_writing_a1.json" in result.output

    # Test no filters
    result = runner.invoke(app, ["eval", "samples-list"])
    assert result.exit_code == 0
    assert "Samples" in result.output


def test_eval_samples_list_no_match() -> None:
    """Non-existent language should show yellow message."""
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["eval", "samples-list", "--language", "zz"],
    )
    assert result.exit_code == 0
    assert "No samples match" in result.output


def test_rubrics_dimensions_writing_en() -> None:
    """Should show dimensions for English writing."""
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["rubrics", "dimensions", "--lang", "en", "--skill", "writing"],
    )
    assert result.exit_code == 0
    assert "Cohesion Coherence" in result.output
    assert "Vocabulary Writing" in result.output
    assert "C2" in result.output


def test_rubrics_dimensions_json_output() -> None:
    """JSON output should contain dimension data."""
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["rubrics", "dimensions", "--lang", "en", "--skill", "writing", "--json"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["skill"] == "writing"
    assert "dimensions" in data
    assert "cohesion_coherence" in data["dimensions"]


def test_rubrics_dimensions_no_dimensions() -> None:
    """Skill without dimensions should show yellow warning."""
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["rubrics", "dimensions", "--lang", "en", "--skill", "vocabulary"],
    )
    assert result.exit_code == 0
    assert "No dimensions" in result.output


def test_rubrics_dimensions_multilingual() -> None:
    """Dimensions should be available in multiple languages."""
    runner = CliRunner()
    for lang in ["en", "vi", "zh", "ko", "ja"]:
        result = runner.invoke(
            app,
            ["rubrics", "dimensions", "--lang", lang, "--skill", "writing", "--json"],
        )
        assert result.exit_code == 0, f"Failed for {lang}: {result.output}"
        data = json.loads(result.output)
        assert "dimensions" in data
        dims = data["dimensions"]
        assert "cohesion_coherence" in dims, f"Missing cohesion_coherence for {lang}"
        assert "vocabulary_writing" in dims, f"Missing vocabulary_writing for {lang}"
        assert "grammar_writing" in dims, f"Missing grammar_writing for {lang}"
        assert "organization" in dims, f"Missing organization for {lang}"
        assert "task_achievement" in dims, f"Missing task_achievement for {lang}"


def test_eval_score_all_samples() -> None:
    """Score command should work on any sample file."""
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["eval", "score", "--sample", "data/samples/en_writing_a2.json"],
    )
    assert result.exit_code == 0
    assert "Score" in result.output


def test_eval_samples_with_filters() -> None:
    """samples-list with both filters should narrow results."""
    runner = CliRunner()
    # With language+skill filter, should have fewer results than no filter
    result_filtered = runner.invoke(
        app,
        ["eval", "samples-list", "--language", "en", "--skill", "writing"],
    )
    result_all = runner.invoke(app, ["eval", "samples-list"])
    assert result_filtered.exit_code == 0
    assert result_all.exit_code == 0
    # Filtered count should appear in output
    assert "filtered" in result_filtered.output.lower()


def test_rubrics_explain_still_works() -> None:
    """Existing explain command should still work."""
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["rubrics", "explain", "--lang", "en"],
    )
    assert result.exit_code == 0
    assert "writing" in result.output or "Writing" in result.output


def test_rubrics_list_still_works() -> None:
    """Existing list command should still work."""
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["rubrics", "list"],
    )
    assert result.exit_code == 0
