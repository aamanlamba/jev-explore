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

    if args.output:
        output_parent = Path(args.output).parent
        if not output_parent.is_dir():
            print(
                f"Error: output directory does not exist: {output_parent}",
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

    failed = sum(1 for result in results if result.error is not None)
    if failed > 0:
        print(f"{failed} of {len(results)} headlines failed", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
