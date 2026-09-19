# TODO

## Ingestion pipeline: classify headlines from websites and documents

Extend the headline classifier so headlines don't have to be pasted by hand —
pull them from a website or a document and feed them straight into the
existing `evaluate_headlines()` pipeline.

**High-level design:**

- **Sources**
  - Website: fetch a URL (news homepage, RSS/Atom feed, or section page) and
    extract headline-like text — likely `<h1>`/`<h2>`/article-title elements
    for HTML pages, or `<title>`/`<summary>` for RSS.
  - Documents: accept uploaded files (`.txt`, `.pdf`, maybe `.docx`) and
    extract one headline per line, or one per detected heading/title.
- **Extraction layer**: a new module (e.g. `ingest.py`) with one function per
  source type, each returning `list[str]` of raw headline candidates — same
  shape `evaluate_headlines()` already expects, so no changes needed
  downstream.
- **Dedup / cleanup**: strip whitespace, drop empties and near-duplicates
  before evaluation, to avoid wasting API calls on repeated headlines.
- **Reuse**: feeds directly into `evaluator.evaluate_headlines()` and
  `formatter.py`'s existing table/JSON/CSV output — no changes to the
  classification core.
- **Entry points**: likely both a CLI flag (`headline_cli.py --url ...` /
  `--file ...`) and a Streamlit input option (URL box / file uploader)
  alongside the existing text area.
- **Open questions to resolve before building** (needs a proper brainstorm):
  - Rate limiting / how many headlines per fetch before hitting the TypeSafe
    API too hard.
  - Which document formats are actually needed (just PDF/txt, or more).
  - How to detect "this looks like a headline" vs. body text on an arbitrary
    web page — fixed CSS selectors vs. heuristic (e.g. short text in heading
    tags) vs. an LLM extraction pass.
  - Error handling for unreachable URLs / unparseable documents.
