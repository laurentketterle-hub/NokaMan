from __future__ import annotations

import re
from collections.abc import Mapping

DIMENSION_WEIGHTS = {
    "cohesion": 0.25,
    "coherence": 0.25,
    "vocabulary": 0.20,
    "grammar": 0.15,
    "organization": 0.10,
    "task_achievement": 0.05,
}
BASE_LIMITATIONS = (
    "Lexical cohesion heuristics do not assess argument quality or factual accuracy.",
    "Coherence scoring is based on surface-level discourse markers and paragraph structure.",
    "Vocabulary assessment relies on word-length and diversity heuristics, not semantic analysis.",
    "Grammar scoring uses sentence-length variation and punctuation as proxy signals.",
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


def _vocabulary_score(text: str, words: list[str]) -> float:
    """Score vocabulary range and sophistication via word diversity and length."""
    unique_words = set(words)
    # Type-token ratio (lexical diversity)
    ttr = len(unique_words) / max(1, len(words))

    # Long-word ratio (sophistication proxy)
    long_words = [w for w in words if len(w) > 6]
    long_ratio = len(long_words) / max(1, len(words))

    # Unique word count saturation (capped at 50 for scoring)
    unique_saturation = min(len(unique_words), 50) / 50

    score = _clamp(ttr * 35 + long_ratio * 40 + unique_saturation * 25)
    return score


def _grammar_score(text: str, words: list[str]) -> float:
    """Score grammatical complexity via sentence length variation and punctuation."""
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    if not sentences:
        return 0.0

    sent_lens = [len(s.split()) for s in sentences]
    avg_len = sum(sent_lens) / len(sent_lens)

    # Sentence length variation (std dev)
    if len(sent_lens) > 1:
        mean = sum(sent_lens) / len(sent_lens)
        variance = sum((x - mean) ** 2 for x in sent_lens) / len(sent_lens)
        std_dev = variance ** 0.5
        variation_score = _clamp(min(std_dev, 10) / 10 * 100)
    else:
        variation_score = 20.0

    # Average sentence length (ideal range: 10-25 words)
    if 10 <= avg_len <= 25:
        len_score = 100.0
    elif avg_len < 10:
        len_score = _clamp(avg_len / 10 * 100)
    else:
        len_score = _clamp(max(0, 100 - (avg_len - 25) * 2))

    # Complex punctuation signals (commas, semicolons, colons)
    complex_punct = len(re.findall(r"[,;:]", text))
    punct_density = complex_punct / max(1, len(sentences))
    punct_score = _clamp(min(punct_density, 3) / 3 * 100)

    score = _clamp(variation_score * 0.35 + len_score * 0.35 + punct_score * 0.30)
    return score


def _organization_score(text: str, words: list[str]) -> float:
    """Score logical organization via paragraph transitions and structure."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if len(paragraphs) < 2:
        return 30.0

    # Transition words at paragraph starts
    transitions = r"^\s*(however|furthermore|moreover|in addition|first|second|third|finally|in conclusion|to summarize|on the other hand|consequently|therefore|meanwhile|similarly|in contrast|nevertheless|accordingly|subsequently|additionally|next|then|also|thus|hence)"
    transition_count = sum(1 for p in paragraphs if re.search(transitions, p, re.IGNORECASE))

    # Paragraph-to-paragraph cohesion
    transition_ratio = transition_count / max(1, len(paragraphs))

    # Introduction/conclusion detection
    has_intro = len(paragraphs) > 1 and len(_words(paragraphs[0])) > 5
    has_conclusion = len(paragraphs) > 1 and len(_words(paragraphs[-1])) > 5

    # Average paragraph words (balanced = good)
    para_word_counts = [len(_words(p)) for p in paragraphs]
    avg_para_words = sum(para_word_counts) / len(para_word_counts)
    if 30 <= avg_para_words <= 120:
        balance_score = 100.0
    elif avg_para_words < 30:
        balance_score = _clamp(avg_para_words / 30 * 100)
    else:
        balance_score = _clamp(max(0, 100 - (avg_para_words - 120) * 0.5))

    score = _clamp(
        transition_ratio * 45 + (20 if has_intro else 0) + (15 if has_conclusion else 0) + balance_score * 0.20
    )
    return score


def _task_achievement_score(text: str, words: list[str]) -> float:
    """Score task achievement via text completeness and development signals."""
    # Word count as a rough completeness proxy
    if len(words) < 20:
        return _clamp(len(words) / 20 * 30)

    # Sentence count (more sentences = more developed)
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    sent_score = _clamp(min(len(sentences), 10) / 10 * 100)

    # Examples and elaboration markers
    elaboration = r"\b(for example|for instance|such as|specifically|in particular|namely|that is|in other words|to illustrate|this means|because|since|as a result)\b"
    elaboration_count = len(re.findall(elaboration, text.lower()))
    elaboration_density = elaboration_count / max(1, len(sentences))
    elaboration_score = _clamp(min(elaboration_density, 1.0) * 100)

    # Opinion/perspective markers
    stance = r"\b(I think|I believe|in my opinion|it seems|it appears|arguably|clearly|undoubtedly|perhaps|maybe|probably|certainly|definitely)\b"
    stance_count = len(re.findall(stance, text.lower()))
    stance_score = _clamp(min(stance_count, 3) / 3 * 100)

    score = _clamp(
        sent_score * 0.40 + elaboration_score * 0.35 + stance_score * 0.25
    )
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
    vocabulary = _vocabulary_score(text, words)
    grammar = _grammar_score(text, words)
    organization = _organization_score(text, words)
    task_achievement = _task_achievement_score(text, words)

    dimensions = {
        "cohesion": cohesion,
        "coherence": coherence,
        "vocabulary": vocabulary,
        "grammar": grammar,
        "organization": organization,
        "task_achievement": task_achievement,
    }
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

def score_batch(texts):
    return [score_writing_cohesion(t) for t in texts]

def export_scores_json(texts, path):
    import json
    results = [{"text": t[:100], "result": score_writing_cohesion(t)} for t in texts]
    with open(path, "w") as f:
        json.dump(results, f, indent=2)
    return path
