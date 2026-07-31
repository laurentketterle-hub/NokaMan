from __future__ import annotations

import json
from pathlib import Path

from nokaman.config import LISTENING_DIR, RUBRICS_DIR, SAMPLES_DIR


def list_sample_files(directory: Path | None = None) -> list[Path]:
    root = directory or SAMPLES_DIR
    if not root.exists():
        return []
    return sorted(root.glob("*.json"))


def list_rubric_files(directory: Path | None = None) -> list[Path]:
    root = directory or RUBRICS_DIR
    if not root.exists():
        return []
    return sorted(root.glob("*.json"))


def list_listening_pack_files(directory: Path | None = None) -> list[Path]:
    root = directory or LISTENING_DIR
    if not root.exists():
        return []
    return sorted(root.glob("*.json"))


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_sample(path: Path) -> dict:
    payload = load_json(path)
    payload.setdefault("id", path.stem)
    payload.setdefault("language", "en")
    payload.setdefault("skill", "writing")
    payload.setdefault("text", "")
    return payload


def load_listening_pack(path: Path) -> dict:
    payload = load_json(path)
    payload.setdefault("id", path.stem)
    payload.setdefault("language", "en")
    payload.setdefault("skill", "listening")
    payload.setdefault("questions", payload.get("items") or [])
    payload["items"] = list(payload.get("items") or payload.get("questions") or [])
    return payload


def load_rubric(path: Path) -> dict:
    payload = load_json(path)
    payload.setdefault("language", path.stem)
    payload.setdefault("skills", {})
    return payload


# ── catalog helpers ───────────────────────────────────────────────


def catalog_samples(directory: Path | None = None) -> list[dict]:
    """Parse every JSON sample file into a list of structured records.

    Each record carries the file's ``id``, ``language``, ``skill``,
    ``expected_cefr``, ``text``, the filename, and a derived ``text_length``
    for quick sorting / filtering.
    """
    records: list[dict] = []
    for path in list_sample_files(directory):
        payload = load_sample(path)
        text = str(payload.get("text") or "")
        records.append({
            "id": payload.get("id"),
            "language": payload.get("language", "?"),
            "skill": payload.get("skill", "?"),
            "expected_cefr": payload.get("expected_cefr", "?"),
            "text": text,
            "file": path.name,
            "text_length": len(text),
        })
    return records


def filter_catalog(
    records: list[dict] | None = None,
    *,
    language: str | None = None,
    skill: str | None = None,
    cefr: str | None = None,
) -> list[dict]:
    """Narrow *records* (or the full catalogue) by language / skill / CEFR.

    Matching is **case-insensitive** and trims whitespace, so ``EN``
    matches ``en``, ``Writing`` matches ``writing``, etc.
    """
    if records is None:
        records = catalog_samples()
    if language:
        lang = language.strip().lower()
        records = [r for r in records if str(r.get("language") or "").strip().lower() == lang]
    if skill:
        sk = skill.strip().lower()
        records = [r for r in records if str(r.get("skill") or "").strip().lower() == sk]
    if cefr:
        ce = cefr.strip().upper()
        records = [r for r in records if str(r.get("expected_cefr") or "").strip().upper() == ce]
    return records


def sample_info(sample_id: str, directory: Path | None = None) -> dict | None:
    """Look up a single sample by its ``id`` field and return the full record.

    Returns ``None`` when no sample matches.
    """
    for rec in catalog_samples(directory):
        if str(rec.get("id") or "") == sample_id:
            return rec
    return None


def summary_by_cefr(directory: Path | None = None) -> dict[str, int]:
    """Count of samples per CEFR level."""
    from collections import Counter

    c: Counter[str] = Counter()
    for rec in catalog_samples(directory):
        cefr = str(rec.get("expected_cefr") or "?").upper()
        c[cefr] += 1
    return dict(sorted(c.items()))


def summary_by_language(directory: Path | None = None) -> dict[str, int]:
    """Count of samples per language code."""
    from collections import Counter

    c: Counter[str] = Counter()
    for rec in catalog_samples(directory):
        lang = str(rec.get("language") or "?").strip().lower()
        c[lang] += 1
    return dict(sorted(c.items()))


def summary_by_skill(directory: Path | None = None) -> dict[str, int]:
    """Count of samples per skill."""
    from collections import Counter

    c: Counter[str] = Counter()
    for rec in catalog_samples(directory):
        sk = str(rec.get("skill") or "?").strip().lower()
        c[sk] += 1
    return dict(sorted(c.items()))
