# Headline Classifier CLI — Design

## Purpose

A small command-line tool that evaluates a set of news article headlines
across multiple dimensions using the TypeSafe API (Jev / System One).
It extends the existing exploration in `jev-explore.ipynb` — same stack,
same API key handling — but as a reusable CLI instead of a notebook cell.

## Scope

- Input: a list of news headlines, either the bundled sample set or a
  user-supplied text file (one headline per line).
- Evaluation: for each headline, ask TypeSafe a fixed set of questions
  covering topic category (multi-label), sentiment, sensationalism, and
  breaking-news likelihood — all in a single `system_one` call per
  headline.
- Output: a console table always; optionally a JSON or CSV file.
- Out of scope: fetching headlines from a live news API, a config file
  for custom categories, automated test suite (manual verification only
  for this first version).

## Components

| File | Responsibility |
| --- | --- |
| `sample_headlines.txt` | Bundled diverse sample (~10 headlines spanning all 8 categories), used when `--input` is omitted. |
| `evaluator.py` | Builds the TypeSafe question set and calls `client.system_one(state=headline, questions={...})` once per headline. |
| `formatter.py` | Renders the console table; serializes results to JSON or CSV. |
| `headline_cli.py` | Entry point: argument parsing, orchestration, error handling. |

No new package structure — flat modules alongside the existing notebook,
matching the project's current simplicity.

## Dimensions evaluated (per headline, one batched request)

- **8× `Noul`** — one per category: Politics, Business, Technology,
  Sports, Entertainment, Health, Science, World. Multi-label: a
  headline can score high on more than one (e.g. a headline can be both
  "Business" and "Technology").
- **`Choice`** — sentiment: `positive` / `neutral` / `negative`.
- **`Score`** — sensationalism, along levels from factual/straightforward
  to attention-grabbing to clickbait.
- **`Noul`** — is this breaking / time-sensitive news.

All 11 questions are asked together in one `system_one` call per
headline (independent questions over the same state run in parallel,
per TypeSafe's guidance).

## CLI interface

```bash
python headline_cli.py
python headline_cli.py --input my_headlines.txt
python headline_cli.py --input my_headlines.txt --output results.json --format json
python headline_cli.py --input my_headlines.txt --output results.csv --format csv
```

- `--input PATH` (optional) — text file, one headline per line. Defaults
  to the bundled `sample_headlines.txt`.
- `--output PATH` (optional) — file to write results to. If omitted,
  only the console table is shown.
- `--format {json,csv}` (optional, default `json`) — format for
  `--output`. Only meaningful when `--output` is given.

### Console table

Always printed. Columns: headline (truncated), matched categories
(those with probability > 0.5, comma-joined), sentiment, sensationalism
score, breaking (yes/no derived from probability > 0.5).

### JSON output

Full nested structure per headline: all 8 category probabilities,
full sentiment distribution + confidence, sensationalism score,
breaking-news probability.

### CSV output

One flat row per headline: headline, one column per category
probability, sentiment (top choice only), sensationalism score,
breaking probability. Loses the nested detail (full distributions)
that JSON keeps — acceptable for spreadsheet use.

## Data flow

1. Load headlines — from `--input` file if given, else
   `sample_headlines.txt`.
2. For each headline, call `evaluator.evaluate(headline)` →
   TypeSafe `system_one` request → parsed result object.
3. Collect all per-headline results.
4. Print console table via `formatter.print_table(results)`.
5. If `--output` given, write via `formatter.write_json(...)` or
   `formatter.write_csv(...)` depending on `--format`.

## Error handling

- Missing `TYPESAFE_API_KEY` (via `.env` / environment) fails fast with
  a clear message before any API calls are made.
- Empty or missing `--input` file: clear error, exit before calling the
  API.
- A per-headline TypeSafe API error (network/API error) is caught,
  recorded as an error row for that headline, and the run continues
  with the remaining headlines rather than aborting the whole batch.

## Testing

Given the small, exploratory scope (same spirit as the existing
notebook), verification is manual for this first version: run against
the bundled sample set, and against a custom `--input` file, for each
of the console/JSON/CSV output paths, and confirm the output looks
correct. No automated test suite in this version.

## Dependencies

No new dependencies beyond what's already in `requirements.txt`
(`typesafe-sdk`, `python-dotenv`). Console table and CSV writing use
the standard library (`csv` module, manual string formatting) to avoid
adding packages for a small CLI.
