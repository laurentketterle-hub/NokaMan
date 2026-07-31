"""Offline writing cohesion/coherence scoring.

Provides deterministic heuristics for evaluating text cohesion
(transition-word density, pronoun-reference chains) and coherence
(topic-sentence patterns, paragraph logical flow).

These are stub dimensions intended to complement existing language
rubrics; they do NOT perform semantic analysis or discourse parsing.
"""

from __future__ import annotations

import re
from collections.abc import Mapping

# ── Transition word lists ──────────────────────────────────────────
ADDITIVE_TRANSITIONS = frozenset({
    "also", "additionally", "furthermore", "moreover", "in addition",
    "besides", "similarly", "likewise", "as well as", "not only",
    "another", "equally",
})
ADVERSATIVE_TRANSITIONS = frozenset({
    "but", "however", "although", "nevertheless", "nonetheless",
    "conversely", "on the other hand", "in contrast", "whereas",
    "while", "yet", "still", "instead", "despite", "even though",
})
CAUSAL_TRANSITIONS = frozenset({
    "therefore", "thus", "consequently", "as a result", "hence",
    "accordingly", "so", "because", "since", "for this reason",
    "due to", "owing to",
})
SEQUENTIAL_TRANSITIONS = frozenset({
    "first", "second", "third", "finally", "lastly", "next",
    "then", "subsequently", "previously", "afterward", "meanwhile",
    "initially", "ultimately", "eventually",
})

ALL_TRANSITIONS = (
    ADDITIVE_TRANSITIONS
    | ADVERSATIVE_TRANSITIONS
    | CAUSAL_TRANSITIONS
    | SEQUENTIAL_TRANSITIONS
)

# Pronouns that signal forward/backward reference (cohesion)
REFERENCE_PRONOUNS = frozenset({
    "it", "they", "them", "this", "that", "these", "those",
    "he", "she", "his", "her", "its", "their",
})

DIMENSION_WEIGHTS = {
    "cohesion": 0.40,
    "coherence": 0.35,
    "sentence_variety": 0.25,
}

BASE_LIMITATIONS = (
    "Cohesion/coherence heuristics are surface-level and do not perform semantic analysis or discourse parsing.",
    "Transition-word detection is language-dependent; results for non-English text use English word lists and may be inaccurate.",
    "Paragraph detection relies on blank-line separation and may fail for markdown lists, code blocks, or inline HTML.",
    "The result is an offline product signal, not a certified writing assessment (e.g., CEFR, IELTS Writing).",
    "Pronoun-reference scoring is a naive heuristic that counts pronouns without resolving antecedents.",
)


def _words(text: str) -> list[str]:
    return re.findall(r"[^\W\d_]+(?:['\u2019-][^\W\d_]+)*", text.lower(), flags=re.UNICODE)


def _sentences(text: str) -> list[str]:
    """Split text into sentences using punctuation boundaries."""
    # Normalize whitespace first
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return []
    # Split on sentence-ending punctuation followed by space or end
    raw = re.split(r"(?<=[.!?])\s+", cleaned)
    return [s.strip() for s in raw if s.strip() and len(_words(s)) >= 2]


def _paragraphs(text: str) -> list[str]:
    """Split text into paragraphs at blank lines."""
    parts = re.split(r"\n\s*\n", text.strip())
    return [p.strip() for p in parts if p.strip() and len(_words(p)) >= 3]


def _clamp(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 2)


def _transition_density(text: str) -> float:
    """Fraction of sentences that contain at least one transition word."""
    sents = _sentences(text)
    if not sents:
        return 0.0
    count = sum(
        1 for s in sents
        if any(tok in ALL_TRANSITIONS for tok in _words(s))
    )
    return count / len(sents)


def _pronoun_density(text: str) -> float:
    """Fraction of words that are referential pronouns."""
    tokens = _words(text)
    if not tokens:
        return 0.0
    refs = sum(1 for t in tokens if t in REFERENCE_PRONOUNS)
    return refs / len(tokens)


def _sentence_length_variance(text: str) -> float:
    """Coefficient of variation of sentence lengths (higher = more variety)."""
    sents = _sentences(text)
    if len(sents) < 2:
        return 0.0
    lengths = [len(_words(s)) for s in sents]
    mean_len = sum(lengths) / len(lengths)
    if mean_len == 0:
        return 0.0
    variance = sum((l - mean_len) ** 2 for l in lengths) / len(lengths)
    return (variance ** 0.5) / mean_len


def _topic_sentence_score(text: str) -> float:
    """Approximate topic-sentence presence: first sentence of each paragraph
    should be declarative and medium-length."""
    paras = _paragraphs(text)
    if not paras:
        return 0.0
    scores = []
    for p in paras:
        sents = _sentences(p)
        if not sents:
            scores.append(0.0)
            continue
        first = sents[0]
        words = _words(first)
        n = len(words)
        # Declarative: starts with capital, ends with period, no question/exclamation
        is_declarative = bool(re.match(r"^[A-Z]", first)) and first.rstrip().endswith(".")
        # Medium-length: 8-25 words
        good_length = 8 <= n <= 25
        score = 0.0
        if is_declarative:
            score += 0.5
        if good_length:
            score += 0.5
        scores.append(score)
    return sum(scores) / len(scores)


def _paragraph_count_score(text: str) -> float:
    """Score based on adequate paragraph count relative to text length."""
    paras = _paragraphs(text)
    sents = _sentences(text)
    if not sents:
        return 0.0
    # Ideal: 1 paragraph per 3-5 sentences
    ratio = len(paras) / max(1, len(sents))
    if 0.15 <= ratio <= 0.40:
        return 100.0
    if ratio < 0.05:
        return 30.0  # wall of text
    if ratio > 0.60:
        return 50.0  # too fragmented
    return _clamp(ratio * 250)  # linear scale


def score_writing_cohesion(
    text: str,
    *,
    paragraph_count: int | None = None,
    transition_count: int | None = None,
) -> dict:
    """Score text cohesion and coherence with deterministic offline heuristics.

    Args:
        text: The writing sample to score.
        paragraph_count: Optional pre-computed paragraph count (bypasses auto-detection).
        transition_count: Optional pre-computed transition word count.

    Returns:
        Dict with 'score', 'dimensions', 'observations', 'limitations'.

    Raises:
        ValueError: If text is empty or contains no words.
    """
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("text must not be empty")
    if not _words(cleaned):
        raise ValueError("text must contain words")

    sents = _sentences(cleaned)
    paras = (
        paragraph_count
        if paragraph_count is not None
        else len(_paragraphs(cleaned))
    )
    transitions = (
        transition_count
        if transition_count is not None
        else sum(
            1 for s in sents
            if any(tok in ALL_TRANSITIONS for tok in _words(s))
        )
    )

    # ── Dimension: Cohesion ────────────────────────────────────────
    t_density = _transition_density(cleaned)
    p_density = _pronoun_density(cleaned)
    # Ideal: 40-80% of sentences have transitions, pronouns < 15% of words
    cohesion = _clamp(min(t_density * 125, 100) * 0.6 + max(0, 100 - p_density * 400) * 0.4)

    # ── Dimension: Coherence ────────────────────────────────────────
    topic_score = _topic_sentence_score(cleaned)
    para_score = _paragraph_count_score(cleaned)
    coherence = _clamp(topic_score * 70 + para_score * 30)

    # ── Dimension: Sentence variety ─────────────────────────────────
    variety = _clamp(_sentence_length_variance(cleaned) * 200)

    dimensions = {
        "cohesion": cohesion,
        "coherence": coherence,
        "sentence_variety": variety,
    }
    overall = _clamp(
        sum(dimensions[name] * weight for name, weight in DIMENSION_WEIGHTS.items())
    )

    limitations = list(BASE_LIMITATIONS)
    if paragraph_count is not None:
        limitations.append(
            "Paragraph count was provided externally; automatic paragraph detection was not used."
        )
    if transition_count is not None:
        limitations.append(
            "Transition count was provided externally; automatic transition detection was not used."
        )

    return {
        "score": overall,
        "dimensions": dimensions,
        "observations": {
            "word_count": len(_words(cleaned)),
            "sentence_count": len(sents),
            "paragraph_count": paras,
            "transition_sentence_count": transitions,
            "transition_density": round(t_density, 3),
            "pronoun_density": round(p_density, 3),
            "sentence_length_cv": round(_sentence_length_variance(cleaned), 3),
            "avg_sentence_words": round(len(_words(cleaned)) / max(1, len(sents)), 1),
        },
        "limitations": limitations,
    }


def score_writing_sample(sample: Mapping[str, object]) -> dict:
    """Score a writing sample containing optional cohesion observations.

    Args:
        sample: Mapping with 'skill' (must be 'writing'), 'text', and
                optional 'cohesion_observations'.

    Returns:
        Scoring result dict from score_writing_cohesion().
    """
    if str(sample.get("skill") or "").strip().lower() != "writing":
        raise ValueError("sample skill must be 'writing'")
    observations = sample.get("cohesion_observations") or {}
    if not isinstance(observations, Mapping):
        raise ValueError("cohesion_observations must be an object")
    return score_writing_cohesion(
        str(sample.get("text") or ""),
        paragraph_count=_optional_int(observations.get("paragraph_count")),
        transition_count=_optional_int(observations.get("transition_count")),
    )


def _optional_int(value: object) -> int | None:
    return None if value is None else int(value)
