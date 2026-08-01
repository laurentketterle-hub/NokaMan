from __future__ import annotations

import re
from collections.abc import Mapping

DIMENSION_WEIGHTS = {
    "cohesion": 0.35,
    "coherence": 0.35,
    "paragraph_structure": 0.15,
    "transition_quality": 0.15,
}
LIMITATIONS = (
    "Cohesion/coherence heuristics are deterministic surface-level proxies and do not measure true discourse quality.",
    "Transition detection is language-dependent; results are most reliable for English.",
    "Paragraph structure detection relies on newline breaks and may misclassify poetry or dialogue formatting.",
    "These dimensions are offline approximations, not certified CEFR writing assessment criteria.",
)


def _clamp(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 2)


def _count_cohesive_devices(text: str) -> dict:
    """Count surface cohesive devices: pronouns, connectives, lexical repetition."""
    words = re.findall(r"[^\W\d_]+(?:['-][^\W\d_]+)*", text.lower(), flags=re.UNICODE)
    n_words = max(1, len(words))

    # Pronouns (he, she, it, they, this, that, these, those, etc.)
    pronouns = {"he", "she", "it", "they", "we", "this", "that", "these", "those",
                "him", "her", "them", "us", "his", "hers", "its", "their", "our",
                "himself", "herself", "itself", "themselves", "ourselves", "myself", "yourself"}
    pronoun_count = sum(1 for w in words if w in pronouns)

    # Connectives / transition words
    connectives = {"however", "therefore", "moreover", "furthermore", "nevertheless",
                   "consequently", "meanwhile", "additionally", "similarly", "likewise",
                   "alternatively", "otherwise", "thus", "hence", "accordingly", "nonetheless",
                   "besides", "instead", "indeed", "specifically", "finally", "next", "then",
                   "first", "second", "third", "lastly", "also", "for", "example", "instance",
                   "because", "since", "although", "while", "whereas", "unless", "until",
                   "after", "before", "when", "if", "so", "yet", "but", "and", "or"}
    connective_count = sum(1 for w in words if w in connectives)

    # Lexical repetition ratio (unique/total words — higher uniqueness suggests lexical variety)
    unique_ratio = len(set(words)) / n_words

    return {
        "pronoun_count": pronoun_count,
        "connective_count": connective_count,
        "unique_ratio": round(unique_ratio, 4),
        "word_count": len(words),
    }


def _score_cohesion(devices: dict) -> float:
    """Score cohesion from surface device density."""
    n_words = max(1, devices["word_count"])
    pronoun_density = devices["pronoun_count"] / n_words
    connective_density = devices["connective_count"] / n_words

    # Balanced pronoun usage (not too sparse, not too dense)
    if pronoun_density < 0.02:
        pronoun_score = pronoun_density / 0.02 * 50
    elif pronoun_density < 0.10:
        pronoun_score = 100.0
    else:
        pronoun_score = max(30, 100 - (pronoun_density - 0.10) * 200)

    # Connective density scoring
    if connective_density < 0.01:
        connective_score = connective_density / 0.01 * 50
    elif connective_density < 0.08:
        connective_score = 100.0
    else:
        connective_score = max(30, 100 - (connective_density - 0.08) * 150)

    return _clamp(pronoun_score * 0.4 + connective_score * 0.4 + devices["unique_ratio"] * 100 * 0.2)


def _score_coherence(text: str) -> float:
    """Score coherence via paragraph/sentence flow heuristics."""
    # Split into paragraphs
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [text.strip()]

    # Split into sentences
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    n_sentences = max(1, len(sentences))

    # Average sentence length (words per sentence)
    words_per_sentence = [
        len(re.findall(r"[^\W\d_]+(?:['-][^\W\d_]+)*", s.lower(), flags=re.UNICODE))
        for s in sentences
    ]
    avg_sentence_len = sum(words_per_sentence) / n_sentences

    # Sentence length variance (lower = more consistent)
    if n_sentences > 1:
        mean = avg_sentence_len
        variance = sum((w - mean) ** 2 for w in words_per_sentence) / n_sentences
        cv = (variance ** 0.5) / max(1, mean)  # coefficient of variation
    else:
        cv = 0.0

    # Ideal average sentence length 8-20 words
    if avg_sentence_len < 5:
        len_score = avg_sentence_len / 5 * 50
    elif avg_sentence_len <= 20:
        len_score = 100.0
    elif avg_sentence_len <= 35:
        len_score = 100 - (avg_sentence_len - 20) / 15 * 40
    else:
        len_score = max(20, 60 - (avg_sentence_len - 35) * 2)

    # Consistency bonus
    consistency_score = max(30, 100 - cv * 50)

    # Paragraph cohesion: check if paragraphs connect logically (first/last sentence overlap)
    para_flow = 50.0
    if len(paragraphs) > 1:
        flow_scores = []
        for i in range(len(paragraphs) - 1):
            curr_last_words = set(re.findall(r"[^\W\d_]+", paragraphs[i].split(".")[-1].lower()))
            next_first_words = set(re.findall(r"[^\W\d_]+", paragraphs[i+1].split(".")[0].lower()))
            if curr_last_words and next_first_words:
                overlap = len(curr_last_words & next_first_words) / max(1, len(curr_last_words | next_first_words))
                flow_scores.append(min(100, overlap * 300))
        if flow_scores:
            para_flow = sum(flow_scores) / len(flow_scores)

    return _clamp(len_score * 0.35 + consistency_score * 0.30 + para_flow * 0.35)


def _score_paragraph_structure(text: str) -> float:
    """Score paragraph structure: topic sentences, length balance."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [text.strip()]
    n_paras = len(paragraphs)

    # Ideal 2-5 paragraphs
    if n_paras == 1:
        para_count_score = 50.0
    elif n_paras <= 5:
        para_count_score = 100.0
    else:
        para_count_score = max(30, 100 - (n_paras - 5) * 10)

    # Paragraph length balance
    para_lens = [len(re.findall(r"[^\W\d_]+", p.lower())) for p in paragraphs]
    avg_len = sum(para_lens) / max(1, n_paras)
    if avg_len > 0 and n_paras > 1:
        deviations = [abs(pl - avg_len) / avg_len for pl in para_lens]
        balance = max(30, 100 - sum(deviations) / n_paras * 100)
    else:
        balance = 70.0

    # Topic sentence detection: first sentence of each paragraph should be substantial
    topic_scores = []
    for p in paragraphs:
        first_sent = p.split(".")[0].strip()
        first_words = len(re.findall(r"[^\W\d_]+", first_sent.lower()))
        if first_words >= 5:
            topic_scores.append(100.0)
        elif first_words >= 3:
            topic_scores.append(70.0)
        else:
            topic_scores.append(30.0)
    topic_avg = sum(topic_scores) / max(1, len(topic_scores))

    return _clamp(para_count_score * 0.3 + balance * 0.35 + topic_avg * 0.35)


def _score_transitions(text: str) -> float:
    """Score transition quality by detecting transition words at sentence starts."""
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    if len(sentences) <= 1:
        return 50.0

    transition_starters = {
        "however", "therefore", "moreover", "furthermore", "nevertheless",
        "consequently", "meanwhile", "additionally", "similarly", "likewise",
        "alternatively", "otherwise", "thus", "hence", "accordingly", "nonetheless",
        "besides", "instead", "indeed", "specifically", "finally", "next", "then",
        "first", "second", "third", "lastly", "also", "for", "in", "on", "at",
        "after", "before", "during", "while", "although", "because", "since",
        "as", "despite", "regarding", "concerning", "with", "without",
    }

    transition_count = 0
    for sent in sentences[1:]:  # skip first sentence
        first_word = re.findall(r"[^\W\d_]+", sent.lower())
        if first_word and first_word[0] in transition_starters:
            transition_count += 1

    ratio = transition_count / (len(sentences) - 1)
    return _clamp(ratio * 250)  # ~40% transition rate = 100% score


def score_writing_cohesion(
    text: str,
    *,
    explicit_paragraphs: bool = True,
) -> dict:
    """Score writing cohesion/coherence with deterministic offline heuristics."""
    text = text.strip()
    if not text:
        raise ValueError("text must not be empty")

    words = re.findall(r"[^\W\d_]+(?:['-][^\W\d_]+)*", text.lower(), flags=re.UNICODE)
    if not words:
        raise ValueError("text must contain words")

    devices = _count_cohesive_devices(text)

    dimensions = {
        "cohesion": _score_cohesion(devices),
        "coherence": _score_coherence(text),
        "paragraph_structure": _score_paragraph_structure(text),
        "transition_quality": _score_transitions(text),
    }
    overall = _clamp(
        sum(dimensions[name] * weight for name, weight in DIMENSION_WEIGHTS.items())
    )

    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    limitations = list(LIMITATIONS)
    if not explicit_paragraphs:
        limitations.append("Paragraph detection skipped; entire text treated as single paragraph.")

    return {
        "score": overall,
        "dimensions": dimensions,
        "observations": {
            "word_count": devices["word_count"],
            "sentence_count": len(sentences),
            "paragraph_count": len(paragraphs),
            "avg_sentence_length": round(
                devices["word_count"] / max(1, len(sentences)), 2
            ),
            "pronoun_count": devices["pronoun_count"],
            "connective_count": devices["connective_count"],
            "unique_word_ratio": devices["unique_ratio"],
        },
        "limitations": limitations,
    }


def score_writing_sample(sample: Mapping[str, object]) -> dict:
    """Score a writing sample."""
    if str(sample.get("skill") or "").strip().lower() != "writing":
        raise ValueError("sample skill must be writing")
    return score_writing_cohesion(
        str(sample.get("text") or ""),
    )
