# Jev Explore

A small Python notebook project for exploring the TypeSafe SDK and using it to analyze support-style customer messages. This is designed to demonstrate the usage of Jev, TypeSafe's first System One classifier model.

System One models are a class of AI models built to make fast, structured decisions that software can use directly. A System One model evaluates a state and returns typed answers and probabilities.

Like an LLM, a System One model understands natural-language input. It returns typed decisions and probabilities rather than generated text.

## Overview

This project demonstrates how to:

- load environment variables from a `.env` file
- initialize the TypeSafe client
- classify a customer message by department
- score the message's frustration level
- estimate urgency using the TypeSafe model

The notebook uses a sample support ticket and returns structured analysis values such as the likely team to route the issue to and the emotional urgency of the message.

## Project Structure

- `jev-explore.ipynb` — notebook with the main TypeSafe SDK example
- `requirements.txt` — Python dependencies

## Requirements

- Python 3.9+
- Jupyter Notebook or VS Code with notebook support
- A valid TypeSafe API key

## Setup

1. Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root with your API key:

```env
TYPESAFE_API_KEY=your_api_key_here
```

## Running the Notebook

Open `jev-explore.ipynb` in Jupyter or VS Code and run the cells in order.

The example sends a support message to the TypeSafe client and prints outputs similar to:

```python
print(response.answers["department"].choice)
print(response.answers["frustration"].score)
print(response.answers["is_urgent"].noul)
```

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

The sensationalism score ranges from 0 (straightforward and factual) to 2
(highly sensational, clickbait framing).

## Dependencies

The project currently uses:

- `ipykernel`
- `python-dotenv`
- `typesafe-sdk`

## Notes

- The notebook expects the environment variable `TYPESAFE_API_KEY` to be present.
- If the API key is missing or invalid, the TypeSafe client requests will fail.
- The example is intended as a lightweight exploration and can be extended for production support triage workflows.
