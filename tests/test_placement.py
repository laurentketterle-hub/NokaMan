from __future__ import annotations

from nokaman.eval.placement import (
    PLACEMENT_PROMPTS,
    PlacementReport,
    PlacementResult,
    placement_report_to_dict,
    run_placement,
    run_placement_cli,
    save_placement_report,
)
from nokaman.rubrics.registry import CEFR_BANDS


# ── Prompt inventory ───────────────────────────────────────────

def test_three_languages_have_prompts() -> None:
    """EN, KO, JA must all be present."""
    for lang in ("en", "ko", "ja"):
        assert lang in PLACEMENT_PROMPTS, f"missing prompts for {lang}"
        assert len(PLACEMENT_PROMPTS[lang]) >= 5, f"too few prompts for {lang}"


def test_prompts_have_required_fields() -> None:
    for lang, prompts in PLACEMENT_PROMPTS.items():
        for p in prompts:
            assert "id" in p
            assert "skill" in p
            assert "cefr_target" in p
            assert "prompt" in p
            assert p["skill"] in {"writing", "vocabulary", "grammar"}


def test_prompt_ids_are_unique() -> None:
    ids: list[str] = []
    for prompts in PLACEMENT_PROMPTS.values():
        for p in prompts:
            ids.append(p["id"])
    assert len(ids) == len(set(ids)), "duplicate prompt ids"


# ── Core placement logic ───────────────────────────────────────

def test_run_placement_en_returns_report() -> None:
    answers = [
        "I enjoy cooking Italian food on weekends.",
        "Last summer I visited Paris with my sister. We saw the Eiffel Tower at night.",
        "In my opinion, technology helps us stay in touch with distant family members.",
        "It was a very hot day, so we stayed home and watched a movie.",
        "If I had more free time, I would learn to play the guitar.",
    ]
    report = run_placement("en", answers)
    assert isinstance(report, PlacementReport)
    assert report.language == "en"
    assert report.language_name == "English"
    assert "CEFR" in report.frameworks
    assert report.n_items == 5
    assert 0 <= report.overall_score <= 100
    assert report.overall_cefr in CEFR_BANDS
    assert len(report.items) == 5
    assert "writing" in report.skill_breakdown
    assert report.ready_for_ui is True


def test_run_placement_ko_returns_report() -> None:
    answers = [
        "김치찌개를 가장 좋아합니다. 일주일에 두 번 정도 먹습니다.",
        "최근에 기생충을 봤습니다. 가족 이야기인데 반전이 인상적이었습니다.",
        "환경을 위해 텀블러를 사용하는 것이 좋다고 생각합니다.",
        "날씨가 추워서 밖에 나가기 싫습니다.",
        "한국에 가면 다양한 음식을 먹고 싶습니다.",
    ]
    report = run_placement("ko", answers)
    assert report.language == "ko"
    assert report.language_name == "Korean"
    assert "TOPIK" in report.frameworks
    assert report.n_items == 5


def test_run_placement_ja_returns_report() -> None:
    answers = [
        "春が一番好きです。桜がきれいだからです。",
        "コンビニ人間を読みました。普通について考えさせられました。",
        "オンライン学習は自分のペースでできるので効果的です。",
        "昨日は疲れていたので早く寝ました。",
        "明日時間があれば映画を見に行きます。",
    ]
    report = run_placement("ja", answers)
    assert report.language == "ja"
    assert report.language_name == "Japanese"
    assert "JLPT" in report.frameworks
    assert report.n_items == 5


def test_fewer_answers_than_prompts() -> None:
    """Only score prompts for which we have answers."""
    report = run_placement("en", ["hello"])
    assert report.n_items == 1
    assert len(report.items) == 1


def test_more_answers_than_prompts() -> None:
    """Extra answers are silently ignored."""
    answers = ["a", "b", "c", "d", "e", "f", "g"]
    report = run_placement("en", answers)
    # Only 5 built-in EN prompts
    assert report.n_items == 5


def test_custom_prompts() -> None:
    custom = [
        {"id": "custom_1", "skill": "writing", "cefr_target": "A1", "prompt": "Say hi."},
    ]
    report = run_placement("en", ["Hello world!"], prompts=custom)
    assert report.n_items == 1
    assert report.items[0]["prompt_id"] == "custom_1"


# ── CLI entry point ────────────────────────────────────────────

def test_run_placement_cli_returns_dict() -> None:
    result = run_placement_cli("en", ["I like cats."])
    assert isinstance(result, dict)
    assert result["language"] == "en"
    assert "items" in result
    assert "skill_breakdown" in result
    assert result["ready_for_ui"] is True


# ── Serialisation ──────────────────────────────────────────────

def test_placement_report_to_dict() -> None:
    report = run_placement("en", ["Hello world!"])
    d = placement_report_to_dict(report)
    assert isinstance(d, dict)
    assert d["language"] == "en"
    assert "framework_bands" in d


# ── Save to disk ───────────────────────────────────────────────

def test_save_placement_report(tmp_path) -> None:
    path = save_placement_report("en", ["Test answer."], out_dir=tmp_path)
    assert path.exists()
    assert path.suffix == ".json"
    content = path.read_text(encoding="utf-8")
    assert "placement" in path.name
    assert "generated_by" in content
    assert "nokaman placement" in content


# ── License safety ─────────────────────────────────────────────

def test_prompts_are_license_safe() -> None:
    """Ensure no prompt content derives from known copyrighted test banks."""
    banned = {"TOEFL", "IELTS", "Cambridge", "ETS", "Pearson"}
    for lang, prompts in PLACEMENT_PROMPTS.items():
        for p in prompts:
            text = p["prompt"].upper()
            for term in banned:
                assert term.upper() not in text, f"prompt {p['id']} may contain copyrighted term {term}"
