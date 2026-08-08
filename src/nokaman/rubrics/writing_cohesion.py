"""Writing cohesion/coherence offline rubric (Closes #66)."""
from __future__ import annotations

import re

# Keywords signalling logical connectors and discourse markers
COHESION_MARKERS = frozenset({
    "however", "therefore", "moreover", "furthermore", "consequently",
    "nevertheless", "meanwhile", "additionally", "in contrast", "on the other hand",
    "first", "second", "third", "finally", "in conclusion", "for example",
    "such as", "because", "since", "although", "whereas", "while",
    "in addition", "similarly", "likewise", "accordingly", "thus"
})

REFERENCE_WORDS = frozenset({
    "this", "that", "these", "those", "it", "they", "them",
    "the former", "the latter"
})

DIMENSION_WEIGHTS = {
    "connector_density": 0.30,
    "reference_cohesion": 0.25,
    "paragraph_flow": 0.25,
    "topic_consistency": 0.20,
}

LIMITATIONS = (
    "Offline heuristics based on surface-level markers; does not assess deep semantic coherence.",
    "Connector detection is English-only and may miss multi-word phrases in other languages.",
    "Paragraph flow assumes standard paragraph breaks; unsegmented text scores lower.",
    "This is a product signal, not a certified CEFR writing assessment.",
)

SAMPLE_DOC = (
    "First, the study examined the effects of sleep on memory consolidation. "
    "However, the results were inconclusive. Therefore, a follow-up experiment was designed. "
    "This experiment controlled for additional variables such as caffeine intake. "
    "In conclusion, while sleep appears to play a role, further research is needed."
)


def _words(text: str) -> list[str]:
    return re.findall(r"[^\W\d_]+(?:['-][^\W\d_]+)*", text.lower(), flags=re.UNICODE)


def _clamp(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 2)


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]


def _connector_density_score(text: str) -> float:
    words = _words(text)
    if len(words) < 20:
        return 50.0
    connectors = sum(1 for w in words if w in COHESION_MARKERS)
    ratio = connectors / len(words)
    if ratio < 0.02:
        return _clamp(ratio * 3000)
    if ratio <= 0.08:
        return _clamp(75 + (ratio - 0.02) * 400)
    return _clamp(100 - (ratio - 0.08) * 500)


def _reference_cohesion_score(text: str) -> float:
    words = _words(text)
    if len(words) < 30:
        return 50.0
    refs = sum(1 for w in words if w in REFERENCE_WORDS)
    ratio = refs / len(words)
    if ratio < 0.03:
        return _clamp(ratio * 2000)
    if ratio <= 0.10:
        return _clamp(75 + (ratio - 0.03) * 350)
    return _clamp(100 - (ratio - 0.10) * 400)


def _paragraph_flow_score(text: str) -> float:
    paragraphs = text.split('\n\n')
    paragraphs = [p.strip() for p in paragraphs if p.strip()]
    if len(paragraphs) < 2:
        return 40.0
    transitions = 0
    for p in paragraphs:
        first_words = ' '.join(_words(p)[:3])
        if any(m in first_words for m in COHESION_MARKERS):
            transitions += 1
    ratio = transitions / (len(paragraphs) - 1)
    return _clamp(40 + ratio * 60)


def _topic_consistency_score(text: str) -> float:
    sentences = _sentences(text)
    if len(sentences) < 3:
        return 50.0
    word_sets = [set(_words(s)) for s in sentences]
    overlaps = 0
    for i in range(len(word_sets) - 1):
        intersection = word_sets[i] & word_sets[i + 1]
        union = word_sets[i] | word_sets[i + 1]
        if union and len(intersection) / len(union) > 0.1:
            overlaps += 1
    ratio = overlaps / (len(sentences) - 1)
    return _clamp(30 + ratio * 70)


def score_writing_cohesion(
    text: str,
    *,
    connector_density_override: float | None = None,
    reference_cohesion_override: float | None = None,
    paragraph_flow_override: float | None = None,
    topic_consistency_override: float | None = None,
) -> dict:
    """Score writing cohesion/coherence with deterministic offline heuristics."""
    text = text.strip()
    if not text:
        raise ValueError("text must not be empty")

    cd = connector_density_override if connector_density_override is not None else _connector_density_score(text)
    rc = reference_cohesion_override if reference_cohesion_override is not None else _reference_cohesion_score(text)
    pf = paragraph_flow_override if paragraph_flow_override is not None else _paragraph_flow_score(text)
    tc = topic_consistency_override if topic_consistency_override is not None else _topic_consistency_score(text)

    weighted = (
        cd * DIMENSION_WEIGHTS["connector_density"] +
        rc * DIMENSION_WEIGHTS["reference_cohesion"] +
        pf * DIMENSION_WEIGHTS["paragraph_flow"] +
        tc * DIMENSION_WEIGHTS["topic_consistency"]
    )

    return {
        "score": _clamp(weighted),
        "dimensions": {
            "connector_density": _clamp(cd),
            "reference_cohesion": _clamp(rc),
            "paragraph_flow": _clamp(pf),
            "topic_consistency": _clamp(tc),
        },
        "word_count": len(_words(text)),
        "sentence_count": len(_sentences(text)),
        "metadata": {
            "rubric": "writing_cohesion_v1",
            "language": "en",
            "limitations": list(LIMITATIONS),
        },
    }


def score_writing_sample(
    text: str, *, sample_id: str = "", duration_seconds: float | None = None
) -> dict:
    """Score a writing sample and attach sample metadata."""
    result = score_writing_cohesion(text)
    result["sample_id"] = sample_id
    if duration_seconds is not None:
        wpm = len(result["dimensions"]) / max(duration_seconds, 1) * 60
        result["estimated_wpm"] = round(wpm, 1)
    return result
