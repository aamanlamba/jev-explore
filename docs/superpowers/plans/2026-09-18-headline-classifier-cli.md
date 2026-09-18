# Headline Classifier CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a CLI that evaluates a list of news headlines across multiple TypeSafe dimensions (topic category, sentiment, sensationalism, breaking-news likelihood) and reports results as a console table, and optionally JSON or CSV.

**Architecture:** Three flat modules at the repo root — `evaluator.py` (builds TypeSafe questions, calls `system_one` per headline, returns structured results), `formatter.py` (renders the console table and writes JSON/CSV), and `headline_cli.py` (argument parsing and orchestration) — plus a bundled `sample_headlines.txt`. Matches the existing project's flat, dependency-light style (see `jev-explore.ipynb`).

**Tech Stack:** Python 3.9+, `typesafe-sdk` (installed: 0.7.0), `python-dotenv`. No new dependencies — CSV/JSON use the standard library.

**Spec:** `docs/superpowers/specs/2026-09-18-headline-classifier-cli-design.md`

## Global Constraints

- No new dependencies beyond `requirements.txt` (`ipykernel`, `python-dotenv`, `typesafe-sdk`).
- Fixed category list (exactly these 8, in this order): Politics, Business, Technology, Sports, Entertainment, Health, Science, World.
- A category or breaking-news "match" uses probability > 0.5 as the threshold everywhere (table and CSV `is_breaking`/matched-category display).
- `--format` accepts only `json` or `csv`; default is `json`.
- Testing approach is manual verification against the real TypeSafe API (the project's `.env` already has a working `TYPESAFE_API_KEY`) — no automated test suite in this version, per the spec.
- Installed SDK response shape (verified against `typesafe_sdk` 0.7.0 in `.venv`): `response.answers["key"]` returns a `NoulAnswer` (`.noul: float`), `ChoiceAnswer` (`.choice: str`, `.confidence: float`, `.probabilities: dict[str, float]`), or `ScoreAnswer` (`.score: float`, `.confidence: float`, `.probabilities: dict[int, float]`) depending on question type. Use this shape, not any other shape you find in external docs.
- Catch `typesafe_sdk.TypeSafeError` (the SDK's base exception) for per-headline failures — it covers all specific TypeSafe error subclasses.

---

### Task 1: Bundled sample headlines

**Files:**
- Create: `sample_headlines.txt`

**Interfaces:**
- Produces: a plain text file, one headline per line, read by `headline_cli.py`'s `load_headlines()` in Task 4.

- [ ] **Step 1: Create the sample headlines file**

Create `sample_headlines.txt` at the repo root with exactly this content (one headline per line, no blank lines), chosen so every one of the 8 categories is plausibly triggered by at least one headline:

```
Senate Passes Sweeping Immigration Reform Bill After Marathon Overnight Session
Tech Giant's Stock Soars After Blowout Earnings, Fueling Market Rally
New AI Chip Promises to Cut Data Center Energy Use in Half
Underdog Team Stuns Rivals to Clinch Championship in Overtime Thriller
Beloved Actor Announces Surprise Retirement After Decades-Long Career
Researchers Identify New Gene Linked to Early-Onset Alzheimer's
NASA's New Telescope Captures Unprecedented Images of Distant Galaxy
Global Leaders Meet in Geneva to Negotiate Climate Emergency Response
Local Hospital Opens First Dedicated Pediatric Cancer Wing
Streaming Platform's New Series Breaks First-Week Viewership Records
```

- [ ] **Step 2: Verify the file**

Run: `wc -l sample_headlines.txt && cat sample_headlines.txt`
Expected: 10 lines (or 9 if your `wc -l` doesn't count a final line without trailing newline — either is fine as long as `cat` shows all 10 headlines), each a single headline with no blank lines.

- [ ] **Step 3: Commit**

```bash
git add sample_headlines.txt
git commit -m "Add bundled sample headlines for headline classifier CLI"
```

---

### Task 2: `evaluator.py` — TypeSafe question building and per-headline evaluation

**Files:**
- Create: `evaluator.py`

**Interfaces:**
- Consumes: `typesafe_sdk.Choice`, `typesafe_sdk.Noul`, `typesafe_sdk.Score`, `typesafe_sdk.TypeSafeClient`, `typesafe_sdk.TypeSafeError` (installed SDK 0.7.0).
- Produces (used by `formatter.py` in Task 3 and `headline_cli.py` in Task 4):
  - `CATEGORIES: list[str]` — the 8 fixed category names, in order.
  - `MATCH_THRESHOLD: float` — `0.5`.
  - `class HeadlineResult` with fields `headline: str`, `categories: dict[str, float]`, `sentiment: str`, `sentiment_probabilities: dict[str, float]`, `sensationalism_score: float`, `breaking_probability: float`, `error: str | None`, and methods `matched_categories(threshold: float = MATCH_THRESHOLD) -> list[str]` and `is_breaking(threshold: float = MATCH_THRESHOLD) -> bool`.
  - `evaluate_headline(client: TypeSafeClient, headline: str) -> HeadlineResult`
  - `evaluate_headlines(client: TypeSafeClient, headlines: list[str]) -> list[HeadlineResult]`

- [ ] **Step 1: Write `evaluator.py`**

```python
"""Evaluate news headlines across multiple TypeSafe dimensions."""
from __future__ import annotations

from dataclasses import dataclass, field

from typesafe_sdk import Choice, Noul, Score, TypeSafeClient, TypeSafeError

CATEGORIES = [
    "Politics",
    "Business",
    "Technology",
    "Sports",
    "Entertainment",
    "Health",
    "Science",
    "World",
]

MATCH_THRESHOLD = 0.5


@dataclass
class HeadlineResult:
    headline: str
    categories: dict[str, float] = field(default_factory=dict)
    sentiment: str = ""
    sentiment_probabilities: dict[str, float] = field(default_factory=dict)
    sensationalism_score: float = 0.0
    breaking_probability: float = 0.0
    error: str | None = None

    def matched_categories(self, threshold: float = MATCH_THRESHOLD) -> list[str]:
        return [name for name, prob in self.categories.items() if prob > threshold]

    def is_breaking(self, threshold: float = MATCH_THRESHOLD) -> bool:
        return self.breaking_probability > threshold


def build_questions() -> dict[str, Choice | Noul | Score]:
    questions: dict[str, Choice | Noul | Score] = {
        f"category_{name.lower()}": Noul(
            instructions=f"The headline is about {name}.",
        )
        for name in CATEGORIES
    }
    questions["sentiment"] = Choice(
        instructions="What is the overall sentiment or tone of this headline?",
        criteria={
            "positive": "Upbeat, favorable, or celebratory framing",
            "neutral": "Matter-of-fact, no clear positive or negative framing",
            "negative": "Unfavorable, alarming, or critical framing",
        },
    )
    questions["sensationalism"] = Score(
        instructions="How sensational or clickbait-y is this headline's framing?",
        criteria=[
            "Straightforward and factual, no exaggeration",
            "Somewhat attention-grabbing, mild exaggeration",
            "Highly sensational, clickbait framing",
        ],
    )
    questions["breaking"] = Noul(
        instructions="This headline describes breaking or time-sensitive news.",
    )
    return questions


def evaluate_headline(client: TypeSafeClient, headline: str) -> HeadlineResult:
    result = HeadlineResult(headline=headline)
    try:
        response = client.system_one(state=headline, questions=build_questions())
    except TypeSafeError as exc:
        result.error = str(exc)
        return result

    for name in CATEGORIES:
        answer = response.answers[f"category_{name.lower()}"]
        result.categories[name] = answer.noul

    sentiment_answer = response.answers["sentiment"]
    result.sentiment = sentiment_answer.choice
    result.sentiment_probabilities = dict(sentiment_answer.probabilities)

    result.sensationalism_score = response.answers["sensationalism"].score
    result.breaking_probability = response.answers["breaking"].noul

    return result


def evaluate_headlines(client: TypeSafeClient, headlines: list[str]) -> list[HeadlineResult]:
    return [evaluate_headline(client, headline) for headline in headlines]
```

- [ ] **Step 2: Manually verify against the real TypeSafe API**

Run:

```bash
.venv/bin/python3 -c "
from dotenv import load_dotenv
load_dotenv()
from typesafe_sdk import TypeSafeClient
from evaluator import evaluate_headline

client = TypeSafeClient()
result = evaluate_headline(client, 'Tech Giant\'s Stock Soars After Blowout Earnings, Fueling Market Rally')
print(result)
print('matched categories:', result.matched_categories())
print('is_breaking:', result.is_breaking())
"
```

Expected: no exception; `result.error` is `None`; `result.categories` has all 8 category names as keys with float probabilities between 0 and 1 (Business and/or Technology should score highest); `result.sentiment` is one of `positive`/`neutral`/`negative`; `result.sensationalism_score` and `result.breaking_probability` are floats. If `TYPESAFE_API_KEY` is missing or invalid, you'll see a `TypeSafeAuthenticationError` traceback — confirm `.env` has a valid key before treating this as a bug.

- [ ] **Step 3: Commit**

```bash
git add evaluator.py
git commit -m "Add evaluator.py for multi-dimension headline scoring via TypeSafe"
```

---

### Task 3: `formatter.py` — console table and JSON/CSV export

**Files:**
- Create: `formatter.py`

**Interfaces:**
- Consumes: `evaluator.CATEGORIES`, `evaluator.HeadlineResult` (from Task 2).
- Produces (used by `headline_cli.py` in Task 4):
  - `print_table(results: list[HeadlineResult]) -> None`
  - `write_json(results: list[HeadlineResult], path: str) -> None`
  - `write_csv(results: list[HeadlineResult], path: str) -> None`

- [ ] **Step 1: Write `formatter.py`**

```python
"""Render and export headline evaluation results."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from evaluator import CATEGORIES, HeadlineResult

TABLE_HEADLINE_WIDTH = 60


def _truncate(text: str, width: int) -> str:
    return text if len(text) <= width else text[: width - 1] + "…"


def print_table(results: list[HeadlineResult]) -> None:
    header = (
        f"{'Headline':<{TABLE_HEADLINE_WIDTH}} {'Categories':<30} "
        f"{'Sentiment':<10} {'Sensational.':<12} {'Breaking':<8}"
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
            f"{result.sensationalism_score:<12.2f} "
            f"{'yes' if result.is_breaking() else 'no':<8}"
        )


def _result_to_dict(result: HeadlineResult) -> dict:
    return {
        "headline": result.headline,
        "error": result.error,
        "categories": result.categories,
        "sentiment": result.sentiment,
        "sentiment_probabilities": result.sentiment_probabilities,
        "sensationalism_score": result.sensationalism_score,
        "breaking_probability": result.breaking_probability,
    }


def write_json(results: list[HeadlineResult], path: str) -> None:
    data = [_result_to_dict(result) for result in results]
    Path(path).write_text(json.dumps(data, indent=2))


def write_csv(results: list[HeadlineResult], path: str) -> None:
    fieldnames = (
        ["headline"]
        + [f"category_{name.lower()}" for name in CATEGORIES]
        + ["sentiment", "sensationalism_score", "breaking_probability", "error"]
    )
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            row = {"headline": result.headline, "error": result.error or ""}
            for name in CATEGORIES:
                row[f"category_{name.lower()}"] = result.categories.get(name, "")
            row["sentiment"] = result.sentiment
            row["sensationalism_score"] = result.sensationalism_score
            row["breaking_probability"] = result.breaking_probability
            writer.writerow(row)
```

- [ ] **Step 2: Manually verify with synthetic data (no API calls needed)**

Run:

```bash
.venv/bin/python3 -c "
from evaluator import HeadlineResult
from formatter import print_table, write_json, write_csv

results = [
    HeadlineResult(
        headline='Tech Giant Stock Soars After Blowout Earnings',
        categories={'Politics': 0.02, 'Business': 0.91, 'Technology': 0.85, 'Sports': 0.01, 'Entertainment': 0.01, 'Health': 0.01, 'Science': 0.05, 'World': 0.1},
        sentiment='positive',
        sentiment_probabilities={'positive': 0.88, 'neutral': 0.1, 'negative': 0.02},
        sensationalism_score=0.4,
        breaking_probability=0.6,
    ),
    HeadlineResult(headline='A headline that failed to evaluate', error='connection timed out'),
]
print_table(results)
write_json(results, '/tmp/_test_results.json')
write_csv(results, '/tmp/_test_results.csv')
print(open('/tmp/_test_results.json').read())
print(open('/tmp/_test_results.csv').read())
"
```

Expected: console table prints two rows — the first showing `Business, Technology` under Categories, `positive`, `0.40`, `yes` (breaking); the second showing `ERROR: connection timed out`. The JSON file contains a 2-element array with full nested data. The CSV file has a header row plus 2 data rows with flat columns per category.

- [ ] **Step 3: Commit**

```bash
git add formatter.py
git commit -m "Add formatter.py for console table and JSON/CSV export"
```

---

### Task 4: `headline_cli.py` — CLI entry point, and README update

**Files:**
- Create: `headline_cli.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: `evaluator.evaluate_headlines` (Task 2), `formatter.print_table`, `formatter.write_json`, `formatter.write_csv` (Task 3).
- Produces: the runnable CLI (`python headline_cli.py ...`), and `main(argv: list[str] | None = None) -> int` as the programmatic entry point.

- [ ] **Step 1: Write `headline_cli.py`**

```python
"""CLI entry point for evaluating news headlines with TypeSafe."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from typesafe_sdk import TypeSafeClient

from evaluator import evaluate_headlines
from formatter import print_table, write_csv, write_json

DEFAULT_SAMPLE_FILE = Path(__file__).parent / "sample_headlines.txt"


def load_headlines(path: str | None) -> list[str]:
    file_path = Path(path) if path else DEFAULT_SAMPLE_FILE
    if not file_path.is_file():
        raise SystemExit(f"Input file not found: {file_path}")
    lines = [line.strip() for line in file_path.read_text().splitlines()]
    headlines = [line for line in lines if line]
    if not headlines:
        raise SystemExit(f"Input file is empty: {file_path}")
    return headlines


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate news headlines across multiple dimensions with TypeSafe."
    )
    parser.add_argument(
        "--input",
        help="Path to a text file of headlines, one per line. Defaults to the bundled sample set.",
    )
    parser.add_argument(
        "--output",
        help="Path to write results to. If omitted, only the console table is shown.",
    )
    parser.add_argument(
        "--format",
        choices=["json", "csv"],
        default="json",
        help="Format for --output (default: json).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    load_dotenv()
    if not os.getenv("TYPESAFE_API_KEY"):
        print(
            "Error: TYPESAFE_API_KEY is not set. Add it to your .env file or environment.",
            file=sys.stderr,
        )
        return 1

    headlines = load_headlines(args.input)

    client = TypeSafeClient()
    results = evaluate_headlines(client, headlines)

    print_table(results)

    if args.output:
        if args.format == "json":
            write_json(results, args.output)
        else:
            write_csv(results, args.output)
        print(f"\nWrote {len(results)} results to {args.output} ({args.format})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Manually verify the full CLI against the real API**

Run each of these and inspect the output:

```bash
.venv/bin/python3 headline_cli.py
```
Expected: a console table with 10 rows (one per bundled sample headline), each showing matched categories, sentiment, sensationalism score, and breaking yes/no. No tracebacks.

```bash
.venv/bin/python3 headline_cli.py --output /tmp/_cli_results.json --format json
cat /tmp/_cli_results.json
```
Expected: table prints as before, plus a "Wrote 10 results to /tmp/_cli_results.json (json)" line; the file contains a JSON array of 10 objects with full nested fields.

```bash
.venv/bin/python3 headline_cli.py --output /tmp/_cli_results.csv --format csv
cat /tmp/_cli_results.csv
```
Expected: table prints as before, plus a "Wrote 10 results..." line; the CSV has a header row and 10 data rows with flat columns.

```bash
.venv/bin/python3 headline_cli.py --input /nonexistent/file.txt
```
Expected: exits with `Input file not found: /nonexistent/file.txt`, no traceback, no API calls made.

- [ ] **Step 3: Update `README.md` with CLI usage**

Add a new section to `README.md` (after the existing "Running the Notebook" section) documenting the CLI:

```markdown
## Running the Headline Classifier CLI

In addition to the notebook, this project includes `headline_cli.py`, a
command-line tool that scores a list of news headlines across multiple
dimensions using TypeSafe: topic category (multi-label, one of Politics,
Business, Technology, Sports, Entertainment, Health, Science, World),
sentiment, sensationalism, and whether the headline reads as breaking news.

```bash
# Evaluate the bundled sample headlines, print a console table
python headline_cli.py

# Evaluate your own headlines (one per line)
python headline_cli.py --input my_headlines.txt

# Also write full results to a file
python headline_cli.py --input my_headlines.txt --output results.json --format json
python headline_cli.py --input my_headlines.txt --output results.csv --format csv
```

`--format` defaults to `json` and only matters when `--output` is given.
JSON output includes full per-category probabilities and distributions;
CSV output is a flattened, spreadsheet-friendly version.
```

- [ ] **Step 4: Commit**

```bash
git add headline_cli.py README.md
git commit -m "Add headline_cli.py entry point and document CLI usage"
```

---

## Self-Review Notes

- **Spec coverage:** bundled sample set (Task 1), file input (Task 4 `load_headlines`), all 4 dimension types incl. 8-category multi-label (Task 2), console table always printed (Task 4), `--output`/`--format` for JSON and CSV (Tasks 3 & 4), fail-fast on missing API key (Task 4 Step 1 `main`), fail-fast on missing/empty input file (Task 4 `load_headlines`), per-headline error handling that continues the batch (Task 2 `evaluate_headline` catches `TypeSafeError` per call, not around the whole loop), manual verification testing (every task's Step 2), README documentation (Task 4 Step 3). All spec sections are covered.
- **Placeholder scan:** none found — every step has runnable code or an exact command with expected output.
- **Type consistency:** `HeadlineResult` fields/methods defined in Task 2 are used identically in Task 3 (`formatter.py`) and Task 4 (`headline_cli.py`); `CATEGORIES` and `MATCH_THRESHOLD` from Task 2 are the only source of category names/threshold, referenced (not redefined) in Tasks 3 and 4.
