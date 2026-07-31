"""Tests for samples list, stats, and info commands with catalog helpers."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from nokaman.data.loader import (
    catalog_samples,
    filter_catalog,
    list_sample_files,
    sample_info,
    summary_by_cefr,
    summary_by_language,
    summary_by_skill,
)


# ── helpers ──────────────────────────────────────────────────────────

def _run_nokaman(*args: str) -> "subprocess.CompletedProcess[str]":
    """Invoke the nokaman CLI in a subprocess."""
    import os

    env = os.environ.copy()
    # Ensure the project root is on PYTHONPATH so `nokaman` is importable
    project_root = str(Path(__file__).resolve().parents[1] / "src")
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = project_root + (";" + existing if existing else "")
    return subprocess.run(
        [sys.executable, "-m", "nokaman.cli"] + list(args),
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )


def _repo_samples_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "samples"


SAMPLES_DIR = _repo_samples_dir()


# ── loader / catalog tests ──────────────────────────────────────────


class TestCatalogSamples:
    def test_returns_all_records(self):
        records = catalog_samples(SAMPLES_DIR)
        files = list_sample_files(SAMPLES_DIR)
        assert len(records) == len(files)

    def test_every_record_has_keys(self):
        records = catalog_samples(SAMPLES_DIR)
        for r in records:
            assert "id" in r
            assert "language" in r
            assert "skill" in r
            assert "expected_cefr" in r
            assert "text" in r
            assert "file" in r
            assert "text_length" in r

    def test_text_length_matches(self):
        for r in catalog_samples(SAMPLES_DIR):
            assert r["text_length"] == len(r.get("text", ""))


class TestFilterCatalog:
    def test_filter_by_language(self):
        en = filter_catalog(language="en")
        assert en
        assert all(r.get("language") == "en" for r in en)

    def test_filter_by_skill(self):
        writing = filter_catalog(skill="writing")
        assert writing
        assert all(r.get("skill") == "writing" for r in writing)

    def test_filter_by_language_and_skill(self):
        out = filter_catalog(language="en", skill="speaking")
        assert out
        assert all(r.get("language") == "en" and r.get("skill") == "speaking" for r in out)

    def test_filter_by_cefr(self):
        a1 = filter_catalog(cefr="A1")
        assert a1
        assert all(str(r.get("expected_cefr")).upper() == "A1" for r in a1)

    def test_filter_combined_three_ways(self):
        out = filter_catalog(language="en", skill="speaking", cefr="A1")
        assert out
        for r in out:
            assert r.get("language") == "en"
            assert r.get("skill") == "speaking"
            assert str(r.get("expected_cefr")).upper() == "A1"

    def test_filter_case_insensitive(self):
        lower = filter_catalog(language="EN", skill="WRITING")
        upper = filter_catalog(language="en", skill="writing")
        assert len(lower) == len(upper)

    def test_filter_cefr_case_insensitive(self):
        lower = filter_catalog(cefr="a1")
        upper = filter_catalog(cefr="A1")
        assert len(lower) == len(upper)

    def test_filter_missing_language(self):
        assert filter_catalog(language="zzzz") == []

    def test_filter_missing_skill(self):
        assert filter_catalog(skill="telepathy") == []

    def test_filter_missing_cefr(self):
        assert filter_catalog(cefr="C99") == []

    def test_filter_subset_of_larger(self):
        all_en = filter_catalog(language="en")
        all_writing = filter_catalog(skill="writing")
        combined = filter_catalog(language="en", skill="writing")
        assert len(combined) <= len(all_en)
        assert len(combined) <= len(all_writing)

    def test_accepts_existing_records(self):
        preloaded = catalog_samples(SAMPLES_DIR)
        filtered = filter_catalog(preloaded, language="en")
        assert filtered
        assert all(r.get("language") == "en" for r in filtered)


class TestSampleInfo:
    def test_known_id_returns_record(self):
        records = catalog_samples(SAMPLES_DIR)
        if not records:
            pytest.skip("No samples available")
        first_id = records[0]["id"]
        rec = sample_info(first_id)
        assert rec is not None
        assert rec["id"] == first_id

    def test_unknown_id_returns_none(self):
        assert sample_info("no-such-id-99999") is None


class TestSummaries:
    def test_summary_by_language_keys(self):
        d = summary_by_language()
        assert isinstance(d, dict)
        total = sum(d.values())
        assert total == len(catalog_samples())

    def test_summary_by_skill_keys(self):
        d = summary_by_skill()
        assert isinstance(d, dict)
        total = sum(d.values())
        assert total == len(catalog_samples())

    def test_summary_by_cefr_keys(self):
        d = summary_by_cefr()
        assert isinstance(d, dict)
        total = sum(d.values())
        assert total == len(catalog_samples())


# ── CLI tests: samples list ─────────────────────────────────────────


class TestSamplesListCli:
    def test_list_all(self):
        result = _run_nokaman("samples", "list")
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "Samples" in result.stdout

    def test_list_language_filter(self):
        result = _run_nokaman("samples", "list", "--language", "en")
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "Samples" in result.stdout

    def test_list_skill_filter(self):
        result = _run_nokaman("samples", "list", "--skill", "reading")
        assert result.returncode == 0, f"stderr: {result.stderr}"

    def test_list_cefr_filter(self):
        result = _run_nokaman("samples", "list", "--cefr", "A1")
        assert result.returncode == 0, f"stderr: {result.stderr}"

    def test_list_combined_filters(self):
        result = _run_nokaman("samples", "list", "-l", "en", "-s", "speaking", "-c", "A1")
        assert result.returncode == 0, f"stderr: {result.stderr}"

    def test_list_json_output(self):
        result = _run_nokaman("samples", "list", "--json", "-l", "en")
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout)
        assert isinstance(data, list)
        if data:
            assert "id" in data[0]
            assert "language" in data[0]
            assert "skill" in data[0]

    def test_list_json_does_not_include_text(self):
        result = _run_nokaman("samples", "list", "--json", "-l", "en")
        data = json.loads(result.stdout)
        for item in data:
            assert "text" not in item, "text key should not appear in JSON list output"

    def test_list_sort_by_language(self):
        result = _run_nokaman("samples", "list", "--sort-by", "language")
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "Samples" in result.stdout

    def test_list_sort_by_skill(self):
        result = _run_nokaman("samples", "list", "--sort-by", "skill")
        assert result.returncode == 0, f"stderr: {result.stderr}"

    def test_list_sort_by_cefr(self):
        result = _run_nokaman("samples", "list", "--sort-by", "cefr")
        assert result.returncode == 0, f"stderr: {result.stderr}"

    def test_list_sort_by_id(self):
        result = _run_nokaman("samples", "list", "--sort-by", "id")
        assert result.returncode == 0, f"stderr: {result.stderr}"

    def test_list_sort_by_text_length(self):
        result = _run_nokaman("samples", "list", "--sort-by", "text_length")
        assert result.returncode == 0, f"stderr: {result.stderr}"

    def test_list_limit(self):
        result = _run_nokaman("samples", "list", "--limit", "3")
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "Samples (3)" in result.stdout

    def test_list_no_match(self):
        result = _run_nokaman("samples", "list", "--language", "zz")
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "No samples" in result.stdout


# ── CLI tests: samples stats ────────────────────────────────────────


class TestSamplesStatsCli:
    def test_stats_all(self):
        result = _run_nokaman("samples", "stats")
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "Sample Statistics" in result.stdout

    def test_stats_language_filter(self):
        result = _run_nokaman("samples", "stats", "--language", "en")
        assert result.returncode == 0, f"stderr: {result.stderr}"

    def test_stats_skill_filter(self):
        result = _run_nokaman("samples", "stats", "--skill", "reading")
        assert result.returncode == 0, f"stderr: {result.stderr}"

    def test_stats_cefr_filter(self):
        result = _run_nokaman("samples", "stats", "--cefr", "A2")
        assert result.returncode == 0, f"stderr: {result.stderr}"

    def test_stats_json_output(self):
        result = _run_nokaman("samples", "stats", "--json")
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout)
        assert "total_samples" in data
        assert "by_language" in data
        assert "by_skill" in data
        assert "by_cefr" in data

    def test_stats_shows_by_language_section(self):
        result = _run_nokaman("samples", "stats")
        assert "By Language" in result.stdout

    def test_stats_shows_by_skill_section(self):
        result = _run_nokaman("samples", "stats")
        assert "By Skill" in result.stdout

    def test_stats_shows_by_cefr_section(self):
        result = _run_nokaman("samples", "stats")
        assert "By CEFR" in result.stdout


# ── CLI tests: samples info ─────────────────────────────────────────


class TestSamplesInfoCli:
    def test_info_known_sample(self):
        records = catalog_samples(SAMPLES_DIR)
        if not records:
            pytest.skip("No samples available")
        sample_id = records[0]["id"]
        result = _run_nokaman("samples", "info", sample_id)
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert sample_id in result.stdout

    def test_info_unknown_sample(self):
        result = _run_nokaman("samples", "info", "no-such-id-99999")
        assert result.returncode != 0
        assert "not found" in result.stdout.lower() or "Sample not found" in result.stdout

    def test_info_json_output(self):
        records = catalog_samples(SAMPLES_DIR)
        if not records:
            pytest.skip("No samples available")
        sample_id = records[0]["id"]
        result = _run_nokaman("samples", "info", sample_id, "--json")
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout)
        assert data["id"] == sample_id


# ── CLI tests: samples help ─────────────────────────────────────────


def test_samples_help():
    result = _run_nokaman("samples", "--help")
    assert result.returncode == 0
    assert "list" in result.stdout.lower()
    assert "stats" in result.stdout.lower()
    assert "info" in result.stdout.lower()
