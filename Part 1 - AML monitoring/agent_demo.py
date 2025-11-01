"""Demo script showing end-to-end: parse a clause with LangChain agent then score a tiny transactions sample.

Run:
  setx OPENAI_API_KEY "your_key_here"
  python "Part 1 - AML monitoring\agent_demo.py"

This script is intentionally minimal and intended as a starting point.
"""
import json
from pathlib import Path

from langchain_agent import parse_text_to_criteria
from risk_scoring import score_transactions
import pandas as pd


def main():
    clause = (
        "Financial institutions must identify and verify beneficial owners for customers that are legal persons."
        " Enhanced due diligence is required for politically exposed persons and when dealing with high-risk jurisdictions."
    )

    parsed = parse_text_to_criteria(clause, source="MAS-demo")
    print("Parsed criteria:")
    print(json.dumps(parsed, indent=2))

    # Build a tiny transactions dataset
    tx = pd.DataFrame(
        [
            {"id": 1, "description": "Wire transfer - beneficial owner unknown", "counterparty_name": "Acme Pte Ltd"},
            {"id": 2, "description": "Invoice payment", "counterparty_name": "Global Supplies"},
            {"id": 3, "description": "Account opening - politically exposed person", "counterparty_name": "Mr. X (PEP)"},
        ]
    )

    scored = score_transactions(parsed.get("criteria", []), tx)
    print("Scored transactions:")
    print(scored.to_string(index=False))


if __name__ == "__main__":
    main()
