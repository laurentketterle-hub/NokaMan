"""
Multi-language placement test pack (EN / KO / JA minimum).

Provides a polished, single-path placement test suitable for embedding in a
language app — pre-defined prompts, scoring via ToyAbilityModel, and a
structured report with framework bands.

All prompt content is license-safe (original material).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from nokaman.config import OUT_DIR
from nokaman.models.toy import ToyAbilityModel
from nokaman.rubrics.registry import get_language_meta, SUPPORTED_LANGUAGES


# ── Placement prompts (license-safe, original content) ──────────────

PLACEMENT_PROMPTS: dict[str, list[dict[str, str]]] = {
    "en": [
        {
            "id": "en_placement_1",
            "skill": "writing",
            "cefr_target": "A2",
            "prompt": (
                "Write 2–3 sentences about your favorite hobby. "
                "Say what it is, how often you do it, and why you enjoy it."
            ),
        },
        {
            "id": "en_placement_2",
            "skill": "writing",
            "cefr_target": "B1",
            "prompt": (
                "Describe a recent trip or outing you took. "
                "Include where you went, who was with you, and one thing that surprised you."
            ),
        },
        {
            "id": "en_placement_3",
            "skill": "writing",
            "cefr_target": "B2",
            "prompt": (
                "Some people think technology makes us more connected; others say it makes "
                "us more isolated. Write a short paragraph giving your opinion and one reason."
            ),
        },
        {
            "id": "en_placement_4",
            "skill": "vocabulary",
            "cefr_target": "B1",
            "prompt": (
                "Read this short text and then rewrite it using different words while "
                "keeping the same meaning: 'The weather was very hot, so we decided to stay "
                "inside and watch a movie.'"
            ),
        },
        {
            "id": "en_placement_5",
            "skill": "grammar",
            "cefr_target": "B2",
            "prompt": (
                "Complete the following sentence in a natural way, using at least one "
                "conditional form: 'If I had more free time, ...'"
            ),
        },
    ],
    "ko": [
        {
            "id": "ko_placement_1",
            "skill": "writing",
            "cefr_target": "A2",
            "prompt": (
                "좋아하는 음식에 대해 2-3문장으로 써 보세요. "
                "무슨 음식인지, 얼마나 자주 먹는지, 왜 좋아하는지 이야기해 주세요."
            ),
        },
        {
            "id": "ko_placement_2",
            "skill": "writing",
            "cefr_target": "B1",
            "prompt": (
                "최근에 본 영화나 드라마에 대해 설명해 보세요. "
                "줄거리를 간단히 말하고, 어떤 점이 인상 깊었는지 이야기해 주세요."
            ),
        },
        {
            "id": "ko_placement_3",
            "skill": "writing",
            "cefr_target": "B2",
            "prompt": (
                "환경 보호를 위해 개인이 할 수 있는 일에는 어떤 것이 있을까요? "
                "자신의 의견과 한 가지 구체적인 예를 들어 설명해 보세요."
            ),
        },
        {
            "id": "ko_placement_4",
            "skill": "vocabulary",
            "cefr_target": "B1",
            "prompt": (
                "다음 문장을 다른 표현으로 바꿔 써 보세요. "
                "의미는 같게 유지해야 합니다: '요즘 날씨가 너무 추워서 밖에 나가기 싫어요.'"
            ),
        },
        {
            "id": "ko_placement_5",
            "skill": "grammar",
            "cefr_target": "B2",
            "prompt": (
                "다음 문장을 완성해 보세요. '-면 좋겠다' 또는 '-더라면' 형태를 "
                "사용해야 합니다: '만약 한국에 여행을 갈 수 있다면, ...'"
            ),
        },
    ],
    "ja": [
        {
            "id": "ja_placement_1",
            "skill": "writing",
            "cefr_target": "A2",
            "prompt": (
                "好きな季節について2〜3文で書いてください。"
                "どの季節が好きか、その季節に何をするか、なぜ好きなのかを書いてください。"
            ),
        },
        {
            "id": "ja_placement_2",
            "skill": "writing",
            "cefr_target": "B1",
            "prompt": (
                "最近読んだ本や漫画について説明してください。"
                "内容を簡単にまとめ、どんなところが面白かったか教えてください。"
            ),
        },
        {
            "id": "ja_placement_3",
            "skill": "writing",
            "cefr_target": "B2",
            "prompt": (
                "オンライン学習と対面授業のどちらが効果的だと思いますか。"
                "自分の意見と理由を一つ挙げて説明してください。"
            ),
        },
        {
            "id": "ja_placement_4",
            "skill": "vocabulary",
            "cefr_target": "B1",
            "prompt": (
                "次の文を、意味を変えずに違う表現で書き直してください: "
                "'昨日はとても疲れていたので、早く寝ました。'"
            ),
        },
        {
            "id": "ja_placement_5",
            "skill": "grammar",
            "cefr_target": "B2",
            "prompt": (
                "次の文を完成させてください。条件形（〜ば、〜たら）を使ってください: "
                "'もし明日時間があれば、...'"
            ),
        },
    ],
}


@dataclass
class PlacementResult:
    """Holds a single prompt + answer + score."""

    prompt_id: str
    skill: str
    cefr_target: str
    prompt: str
    answer: str
    score: float
    cefr: str
    framework_bands: dict[str, Any] = field(default_factory=dict)
    features: dict[str, Any] = field(default_factory=dict)


@dataclass
class PlacementReport:
    """Full placement report suitable for embedding in a language app."""

    language: str
    language_name: str
    frameworks: list[str]
    n_items: int
    overall_score: float
    overall_cefr: str
    framework_bands: dict[str, Any]
    skill_breakdown: dict[str, dict[str, Any]]
    items: list[dict[str, Any]]
    ready_for_ui: bool = True
    model: str = "ToyAbilityModel"


def run_placement(
    language: str,
    answers: list[str],
    *,
    prompts: list[dict[str, str]] | None = None,
) -> PlacementReport:
    """Run a full multi-skill placement test for *language*.

    Parameters
    ----------
    language : str
        ISO language code (``en``, ``ko``, ``ja``, …).
    answers : list[str]
        Learner free-text answers, one per prompt (same order).
    prompts : list[dict] | None
        Custom prompt set.  When ``None``, the built-in placement prompts
        for *language* are used.

    Returns
    -------
    PlacementReport
        Structured report with overall CEFR, framework bands, skill breakdown,
        and per-item detail.
    """
    code = language.strip().lower()
    meta = get_language_meta(code)
    model = ToyAbilityModel(language=code)

    if prompts is None:
        prompts = PLACEMENT_PROMPTS.get(code, PLACEMENT_PROMPTS.get("en", []))

    # Truncate answers to match prompt count
    n = min(len(prompts), len(answers))
    results: list[PlacementResult] = []
    skill_scores: dict[str, list[float]] = {}

    for i in range(n):
        prompt_def = prompts[i]
        answer_text = answers[i] if i < len(answers) else ""
        scored = model.score_text(answer_text, skill=prompt_def.get("skill", "writing"))

        result = PlacementResult(
            prompt_id=prompt_def["id"],
            skill=prompt_def.get("skill", "writing"),
            cefr_target=prompt_def.get("cefr_target", "A2"),
            prompt=prompt_def["prompt"],
            answer=answer_text,
            score=scored["score"],
            cefr=scored["cefr"],
            framework_bands=scored.get("framework_bands", {}),
            features=scored.get("features", {}),
        )
        results.append(result)

        sk = result.skill
        skill_scores.setdefault(sk, []).append(result.score)

    # Overall average
    all_scores = [r.score for r in results]
    overall = sum(all_scores) / len(all_scores) if all_scores else 0.0

    from nokaman.models.cefr import score_to_cefr

    overall_cefr = score_to_cefr(overall)

    # Framework bands (use writing skill as representative)
    writing_scored = model.score_text(
        " ".join(a for a in answers[:3] if a), skill="writing"
    )
    framework_bands = writing_scored.get("framework_bands", {})

    # Skill breakdown
    breakdown: dict[str, dict[str, Any]] = {}
    for sk, scores in skill_scores.items():
        avg = sum(scores) / len(scores)
        breakdown[sk] = {
            "n_items": len(scores),
            "average_score": round(avg, 2),
            "cefr": score_to_cefr(avg),
        }

    return PlacementReport(
        language=code,
        language_name=meta["name"],
        frameworks=list(meta["frameworks"]),
        n_items=n,
        overall_score=round(overall, 2),
        overall_cefr=overall_cefr,
        framework_bands=framework_bands,
        skill_breakdown=breakdown,
        items=[
            {
                "prompt_id": r.prompt_id,
                "skill": r.skill,
                "cefr_target": r.cefr_target,
                "prompt": r.prompt,
                "answer": r.answer,
                "score": r.score,
                "cefr": r.cefr,
                "framework_bands": r.framework_bands,
                "features": r.features,
            }
            for r in results
        ],
    )


def placement_report_to_dict(report: PlacementReport) -> dict[str, Any]:
    """Serialise a PlacementReport to a plain dict (JSON-safe)."""
    return {
        "language": report.language,
        "language_name": report.language_name,
        "frameworks": report.frameworks,
        "n_items": report.n_items,
        "overall_score": report.overall_score,
        "overall_cefr": report.overall_cefr,
        "framework_bands": report.framework_bands,
        "skill_breakdown": report.skill_breakdown,
        "items": report.items,
        "ready_for_ui": report.ready_for_ui,
        "model": report.model,
    }


def run_placement_cli(language: str, answers: list[str]) -> dict[str, Any]:
    """Single CLI/API entry point — run placement and return dict.

    This is the function wired to ``nokaman eval placement``.
    """
    report = run_placement(language, answers)
    return placement_report_to_dict(report)


def save_placement_report(
    language: str,
    answers: list[str],
    *,
    out_dir: Path | None = None,
) -> Path:
    """Run placement and persist the JSON report to disk.

    Returns the path to the saved report file.
    """
    report = run_placement(language, answers)
    d = placement_report_to_dict(report)
    d["generated_by"] = "nokaman placement"

    dest = (out_dir or OUT_DIR)
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / f"placement_{language}_{report.overall_cefr}.json"
    path.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
