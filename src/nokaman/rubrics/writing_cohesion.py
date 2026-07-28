from __future__ import annotations

import re
from collections.abc import Mapping

DIMENSION_WEIGHTS = {
    "cohesion": 0.50,
    "coherence": 0.50,
}
BASE_LIMITATIONS = (
    "Lexical cohesion heuristics do not assess argument quality or factual accuracy.",
    "Coherence scoring is based on surface-level discourse markers and paragraph structure.",
    "This is an offline product signal, not a certified CEFR writing assessment.",
)


def _words(text: str) -> list[str]:
    return re.findall(r"[^\W\d_]+(?:['-][^\W\d_]+)*", text.lower(), flags=re.UNICODE)


def _clamp(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 2)


def _cohesion_score(text: str, words: list[str]) -> float:
    """Score lexical cohesion via word overlap and connector density."""
    if not words:
        return 0.0
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    if len(sentences) < 2:
        return 50.0

    # Connector density
    connectors = r"\b(and|but|or|so|because|therefore|however|moreover|furthermore|thus|hence|consequently|meanwhile|otherwise|nevertheless|although|whereas|while|since|unless|until|after|before|if|when|then|also|indeed|instead|finally|next|first|second|third)\b"
    connector_count = len(re.findall(connectors, text.lower()))
    connector_density = connector_count / max(1, len(sentences))

    # Word overlap between adjacent sentences
    overlaps = []
    for i in range(len(sentences) - 1):
        w1 = set(_words(sentences[i]))
        w2 = set(_words(sentences[i + 1]))
        if w1 and w2:
            overlaps.append(len(w1 & w2) / max(1, min(len(w1), len(w2))))
    avg_overlap = sum(overlaps) / max(1, len(overlaps)) if overlaps else 0.0

    score = _clamp(avg_overlap * 60 + connector_density * 25)
    return score


def _coherence_score(text: str, words: list[str]) -> float:
    """Score coherence via paragraph structure and topic consistency."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if len(paragraphs) < 2:
        return 50.0

    # Paragraph count as a signal of structure
    para_score = _clamp(min(len(paragraphs), 5) / 5 * 100)

    # Average paragraph length (not too short, not too long = balanced)
    avg_para_words = sum(len(_words(p)) for p in paragraphs) / len(paragraphs)
    length_score = 100.0
    if avg_para_words < 20:
        length_score = _clamp(avg_para_words / 20 * 100)
    elif avg_para_words > 150:
        length_score = _clamp(100 - (avg_para_words - 150) * 0.5)

    # Topic words consistency
    all_words = _words(text.lower())
    topic_words = {w for w in all_words if len(w) > 4 and all_words.count(w) >= 2}
    topic_density = len(topic_words) / max(1, len(set(all_words)))

    score = _clamp(para_score * 0.40 + length_score * 0.30 + topic_density * 200 * 0.30)
    return score


def score_writing_cohesion(
    text: str,
    *,
    sentence_count: int | None = None,
    paragraph_count: int | None = None,
) -> dict:
    """Score offline writing cohesion/coherence with deterministic heuristics."""
    text = text.strip()
    if not text:
        raise ValueError("text must not be empty")

    words = _words(text)
    if not words:
        raise ValueError("text must contain words")

    cohesion = _cohesion_score(text, words)
    coherence = _coherence_score(text, words)

    dimensions = {"cohesion": cohesion, "coherence": coherence}
    overall = _clamp(sum(dimensions[name] * weight for name, weight in DIMENSION_WEIGHTS.items()))

    limitations = list(BASE_LIMITATIONS)
    if sentence_count is None:
        limitations.append("Sentence count was estimated from text punctuation.")
    if paragraph_count is None:
        limitations.append("Paragraph count was estimated from text structure.")

    return {
        "score": overall,
        "dimensions": dimensions,
        "observations": {
            "word_count": len(words),
            "sentence_count": sentence_count or len(re.split(r"[.!?]+", text)),
            "paragraph_count": paragraph_count or len([p for p in text.split("\n\n") if p.strip()]),
        },
        "limitations": limitations,
    }


def score_writing_sample(sample: Mapping[str, object]) -> dict:
    """Score a writing sample containing optional cohesion/coherence observations."""
    if str(sample.get("skill") or "").strip().lower() != "writing":
        raise ValueError("sample skill must be writing")
    return score_writing_cohesion(
        str(sample.get("text") or ""),
        sentence_count=_optional_int(sample.get("sentence_count")),
        paragraph_count=_optional_int(sample.get("paragraph_count")),
    )


def _optional_int(value: object) -> int | None:
    return None if value is None else int(value)

def score_writing_readability(text):
    words=text.split()
    sentences=[s.strip() for s in text.replace("!",".").replace("?",".").split(".") if s.strip()]
    if not words or not sentences: raise ValueError("Empty")
    avg=len(words)/len(sentences)
    long=sum(1 for w in words if len(w)>6)
    s=max(0,min(100,100-abs(avg-15)*3-(long/max(1,len(words)))*50))
    return {"score":round(s,2),"avg_sent_len":round(avg,1),"long_word_ratio":round(long/max(1,len(words)),2)}
