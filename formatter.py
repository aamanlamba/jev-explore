"""Render and export headline evaluation results."""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from evaluator import CATEGORIES, HeadlineResult

TABLE_HEADLINE_WIDTH = 60


def _truncate(text: str, width: int) -> str:
    return text if len(text) <= width else text[: width - 1] + "…"


def print_table(results: list[HeadlineResult]) -> None:
    header = (
        f"{'Headline':<{TABLE_HEADLINE_WIDTH}} {'Categories':<30} "
        f"{'Sentiment':<10} {'Sensational.(0-2)':<18} {'Breaking':<8}"
    )
    print(header)
    print("-" * len(header))
    for result in results:
        if result.error:
            print(f"{_truncate(result.headline, TABLE_HEADLINE_WIDTH):<{TABLE_HEADLINE_WIDTH}} ERROR: {result.error}")
            continue
        categories = ", ".join(result.matched_categories()) or "-"
        print(
            f"{_truncate(result.headline, TABLE_HEADLINE_WIDTH):<{TABLE_HEADLINE_WIDTH}} "
            f"{_truncate(categories, 30):<30} "
            f"{result.sentiment:<10} "
            f"{result.sensationalism_score:<18.2f} "
            f"{'yes' if result.is_breaking() else 'no':<8}"
        )


def _result_to_dict(result: HeadlineResult) -> dict:
    return {
        "headline": result.headline,
        "error": result.error,
        "error_type": result.error_type,
        "categories": result.categories,
        "sentiment": result.sentiment,
        "sentiment_probabilities": result.sentiment_probabilities,
        "sentiment_confidence": result.sentiment_confidence,
        "sensationalism_score": None if result.error else result.sensationalism_score,
        "breaking_probability": None if result.error else result.breaking_probability,
    }


def results_to_json(results: list[HeadlineResult]) -> str:
    data = [_result_to_dict(result) for result in results]
    return json.dumps(data, indent=2)


def results_to_csv(results: list[HeadlineResult]) -> str:
    fieldnames = (
        ["headline"]
        + [f"category_{name.lower()}" for name in CATEGORIES]
        + ["sentiment", "sensationalism_score", "breaking_probability", "error", "error_type"]
    )
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for result in results:
        row = {
            "headline": result.headline,
            "error": result.error or "",
            "error_type": result.error_type or "",
        }
        for name in CATEGORIES:
            row[f"category_{name.lower()}"] = result.categories.get(name, "")
        row["sentiment"] = result.sentiment
        row["sensationalism_score"] = "" if result.error else result.sensationalism_score
        row["breaking_probability"] = "" if result.error else result.breaking_probability
        writer.writerow(row)
    return buffer.getvalue()


def write_json(results: list[HeadlineResult], path: str) -> None:
    Path(path).write_text(results_to_json(results))


def write_csv(results: list[HeadlineResult], path: str) -> None:
    Path(path).write_text(results_to_csv(results), newline="")
