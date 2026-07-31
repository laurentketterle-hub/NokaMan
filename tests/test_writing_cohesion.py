from nokaman.rubrics.writing_cohesion import score_writing_cohesion, score_writing_readability, score_batch, export_scores_json
import pytest
import tempfile
import os

def test_cohesion():
    result = score_writing_cohesion('The cat sat. The mat comfortable.')
    assert 0 <= result['score'] <= 100
    assert 'cohesion' in result['dimensions']
    assert 'coherence' in result['dimensions']

def test_empty():
    with pytest.raises(ValueError):
        score_writing_cohesion('')

def test_short():
    r = score_writing_cohesion('One.')
    assert 'limitations' in r
    assert 'dimensions' in r
    assert r['dimensions']['cohesion'] >= 0

def test_all_dimensions_present():
    """All 6 dimensions should be present in the result."""
    text = "The quick brown fox jumps over the lazy dog. However, the dog was not impressed. Furthermore, the fox continued jumping."
    result = score_writing_cohesion(text)
    dims = result['dimensions']
    expected_dims = {'cohesion', 'coherence', 'vocabulary', 'grammar', 'organization', 'task_achievement'}
    assert set(dims.keys()) == expected_dims, f"Missing dims: {expected_dims - set(dims.keys())}"
    for name, value in dims.items():
        assert 0 <= value <= 100, f"Dimension {name} out of range: {value}"

def test_well_structured_text_scores_higher():
    """A well-structured paragraph should score higher than random words."""
    good = "First, the experiment was carefully designed to control for confounding variables. However, the results were not as expected. Furthermore, the sample size was too small to draw definitive conclusions. Therefore, we recommend repeating the study with a larger cohort and more rigorous controls."
    bad = "cat dog house tree car run jump eat sleep big small red blue"
    good_result = score_writing_cohesion(good)
    bad_result = score_writing_cohesion(bad)
    assert good_result['score'] > bad_result['score'], f"good={good_result['score']}, bad={bad_result['score']}"

def test_multilingual_cjk():
    """CJK characters should not crash the scorer."""
    text_cn = "今天天气很好。我去公园散步。看见很多人在跑步。"
    result = score_writing_cohesion(text_cn)
    assert 0 <= result['score'] <= 100

def test_vietnamese_text():
    """Vietnamese text should be scored."""
    text_vi = "Hôm nay thời tiết rất đẹp. Tôi đi dạo trong công viên. Tôi thấy nhiều người đang chạy bộ."
    result = score_writing_cohesion(text_vi)
    assert 0 <= result['score'] <= 100

def test_very_long_text():
    """Long text should not overflow or hang."""
    text = "The cat sat on the mat. " * 200
    result = score_writing_cohesion(text)
    assert 'score' in result
    assert 0 <= result['score'] <= 100

def test_single_word():
    """Single word should be scored minimally."""
    with pytest.raises(ValueError):
        score_writing_cohesion("")

def test_score_writing_readability():
    """Readability scorer should return expected keys."""
    r = score_writing_readability("The quick brown fox jumps over the lazy dog. It was a sunny day.")
    assert 'score' in r
    assert 'avg_sent_len' in r
    assert 'long_word_ratio' in r
    assert 0 <= r['score'] <= 100

def test_score_batch():
    """Batch scoring should return list of results."""
    texts = ["Hello world. This is a test.", "Another text here. With more words."]
    results = score_batch(texts)
    assert len(results) == 2
    for r in results:
        assert 'score' in r

def test_export_scores_json():
    """Export should write valid JSON file."""
    texts = ["Test text one. More words here.", "Second text. And another sentence."]
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp:
        path = export_scores_json(texts, tmp.name)
    try:
        import json
        with open(path) as f:
            data = json.load(f)
        assert len(data) == 2
        for item in data:
            assert 'text' in item
            assert 'result' in item
            assert 'score' in item['result']
    finally:
        os.unlink(path)

def test_observations_include_word_count():
    """Observations should include word and sentence counts."""
    text = "The cat sat on the mat. The dog barked."
    result = score_writing_cohesion(text)
    obs = result.get('observations', {})
    assert 'word_count' in obs
    assert 'sentence_count' in obs
    assert obs['word_count'] > 0

def test_organization_dimension():
    """Organization score should reflect paragraph structure."""
    # Text with clear paragraph structure
    structured = (
        "Introduction paragraph with some background information on the topic.\n\n"
        "However, there are several counterarguments to consider. "
        "First, the data may be incomplete. Furthermore, the methodology has limitations.\n\n"
        "In conclusion, while the initial findings are promising, further research is needed."
    )
    # Text without paragraph structure
    flat = "Introduction paragraph with some background. However there are counterarguments. The data may be incomplete. The methodology has limitations. In conclusion further research needed."
    r_structured = score_writing_cohesion(structured)
    r_flat = score_writing_cohesion(flat)
    # Organization should be higher for structured text
    assert r_structured['dimensions']['organization'] > r_flat['dimensions']['organization']

def test_vocabulary_dimension():
    """Vocabulary score should reflect lexical diversity."""
    # High lexical diversity
    diverse = "The magnificent elephant gracefully traversed the expansive savannah while curious giraffes observed from a considerable distance."
    # Low lexical diversity (repetitive)
    repetitive = "The cat is nice. The cat is good. The cat is small. The cat is fast."
    r_diverse = score_writing_cohesion(diverse)
    r_repetitive = score_writing_cohesion(repetitive)
    assert r_diverse['dimensions']['vocabulary'] > r_repetitive['dimensions']['vocabulary']

def test_dimension_weights_sum():
    """Verify all dimension weights are accounted for."""
    from nokaman.rubrics.writing_cohesion import DIMENSION_WEIGHTS
    total = sum(DIMENSION_WEIGHTS.values())
    assert abs(total - 1.0) < 0.01, f"Dimension weights sum to {total}, expected 1.0"

def test_score_ranges_are_clamped():
    """All dimension scores must be in [0, 100]."""
    for _ in range(10):
        text = "word " * 50
        result = score_writing_cohesion(text)
        for dim, val in result['dimensions'].items():
            assert 0.0 <= val <= 100.0, f"{dim}={val} out of [0,100]"
