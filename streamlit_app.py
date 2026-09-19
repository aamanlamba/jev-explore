"""Streamlit frontend for evaluating news headlines with TypeSafe."""
from __future__ import annotations

import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from typesafe_sdk import TypeSafeClient

from evaluator import evaluate_headlines
from formatter import results_to_csv, results_to_json

SAMPLE_HEADLINES_FILE = Path(__file__).parent / "sample_headlines.txt"

st.set_page_config(page_title="Headline Classifier", layout="wide")
st.title("Headline Classifier")
st.caption("Evaluate news headlines for category, sentiment, sensationalism, and breaking-news signal.")

sample_text = SAMPLE_HEADLINES_FILE.read_text() if SAMPLE_HEADLINES_FILE.is_file() else ""
headlines_text = st.text_area(
    "Headlines (one per line)",
    value=sample_text,
    height=250,
)

if st.button("Evaluate", type="primary"):
    headlines = [line.strip() for line in headlines_text.splitlines() if line.strip()]

    load_dotenv()
    if not os.getenv("TYPESAFE_API_KEY"):
        st.error("TYPESAFE_API_KEY is not set. Add it to your .env file or environment.")
    elif not headlines:
        st.warning("Enter at least one headline.")
    else:
        with st.spinner(f"Evaluating {len(headlines)} headline(s)..."):
            client = TypeSafeClient()
            results = evaluate_headlines(client, headlines)
        st.session_state["results"] = results

results = st.session_state.get("results")
if results:
    table_rows = []
    for result in results:
        if result.error:
            table_rows.append({"Headline": result.headline, "Error": result.error})
            continue
        table_rows.append(
            {
                "Headline": result.headline,
                "Categories": ", ".join(result.matched_categories()) or "-",
                "Sentiment": result.sentiment,
                "Sensational. (0-2)": round(result.sensationalism_score, 2),
                "Breaking": "yes" if result.is_breaking() else "no",
            }
        )
    st.dataframe(table_rows, width="stretch")

    failed = sum(1 for result in results if result.error is not None)
    if failed:
        st.warning(f"{failed} of {len(results)} headlines failed.")

    col1, col2 = st.columns(2)
    col1.download_button(
        "Download JSON",
        data=results_to_json(results),
        file_name="headline_results.json",
        mime="application/json",
    )
    col2.download_button(
        "Download CSV",
        data=results_to_csv(results),
        file_name="headline_results.csv",
        mime="text/csv",
    )
