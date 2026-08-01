"""Tests for Spanish DELE framework bands and ES samples."""
from pathlib import Path
from nokaman.models.toy import ToyAbilityModel
from nokaman.eval.pipeline import evaluate_demo


def test_es_framework_bands_include_dele() -> None:
    """Spanish demo output must include dele field."""
    r = ToyAbilityModel("es").score_text(
        "Me gusta aprender español porque es un idioma muy bonito y útil.",
        skill="writing",
    )
    bands = r["framework_bands"]
    assert "dele" in bands
    assert bands["dele"].startswith("DELE")


def test_es_demo_includes_dele_field() -> None:
    """Demo evaluation for Spanish must include DELE band."""
    d = evaluate_demo("es")
    bands = d["framework_bands"]
    assert bands.get("dele")
    assert bands["dele"] in {
        "DELE A1", "DELE A2", "DELE B1", "DELE B2", "DELE C1", "DELE C2"
    }


def test_es_dele_band_matches_cefr() -> None:
    """DELE band should correspond to CEFR level."""
    model = ToyAbilityModel("es")
    # High-quality text should map to higher bands
    r = model.score_text(
        "A mi juicio, la literatura hispanoamericana contemporánea representa "
        "una de las manifestaciones culturales más significativas del siglo XXI. "
        "No obstante, su difusión internacional sigue siendo limitada debido a "
        "barreras lingüísticas y a la escasez de traducciones de calidad. "
        "Por consiguiente, resulta imperativo fomentar políticas culturales que "
        "incentiven la traducción y promuevan el intercambio académico entre "
        "Europa y América Latina, especialmente en el ámbito de las humanidades.",
        skill="writing",
    )
    assert r["framework_bands"]["dele"] in {"DELE B1", "DELE B2", "DELE C1", "DELE C2"}


def test_es_samples_load_and_score() -> None:
    """ES writing samples at different levels should produce valid scores."""
    from nokaman.data.loader import load_sample, list_sample_files
    import os

    samples_dir = os.path.join(os.path.dirname(__file__), "..", "data", "samples")
    es_files = [f for f in os.listdir(samples_dir) if f.startswith("es_")]
    assert len(es_files) >= 4, f"Expected ≥4 ES sample files, got {len(es_files)}"

    model = ToyAbilityModel("es")
    for fname in es_files:
        sample = load_sample(Path(samples_dir) / fname)
        r = model.score_text(str(sample.get("text", "")), skill=str(sample.get("skill", "writing")))
        assert 0 <= r["score"] <= 100, f"Score out of range for {fname}: {r['score']}"
        assert r["cefr"] in {"A1", "A2", "B1", "B2", "C1", "C2"}
        assert "dele" in r["framework_bands"]
