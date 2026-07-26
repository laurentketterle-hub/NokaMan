from nokaman.rubrics.writing_cohesion import score_writing_cohesion
import pytest
def test_cohesion(): assert 0 <= score_writing_cohesion('The cat sat. The mat comfortable.')['score'] <= 100
def test_empty(): pytest.raises(ValueError, score_writing_cohesion, '')
def test_short(): r = score_writing_cohesion('One.'); assert 'limitations' in r
