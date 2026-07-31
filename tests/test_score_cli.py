"""Tests for nokaman eval score CLI command — rich table output."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from nokaman.cli import app


def test_eval_score_text_table() -> None:
    """Score text should produce a rich table with all 6 skill dimensions."""
    result = CliRunner().invoke(
        app,
        ["eval", "score", "--text", "The weather is beautiful today.", "--lang", "en"],
    )
    assert result.exit_code == 0, result.output
    out = result.output
    assert "Overall" in out
    assert "CEFR" in out
    for dim in ("Writing", "Vocabulary", "Grammar", "Reading", "Listening", "Speaking"):
        assert dim in out, f"Missing dimension: {dim}"
    assert "Feature Breakdown" in out
    assert "Token count" in out


def test_eval_score_text_json() -> None:
    """--json should output valid JSON with expected keys."""
    result = CliRunner().invoke(
        app,
        [
            "eval", "score", "--text", "Hello world",
            "--lang", "en", "--skill", "writing", "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert "score" in data
    assert "cefr" in data
    assert "language" in data
    assert "skill" in data


def test_eval_score_no_input() -> None:
    """Without --sample or --text should exit with code 1."""
    result = CliRunner().invoke(app, ["eval", "score"])
    assert result.exit_code == 1, result.output
    assert "Provide" in result.output


def test_eval_score_verbose() -> None:
    """--verbose should still succeed."""
    result = CliRunner().invoke(
        app,
        [
            "eval", "score", "--text", "Because the sun was warm, I walked outside.",
            "--lang", "en", "--verbose",
        ],
    )
    assert result.exit_code == 0, result.output


def test_eval_score_with_skill_option() -> None:
    """--skill should not crash and table should render."""
    result = CliRunner().invoke(
        app,
        [
            "eval", "score", "--text", "I wrote a long essay about history.",
            "--lang", "en", "--skill", "grammar",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "grammar" in result.output.lower()


def test_eval_score_sample_file_exists() -> None:
    """Score a real sample file from the data directory."""
    sample_path = "data/samples/en_writing_b1.json"
    result = CliRunner().invoke(
        app, ["eval", "score", "--sample", sample_path],
    )
    assert result.exit_code == 0, result.output
    out = result.output
    assert "Overall" in out
    assert "CEFR" in out
    assert "Expected CEFR" in out


def test_eval_score_sample_nonexistent_file() -> None:
    """Nonexistent sample path should fail (exists=True enforced by typer)."""
    result = CliRunner().invoke(
        app, ["eval", "score", "--sample", "nonexistent_file.json"],
    )
    assert result.exit_code != 0


def test_eval_score_french_text() -> None:
    """French text should produce a table with French language label."""
    result = CliRunner().invoke(
        app,
        [
            "eval", "score", "--text", "Bonjour, je m'appelle Marie.",
            "--lang", "fr",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "fr" in result.output.lower() or "FR" in result.output


def test_eval_score_korean_text() -> None:
    """Korean text should produce a table with framework bands."""
    result = CliRunner().invoke(
        app,
        [
            "eval", "score", "--text",
            "안녕하세요. 저는 한국어를 공부하고 있습니다.",
            "--lang", "ko",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "TOPIK" in result.output


def test_eval_score_japanese_text() -> None:
    """Japanese text should show JLPT framework."""
    result = CliRunner().invoke(
        app,
        [
            "eval", "score", "--text",
            "こんにちは。私は日本語を勉強しています。",
            "--lang", "ja",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "JLPT" in result.output


def test_eval_score_short_text() -> None:
    """Short text should not crash and produce a table."""
    result = CliRunner().invoke(
        app, ["eval", "score", "--text", "Hi.", "--lang", "en"],
    )
    assert result.exit_code == 0, result.output


def test_eval_score_empty_text() -> None:
    """Empty text should still produce output without crashing."""
    result = CliRunner().invoke(
        app, ["eval", "score", "--text", "", "--lang", "en"],
    )
    assert result.exit_code == 0, result.output


def test_eval_score_json_no_table() -> None:
    """--json should NOT contain rich markup."""
    result = CliRunner().invoke(
        app,
        [
            "eval", "score", "--text", "Test text.",
            "--lang", "en", "--json",
        ],
    )
    assert result.exit_code == 0
    # Rich markup uses [] tags — JSON output should not have them
    data = json.loads(result.output)
    assert isinstance(data, dict)


def test_eval_score_multiple_languages() -> None:
    """Each supported language with demo text should succeed."""
    tests = [
        ("en", "I like learning languages."),
        ("es", "Me gusta aprender idiomas."),
        ("vi", "Tôi thích học ngôn ngữ."),
        ("zh", "我喜欢学习语言。"),
        ("de", "Ich lerne gerne Sprachen."),
    ]
    for lang_code, txt in tests:
        result = CliRunner().invoke(
            app,
            ["eval", "score", "--text", txt, "--lang", lang_code, "--json"],
        )
        assert result.exit_code == 0, f"Failed for {lang_code}: {result.output}"
        data = json.loads(result.output)
        assert data.get("language") == lang_code, f"Wrong language for {lang_code}"
