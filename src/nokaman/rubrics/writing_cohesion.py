"""Writing quality scoring: cohesion, grammar error proxies, length norms.

Offline / deterministic signals with no ML model required.
Toy model still works without optional dependencies.
"""

from __future__ import annotations

import re
from collections.abc import Mapping

# Dimension weights
DIMENSION_WEIGHTS = {
    "cohesion": 0.35,
    "grammar_proxies": 0.30,
    "length_norms": 0.20,
    "lexical_diversity": 0.15,
}

# Multilingual cohesion connectors
COHESION_CONNECTORS = frozenset({
    "because", "although", "however", "therefore", "while", "when", "if",
    "and", "but", "so", "or", "yet", "then", "since", "unless", "until",
    "moreover", "furthermore", "besides", "nevertheless", "consequently",
    "parce", "cependant", "toutefois", "donc", "alors", "mais", "et",
    "ou", "car", "puisque", "lorsque", "quand", "si",
    "porque", "aunque", "sin", "pero", "y", "o", "entonces", "cuando",
    "weil", "obwohl", "jedoch", "deshalb", "und", "aber", "oder", "wenn", "dann",
})

# Common grammar error patterns (regex, name)
GRAMMAR_ERROR_PATTERNS = [
    (r"  {2,}", "double_spaces"),
    (r"[.?!,;:][A-Z]", "missing_space_after_punct"),
    (r"\b(\w+)\s+\1\b", "repeated_word"),
    (r"[.?!]\s+[a-z]", "lowercase_sentence_start"),
    (r"\b(teh|recieve|occured|definately|seperate|accomodate|occurence)\b", "common_misspelling_en"),
    (r"\b(acceuil|language|aparament|comme\s+meme|malgr\w\s+que)\b", "common_misspelling_fr"),
    (r"^[a-z]", "missing_initial_capital"),
    (r"[!?]{3,}", "excessive_punctuation"),
    (r"\([^)]*$|\[[^\]]*$", "unbalanced_bracket"),
]

BASE_LIMITATIONS = (
    "Heuristic grammar proxies detect only surface patterns, not deep syntax errors.",
    "Cohesion assessment uses connector density, not discourse parsing.",
    "Length norms are language-dependent and approximate.",
    "The result is an offline product signal, not a certified CEFR writing assessment.",
)


def _words(text):
    return re.findall(r"[^\W\d_]+(?:['\u2019-][^\W\d_]+)*", text.lower(), flags=re.UNICODE)


def _sentences(text):
    return [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]


def _clamp(value):
    return round(max(0.0, min(100.0, value)), 2)


def _cohesion_score(text, words, sentences):
    if not sentences or len(sentences) < 2:
        return 30.0
    connectors_found = sum(1 for w in words if w in COHESION_CONNECTORS)
    connector_density = connectors_found / max(1, len(sentences)) * 100
    avg_sent_len = len(words) / max(1, len(sentences))
    sent_len_score = 100.0
    if avg_sent_len < 5:
        sent_len_score = avg_sent_len / 5 * 100
    elif avg_sent_len > 35:
        sent_len_score = max(30.0, 100 - (avg_sent_len - 35) * 2)
    transition_count = 0
    for sent in sentences:
        parts = sent.strip().split()
        if parts:
            first_word = parts[0].lower()
            if first_word in COHESION_CONNECTORS:
                transition_count += 1
    transition_density = transition_count / max(1, len(sentences)) * 100
    return _clamp(connector_density * 0.4 + sent_len_score * 0.3 + transition_density * 0.3)


def _grammar_proxies_score(text, words):
    if not words:
        return 0.0
    penalty = 0.0
    for pattern, name in GRAMMAR_ERROR_PATTERNS:
        matches = len(re.findall(pattern, text, flags=re.UNICODE))
        if name == "double_spaces":
            penalty += matches * 1.5
        elif name == "repeated_word":
            penalty += matches * 8.0
        elif name in ("missing_initial_capital", "lowercase_sentence_start"):
            penalty += matches * 5.0
        elif name == "unbalanced_bracket":
            penalty += matches * 6.0
        else:
            penalty += matches * 4.0
    penalty_per_word = penalty / max(1, len(words)) * 100
    return _clamp(100 - penalty_per_word)


def _length_norms_score(words, sentences):
    n = len(words)
    ns = len(sentences)
    if n == 0:
        return 0.0
    if n < 20:
        length_score = n / 20 * 50
    elif n < 50:
        length_score = 50 + (n - 20) / 30 * 30
    elif n <= 300:
        length_score = 100.0
    elif n <= 500:
        length_score = 100 - (n - 300) / 200 * 20
    else:
        length_score = max(40.0, 100 - (n - 500) / 100 * 10)
    if ns < 2:
        length_score *= 0.6
    elif ns < 4:
        length_score *= 0.85
    return _clamp(length_score)


def _lexical_diversity_score(words):
    n = len(words)
    if n == 0:
        return 0.0
    unique = len(set(words))
    guiraud = unique / (n ** 0.5)
    if guiraud < 4:
        return _clamp(guiraud / 4 * 50)
    elif guiraud < 8:
        return _clamp(50 + (guiraud - 4) / 4 * 30)
    elif guiraud <= 15:
        return _clamp(80 + (guiraud - 8) / 7 * 20)
    else:
        return 100.0


def score_writing_cohesion(text, language="en"):
    text_stripped = text.strip()
    if not text_stripped:
        raise ValueError("text must not be empty")
    words = _words(text_stripped)
    sentences = _sentences(text_stripped)
    if not words:
        raise ValueError("text must contain words")
    dimensions = {
        "cohesion": _cohesion_score(text_stripped, words, sentences),
        "grammar_proxies": _grammar_proxies_score(text_stripped, words),
        "length_norms": _length_norms_score(words, sentences),
        "lexical_diversity": _lexical_diversity_score(words),
    }
    overall = _clamp(sum(dimensions[name] * weight for name, weight in DIMENSION_WEIGHTS.items()))
    avg_word_len = sum(len(w) for w in words) / len(words) if words else 0.0
    avg_sent_len = len(words) / max(1, len(sentences))
    limitations = list(BASE_LIMITATIONS)
    if len(words) < 30:
        limitations.append("Short text (< 30 words): cohesion and length scores may be unreliable.")
    return {
        "score": overall,
        "dimensions": dimensions,
        "observations": {
            "word_count": len(words),
            "sentence_count": len(sentences),
            "unique_words": len(set(words)),
            "average_word_length": round(avg_word_len, 2),
            "average_sentence_length": round(avg_sent_len, 2),
            "type_token_ratio": round(len(set(words)) / max(1, len(words)), 4),
        },
        "limitations": limitations,
    }


def score_writing_sample(sample):
    if str(sample.get("skill") or "").strip().lower() != "writing":
        raise ValueError("sample skill must be writing")
    return score_writing_cohesion(
        str(sample.get("text") or ""),
        language=str(sample.get("language") or "en"),
    )
