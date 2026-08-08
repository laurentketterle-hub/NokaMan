"""Batch evaluate CSV export for teacher workflows (Closes #32)."""
from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import List, Dict, Any


def results_to_csv(results: List[Dict[str, Any]], output_path: str = "") -> str:
    """Convert evaluation results to CSV format.

    Args:
        results: List of evaluation result dicts, each with sample_id, score, and dimensions.
        output_path: Optional file path to write CSV. If empty, returns CSV string.

    Returns:
        CSV string if output_path is empty, otherwise confirmation message.
    """
    if not results:
        return "sample_id\n"

    # Collect all dimension keys across results
    dim_keys: set = set()
    for r in results:
        dims = r.get("dimensions", {})
        dim_keys.update(dims.keys())
    dim_keys = sorted(dim_keys)

    # Build headers
    headers = ["sample_id", "score", "word_count"] + list(dim_keys)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)

    for r in results:
        dims = r.get("dimensions", {})
        row = [
            r.get("sample_id", ""),
            r.get("score", ""),
            r.get("word_count", ""),
        ]
        for key in dim_keys:
            row.append(dims.get(key, ""))
        writer.writerow(row)

    csv_content = output.getvalue()

    if output_path:
        Path(output_path).write_text(csv_content, encoding="utf-8")
        return "CSV written to {} ({} rows)".format(output_path, len(results))

    return csv_content


def batch_evaluate_csv(
    samples: List[dict],
    evaluate_fn,
    output_path: str = "",
) -> str:
    """Run evaluation on multiple samples and export as CSV.

    Args:
        samples: List of sample dicts with 'sample_id' and 'text' keys.
        evaluate_fn: Scoring function that takes text and returns a score dict.
        output_path: Optional file path for CSV output.

    Returns:
        CSV string or confirmation message.
    """
    results = []
    for sample in samples:
        sample_id = sample.get("sample_id", "unknown")
        text = sample.get("text", "")
        try:
            result = evaluate_fn(text)
        except Exception as exc:
            result = {"score": "ERROR", "error": str(exc)[:200]}
        result["sample_id"] = sample_id
        results.append(result)

    return results_to_csv(results, output_path)


def format_csv_preview(csv_content: str, max_rows: int = 5) -> str:
    """Format CSV content as a readable preview table."""
    lines = csv_content.strip().split("\n")
    if len(lines) <= 1:
        return "No data."

    preview = lines[:min(len(lines), max_rows + 1)]
    result = "CSV Preview ({} total rows):\n".format(len(lines) - 1)
    result += "\n".join(preview)
    if len(lines) > max_rows + 1:
        result += "\n... and {} more rows".format(len(lines) - max_rows - 1)
    return result
