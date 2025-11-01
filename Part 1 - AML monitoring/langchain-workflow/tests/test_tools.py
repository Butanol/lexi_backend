import pandas as pd

from ..langchain_modules.tools.scoring_tool import score_transactions


def test_scoring_no_criteria():
    df = pd.DataFrame([{"id": 1, "description": "payment"}])
    scored = score_transactions([], df)
    assert "aml_risk_score" in scored.columns
    assert scored.iloc[0]["aml_risk_score"] == 0
