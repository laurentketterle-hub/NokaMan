"""Tests for samples list and stats commands."""
import json
import subprocess
import sys
from pathlib import Path


def _run_nokaman(*args: str) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(
        [sys.executable, "-m", "nokaman.cli"] + list(args),
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_samples_list_all():
    """All samples listed without filters."""
    result = _run_nokaman("samples", "list")
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "Sample" in result.stdout or "sample" in result.stdout.lower()


def test_samples_list_filter_language():
    """Filter by language code."""
    result = _run_nokaman("samples", "list", "--language", "en")
    assert result.returncode == 0, f"stderr: {result.stderr}"


def test_samples_list_filter_skill():
    """Filter by skill name."""
    result = _run_nokaman("samples", "list", "--skill", "reading")
    assert result.returncode == 0, f"stderr: {result.stderr}"


def test_samples_list_filter_both():
    """Filter by both language and skill."""
    result = _run_nokaman("samples", "list", "--language", "en", "--skill", "reading")
    assert result.returncode == 0, f"stderr: {result.stderr}"


def test_samples_list_no_match():
    """No samples match — should not crash."""
    result = _run_nokaman("samples", "list", "--language", "zz")
    assert result.returncode == 0, f"stderr: {result.stderr}"


def test_samples_stats_all():
    """Stats for all samples."""
    result = _run_nokaman("samples", "stats")
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "Language" in result.stdout or "language" in result.stdout.lower()


def test_samples_stats_filter_language():
    """Stats filtered by language."""
    result = _run_nokaman("samples", "stats", "--language", "en")
    assert result.returncode == 0, f"stderr: {result.stderr}"


def test_samples_stats_filter_skill():
    """Stats filtered by skill."""
    result = _run_nokaman("samples", "stats", "--skill", "reading")
    assert result.returncode == 0, f"stderr: {result.stderr}"


def test_samples_help():
    """Help output includes subcommands."""
    result = _run_nokaman("samples", "--help")
    assert result.returncode == 0
    assert "list" in result.stdout.lower()
    assert "stats" in result.stdout.lower()
