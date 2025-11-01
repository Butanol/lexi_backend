"""Simple AML risk scoring engine that maps structured criteria to transaction-level risk scores.

This is a lightweight, rule-based scoring prototype intended to demonstrate how parsed
monitoring criteria (produced by the LangChain agent) can be applied to a transaction dataset.

Design / limitations:
- Criteria triggers are interpreted conservatively: we look for keyword triggers in textual
  transaction fields and apply severity weights.
- This is a prototype. Real production scoring requires feature engineering, robust matching,
  fuzzy name matching, entity resolution, and tests.
"""
import json
import re
from typing import List, Dict, Any

import pandas as pd

SEVERITY_WEIGHTS = {"low": 1, "medium": 3, "high": 5}


def _keywords_from_triggers(triggers: List[Dict[str, str]]) -> List[str]:
    kws = []
    for t in triggers:
        if t.get("type") == "keyword":
            kws.append(t.get("value", "").lower())
        else:
            # also index value for other trigger types
            if t.get("value"):
                kws.append(str(t.get("value")).lower())
    return [k for k in kws if k]


def score_transactions(criteria_list: List[Dict[str, Any]], df: pd.DataFrame, fields: List[str] = None) -> pd.DataFrame:
    """Score each transaction in df and return a DataFrame with an added `aml_risk_score` column.

    - criteria_list: list of criteria (each as dict from the LangChain output)
    - df: transactions dataframe
    - fields: list of fields to search for trigger keywords; if None, default set is used.
    """
    if fields is None:
        # common transaction fields
        fields = ["description", "memo", "counterparty_name", "counterparty_country", "beneficiary"]

    # Prepare a combined text column to search against
    def _row_text(r):
        parts = []
        for f in fields:
            v = r.get(f, "")
            if pd.isna(v):
                v = ""
            parts.append(str(v))
        return " ".join(parts).lower()

    df = df.copy()
    df["_search_text"] = df.apply(_row_text, axis=1)
    df["aml_risk_score"] = 0
    df["matched_criteria"] = [[] for _ in range(len(df))]

    for crit in criteria_list:
        severity = crit.get("severity", "medium").lower()
        weight = SEVERITY_WEIGHTS.get(severity, 3)
        triggers = crit.get("triggers", [])
        kws = _keywords_from_triggers(triggers)

        if not kws:
            continue

        # For each keyword, mark transactions where the keyword appears
        pattern = re.compile(r"\b(?:" + "|".join(re.escape(k) for k in kws) + r")\b", flags=re.IGNORECASE)

        for idx, text in df["_search_text"].items():
            if pattern.search(text):
                df.at[idx, "aml_risk_score"] += weight
                df.at[idx, "matched_criteria"].append(crit.get("criterion_id", crit.get("title", "unknown")))

    # clean helper column
    df.drop(columns=["_search_text"], inplace=True)
    return df


def load_criteria_from_json(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        obj = json.load(f)
    return obj.get("criteria", [])


if __name__ == "__main__":
    # quick demo
    sample_criteria = [
        {
            "criterion_id": "MAS-DEMO-001",
            "title": "Verify Beneficial Owner",
            "description": "Verify beneficial owners for legal entities.",
            "triggers": [{"type": "keyword", "value": "beneficial owner"}],
            "severity": "high",
        },
        {
            "criterion_id": "MAS-DEMO-002",
            "title": "PEP screening",
            "description": "Enhanced CDD for PEPs",
            "triggers": [{"type": "keyword", "value": "politically exposed person"}],
            "severity": "high",
        },
    ]

    sample_tx = pd.DataFrame(
        [
            {"id": 1, "description": "Payment to beneficiary - beneficial owner unknown", "counterparty_name": "ACME LTD"},
            {"id": 2, "description": "Salary payment", "counterparty_name": "John Doe"},
            {"id": 3, "description": "Onboarding for a politically exposed person", "counterparty_name": "Jane PEP"},
        ]
    )

    scored = score_transactions(sample_criteria, sample_tx)
    print(scored.to_dict(orient="records"))
