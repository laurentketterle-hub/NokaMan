"""Tests for samples list CLI with language/skill filters (Closes #59)."""
import json
from pathlib import Path
from nokaman.samples_cli import load_samples, filter_samples, format_samples_table


def make_sample(sample_id, language="en", skill="speaking", level="B1", stype="audio"):
    return {"id": sample_id, "language": language, "skill": skill, "level": level, "type": stype}


class TestFilterSamples:
    def test_filter_by_language(self):
        samples = [
            make_sample("1", language="en"),
            make_sample("2", language="ko"),
            make_sample("3", language="en"),
        ]
        filtered = filter_samples(samples, language="en")
        assert len(filtered) == 2
        assert all(s["language"] == "en" for s in filtered)

    def test_filter_by_skill(self):
        samples = [make_sample("1", skill="speaking"), make_sample("2", skill="writing")]
        filtered = filter_samples(samples, skill="speaking")
        assert len(filtered) == 1

    def test_filter_by_language_and_skill(self):
        samples = [
            make_sample("1", "en", "speaking"),
            make_sample("2", "en", "writing"),
            make_sample("3", "ko", "speaking"),
        ]
        filtered = filter_samples(samples, language="en", skill="speaking")
        assert len(filtered) == 1
        assert filtered[0]["id"] == "1"

    def test_filter_by_level(self):
        samples = [make_sample("1", level="A1"), make_sample("2", level="C2")]
        filtered = filter_samples(samples, level="A1")
        assert len(filtered) == 1

    def test_no_filter_returns_all(self):
        samples = [make_sample("1"), make_sample("2")]
        filtered = filter_samples(samples)
        assert len(filtered) == 2

    def test_filter_case_insensitive(self):
        samples = [make_sample("1", language="EN")]
        filtered = filter_samples(samples, language="en")
        assert len(filtered) == 1


class TestFormatTable:
    def test_table_with_samples(self):
        samples = [make_sample("s1", "en", "speaking", "B1")]
        table = format_samples_table(samples)
        assert "s1" in table
        assert "en" in table
        assert "Total: 1" in table

    def test_empty_table(self):
        table = format_samples_table([])
        assert "No samples" in table

    def test_language_summary(self):
        samples = [make_sample("1", "en"), make_sample("2", "ko")]
        table = format_samples_table(samples)
        assert "en=1" in table or "Languages:" in table
