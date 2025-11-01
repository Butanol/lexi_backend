"""Scoring tool: a relocated copy of the prototype risk_scoring module.
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
            if t.get("value"):
                kws.append(str(t.get("value")).lower())
    return [k for k in kws if k]


def score_transactions(criteria_list: List[Dict[str, Any]], df: pd.DataFrame, fields: List[str] = None) -> pd.DataFrame:
    if fields is None:
        fields = ["description", "memo", "counterparty_name", "counterparty_country", "beneficiary"]

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

        pattern = re.compile(r"\b(?:" + "|".join(re.escape(k) for k in kws) + r")\b", flags=re.IGNORECASE)

        for idx, text in df["_search_text"].items():
            if pattern.search(text):
                df.at[idx, "aml_risk_score"] += weight
                df.at[idx, "matched_criteria"].append(crit.get("criterion_id", crit.get("title", "unknown")))

    df.drop(columns=["_search_text"], inplace=True)
    return df


def load_criteria_from_json(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        obj = json.load(f)
    return obj.get("criteria", [])
