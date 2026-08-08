"""CLI: nokaman samples list --language --skill (Closes #59).

List catalogued samples with filters for language and skill.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Dict, Any


SAMPLE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "samples"


def load_samples(data_dir: Path = SAMPLE_DIR) -> List[Dict[str, Any]]:
    """Load all sample JSON files from the samples directory."""
    samples = []
    if not data_dir.is_dir():
        return samples
    for fpath in sorted(data_dir.glob("**/*.json")):
        try:
            data = json.loads(fpath.read_text())
            data["_file"] = str(fpath.relative_to(data_dir))
            samples.append(data)
        except (json.JSONDecodeError, KeyError):
            continue
    return samples


def filter_samples(
    samples: List[dict],
    language: str = "",
    skill: str = "",
    level: str = "",
) -> List[dict]:
    """Filter samples by language, skill, and/or level."""
    filtered = samples
    if language:
        filtered = [s for s in filtered if s.get("language", "").lower() == language.lower()]
    if skill:
        filtered = [s for s in filtered if s.get("skill", "").lower() == skill.lower()]
    if level:
        filtered = [s for s in filtered if s.get("level", "").lower() == level.lower()]
    return filtered


def format_samples_table(samples: List[dict]) -> str:
    """Format filtered samples as a table."""
    if not samples:
        return "No samples found."

    columns = ["id", "language", "skill", "level", "type"]
    widths = {c: len(c) for c in columns}
    for s in samples:
        for c in columns:
            widths[c] = max(widths[c], len(str(s.get(c, ""))))

    header = " | ".join(c.ljust(widths[c]) for c in columns)
    sep = "-+-".join("-" * widths[c] for c in columns)
    rows = [header, sep]

    for s in samples:
        row = " | ".join(str(s.get(c, "")).ljust(widths[c]) for c in columns)
        rows.append(row)

    rows.append("")
    rows.append("Total: {} samples".format(len(samples)))

    # Summary by language
    langs = {}
    for s in samples:
        lang = s.get("language", "unknown")
        langs[lang] = langs.get(lang, 0) + 1
    rows.append("Languages: " + ", ".join("{}={}".format(k, v) for k, v in sorted(langs.items())))

    return "\n".join(rows)


def main():
    parser = argparse.ArgumentParser(description="NokaMan samples CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    list_parser = sub.add_parser("list", help="List samples with optional filters")
    list_parser.add_argument("--language", type=str, help="Filter by language (e.g., en, ko, ja)")
    list_parser.add_argument("--skill", type=str, help="Filter by skill (e.g., speaking, writing)")
    list_parser.add_argument("--level", type=str, help="Filter by level (e.g., A1, B1, C1)")
    list_parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()
    samples = load_samples()
    filtered = filter_samples(samples, args.language, args.skill, args.level)

    if args.json:
        print(json.dumps(filtered, indent=2, default=str))
    else:
        print(format_samples_table(filtered))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
