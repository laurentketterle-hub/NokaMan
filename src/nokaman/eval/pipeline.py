from __future__ import annotations

from pathlib import Path

from nokaman.data.loader import load_sample
from nokaman.models.cefr import compare_bands
from nokaman.models.toy import ToyAbilityModel
from nokaman.rubrics.registry import get_language_meta


def evaluate_text(language: str, text: str, skill: str = "writing") -> dict:
    meta = get_language_meta(language)
    model = ToyAbilityModel(language=meta["code"])
    result = model.score_text(text, skill=skill)
    result["language_name"] = meta["name"]
    result["frameworks"] = meta["frameworks"]
    return result


def evaluate_sample_file(path: Path) -> dict:
    sample = load_sample(path)
    result = evaluate_text(
        language=str(sample.get("language") or "en"),
        text=str(sample.get("text") or ""),
        skill=str(sample.get("skill") or "writing"),
    )
    expected = sample.get("expected_cefr")
    if expected:
        result["band_check"] = compare_bands(result["cefr"], str(expected))
    result["sample_id"] = sample.get("id")
    result["source"] = str(path)
    return result


def evaluate_demo(language: str) -> dict:
    demos = {
        "en": "I enjoy learning languages because it helps me meet people and travel with confidence.",
        "ko": "저는 한국어를 공부하고 있습니다. 매일 단어를 외우고 짧은 일기를 씁니다.",
        "ja": "毎日日本語を勉強しています。会話の練習もしたいです。",
        "vi": "Tôi đang học tiếng Việt và thích đọc truyện ngắn mỗi ngày.",
        "zh": "我每天学习中文，喜欢和朋友练习口语。",
        "es": "Estoy aprendiendo español y practico con canciones todos los días.",
        "fr": "J'apprends le français et j'aime lire de petits articles.",
        "de": "Ich lerne Deutsch und übe jeden Tag neue Wörter.",
    }
    code = language.strip().lower()
    text = demos.get(code, demos["en"])
    model = ToyAbilityModel(language=code)
    multi = model.score_multi_skill(text)
    multi["demo_text"] = text
    meta = get_language_meta(code)
    multi["language_name"] = meta["name"]
    multi["frameworks"] = meta["frameworks"]
    # Attach framework band labels from overall writing-style score
    writing = model.score_text(text, skill="writing")
    multi["framework_bands"] = writing.get("framework_bands") or {}
    multi["cefr"] = writing.get("cefr") or multi.get("cefr")
    return multi

def evaluate_speaking_transcript(path: Path) -> dict:
    """Score a speaking ASR transcript JSON with fluency feedback bullets."""
    import json

    raw = json.loads(path.read_text(encoding="utf-8"))
    if str(raw.get("skill") or "").strip().lower() != "speaking":
        raise ValueError("ASR transcript skill must be 'speaking'")

    from nokaman.rubrics.speaking_fluency import score_speaking_fluency

    text = str(raw.get("text") or "")
    duration = raw.get("duration_seconds")
    confidence = raw.get("confidence")
    observations = raw.get("fluency_observations") or {}

    result = score_speaking_fluency(
        text,
        duration_seconds=(
            float(duration)
            if duration is not None
            else _optional_float_from(observations.get("duration_seconds"))
        ),
        pause_count=_optional_int_from(
            observations.get("pause_count") if observations else raw.get("pause_count")
        ),
        filler_count=_optional_int_from(
            observations.get("filler_count") if observations else raw.get("filler_count")
        ),
    )

    # Build CEFR band from fluency score
    from nokaman.models.cefr import score_to_cefr

    cefr = score_to_cefr(result["score"])

    # Build feedback bullets
    feedback = _build_speaking_feedback(result, cefr)

    expected = raw.get("expected_cefr")
    band_check = None
    if expected:
        from nokaman.models.cefr import compare_bands

        band_check = compare_bands(cefr, str(expected))

    return {
        "id": raw.get("id", path.stem),
        "language": str(raw.get("language") or "en"),
        "skill": "speaking",
        "score": result["score"],
        "cefr": cefr,
        "dimensions": result["dimensions"],
        "observations": result["observations"],
        "feedback": feedback,
        "limitations": result["limitations"],
        "confidence": confidence,
        "band_check": band_check,
        "source": str(path),
    }


def _build_speaking_feedback(fluency_result: dict, cefr: str) -> list[str]:
    """Generate human-readable feedback bullets from fluency dimensions."""
    dims = fluency_result["dimensions"]
    bullets = []

    if dims["pace"] >= 80:
        bullets.append("Good speaking pace — neither too fast nor too slow.")
    elif dims["pace"] >= 50:
        bullets.append("Try to speak at a more consistent speed.")
    else:
        bullets.append("Your pace could be improved — practice reading aloud with a timer.")

    if dims["continuity"] >= 80:
        bullets.append("Smooth flow with few pauses.")
    elif dims["continuity"] >= 50:
        bullets.append("Some pauses detected — try to connect ideas more smoothly.")
    else:
        bullets.append("Frequent pauses interrupt your flow. Practice longer connected speech.")

    if dims["filler_control"] >= 80:
        bullets.append("Very few hesitation fillers — confident delivery.")
    elif dims["filler_control"] >= 50:
        bullets.append("Occasional fillers like 'um' or 'ah' — try to pause silently instead.")
    else:
        bullets.append("Reduce filler words for a clearer delivery.")

    if dims["phrase_length"] >= 80:
        bullets.append("Good phrase length — sentences feel natural.")
    elif dims["phrase_length"] >= 50:
        bullets.append("Try forming longer, more complex phrases.")
    else:
        bullets.append("Short phrases make speech feel choppy. Combine ideas into longer sentences.")

    bullets.append(f"Estimated CEFR speaking band: {cefr}")
    return bullets


def _optional_float_from(value: object) -> float | None:
    return None if value is None else float(value)


def _optional_int_from(value: object) -> int | None:
    return None if value is None else int(value)
