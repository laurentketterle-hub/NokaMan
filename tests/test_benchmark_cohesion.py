"""Benchmark for writing cohesion scorer."""
import time
from nokaman.rubrics.writing_cohesion import score_writing_cohesion

SAMPLE = "The quick brown fox jumps over the lazy dog. However, the dog was not impressed. Furthermore, the fox continued jumping. In conclusion, both animals went home."

def test_benchmark():
    start = time.time()
    for _ in range(100):
        result = score_writing_cohesion(SAMPLE)
    elapsed = time.time() - start
    assert elapsed < 5.0, f"Too slow: {elapsed:.2f}s for 100 iterations"
    assert result["score"] >= 0
