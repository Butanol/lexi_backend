"""Generate output reports from parsed criteria and a sample transactions CSV.

This script demonstrates applying the scoring tool to a CSV of transactions.
"""
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"

from ..langchain_modules.tools.scoring_tool import score_transactions, load_criteria_from_json


def main(sample_csv: str = None):
    if sample_csv is None:
        # build tiny sample
        df = pd.DataFrame([
            {"id": 1, "description": "Beneficial owner missing", "counterparty_name": "Acme"},
            {"id": 2, "description": "Regular payment", "counterparty_name": "John"},
        ])
    else:
        df = pd.read_csv(sample_csv)

    crit_path = PROCESSED / "criteria.json"
    if crit_path.exists():
        criteria = load_criteria_from_json(str(crit_path))
    else:
        criteria = []

    scored = score_transactions(criteria, df)
    print(scored)


if __name__ == "__main__":
    main()
