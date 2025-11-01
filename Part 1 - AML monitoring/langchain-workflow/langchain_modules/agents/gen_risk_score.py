import os
import pandas as pd
import json
from datetime import datetime
from langchain_groq import ChatGroq
from typing import Dict
import time
from dotenv import load_dotenv
load_dotenv()

# ----------------------------
# 1. MODEL INITIALIZATION
# ----------------------------
validation_llm = ChatGroq(
    model="openai/gpt-oss-20b",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2
)

# ----------------------------
# 2. HELPER FUNCTIONS
# ----------------------------

def load_actionable_rules(json_file_path: str) -> Dict:
    """Load actionable rules from JSON file."""
    with open(json_file_path, 'r') as f:
        return json.load(f)

def load_data(csv_file_path: str) -> pd.DataFrame:
    """Load dataset from CSV."""
    return pd.read_csv(csv_file_path)

def create_risk_scoring_prompt(transaction: Dict, rules: Dict) -> str:
    """Create a regulator-specific AML/CFT risk assessment prompt."""
    regulator = transaction.get('regulator', 'Unknown Regulator')
    jurisdiction = transaction.get('booking_jurisdiction', 'Unknown Jurisdiction')
    
    prompt = f"""You are an expert AML (Anti-Money Laundering) risk assessment system.
Evaluate the following financial transaction against the regulatory framework for {regulator} in {jurisdiction}.

REGULATORY RULES FOR {regulator}:
{json.dumps(rules, indent=2)}

TRANSACTION TO EVALUATE:
{json.dumps(transaction, indent=2)}

TASK:
Assess the risk score (0-100) for this transaction based on how close it comes to violating the regulatory rules provided above.

SCORING GUIDELINES:
- 0-25: Very Low Risk — Fully compliant, <50% threshold use
- 26-45: Low Risk — Minor documentation or 50–70% threshold
- 46-65: Medium Risk — 70–85% threshold or some minor gaps
- 66-85: High Risk — 85–95% threshold, key docs missing
- 86-100: Very High Risk — Rule violations, multiple red flags

OUTPUT (JSON only):
{{
  "risk_score": <integer 0-100>,
  "risk_reasoning": "Detailed explanation citing rule IDs, % thresholds, missing docs, or red flags."
}}
"""
    return prompt

def parse_risk_response(response_text: str, transaction_id: str) -> dict:
    """Extract risk score and reasoning from model response safely."""
    try:
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        if json_start == -1 or json_end == 0:
            return {'risk_score': 50, 'risk_reasoning': f"No valid JSON. Raw: {response_text[:300]}"}
        
        parsed = json.loads(response_text[json_start:json_end])
        risk_score = int(parsed.get('risk_score', 50))
        reasoning = parsed.get('risk_reasoning', 'No reasoning provided')
        return {'risk_score': risk_score, 'risk_reasoning': reasoning}
    except Exception as e:
        return {'risk_score': 50, 'risk_reasoning': f"Parse error: {str(e)} | Raw: {response_text[:300]}"}

def invoke_llm(prompt: str, max_retries: int = 3) -> str:
    """Invoke Groq LLM robustly with retries."""
    for attempt in range(max_retries):
        try:
            response = validation_llm.invoke(prompt)
            return getattr(response, "content", str(response))
        except Exception as e:
            wait = 2 ** attempt
            print(f"⚠ LLM error ({attempt+1}/{max_retries}): {str(e)}. Retrying in {wait}s")
            time.sleep(wait)
    return None

def evaluate_transaction(transaction: Dict, regulator_rules: Dict) -> Dict:
    """Evaluate one transaction against the selected regulator's rules."""
    prompt = create_risk_scoring_prompt(transaction, regulator_rules)
    response_text = invoke_llm(prompt)
    transaction_id = transaction.get('transaction_id', 'unknown')
    
    if response_text:
        return parse_risk_response(response_text, transaction_id)
    else:
        return {'risk_score': 50, 'risk_reasoning': 'LLM failed to respond'}

# ----------------------------
# 3. MAIN MULTI-REGULATOR PROCESS
# ----------------------------
def process_transactions_multi(csv_file_path: str,
                               mas_rules_path: str,
                               finma_rules_path: str,
                               hkma_rules_path: str,
                               output_file_path: str):
    """
    Process transactions with regulator-specific rule sets.
    Each transaction uses rules based on its 'regulator' column.
    """
    print("="*80)
    print("AML RISK SCORING SYSTEM (Multi-Regulator Mode)")
    print("="*80)

    # Load rules once
    rules_map = {
        "MAS": load_actionable_rules(mas_rules_path),
        "FINMA": load_actionable_rules(finma_rules_path),
        "HKMA/SFC": load_actionable_rules(hkma_rules_path)
    }

    # Load dataset
    df = load_data(csv_file_path)
    print(f"✓ Loaded {len(df)} transactions from {csv_file_path}")
    print(f"✓ Loaded rule sets for: {', '.join(rules_map.keys())}")

    # Prepare outputs
    risk_scores, risk_reasonings = [], []
    total_transactions = len(df)

    # Iterate through transactions
    for idx, row in df.iterrows():
        transaction = row.to_dict()

        # Clean up NaNs and timestamps
        for key, val in transaction.items():
            if pd.isna(val):
                transaction[key] = None
            elif isinstance(val, (pd.Timestamp, datetime)):
                transaction[key] = str(val)

        regulator = str(transaction.get("regulator", "")).strip().upper()

        # Pick appropriate ruleset
        regulator_rules = rules_map.get(regulator)
        if not regulator_rules:
            print(f"[{idx+1}/{total_transactions}] No rules found for regulator '{regulator}' → Defaulting to MAS")
            regulator_rules = rules_map["MAS"]

        print(f"\n[{idx+1}/{total_transactions}] Transaction regulator: {regulator}")
        risk_assessment = evaluate_transaction(transaction, regulator_rules)

        risk_scores.append(risk_assessment["risk_score"])
        risk_reasonings.append(risk_assessment["risk_reasoning"])

        # Print preview
        score = risk_assessment["risk_score"]
        print(f"    Risk Score: {score}")
        if score >= 41:
            print(f"    Reason: {risk_assessment['risk_reasoning'][:100]}...")

        # Gentle pacing to avoid throttling
        if (idx + 1) % 10 == 0:
            time.sleep(3)
        else:
            time.sleep(1)

    # Add results
    df["risk_score"] = risk_scores
    df["risk_reasoning"] = risk_reasonings

    df.to_csv(output_file_path, index=False)
    print(f"\n✓ Results saved to {output_file_path}")
    print(f"✓ Evaluated using MAS, FINMA, HKMA/SFC frameworks as applicable.")

    return df

# ----------------------------
# 4. EXAMPLE USAGE
# ----------------------------
if __name__ == "__main__":
    csv_path = "Part 1 - AML monitoring/langchain-workflow/langchain_modules/data/transactions_mock_1000_for_participants.csv"
    mas_rules = "Part 1 - AML monitoring/langchain-workflow/logs/MAS_rules.json"
    finma_rules = "Part 1 - AML monitoring/langchain-workflow/logs/FINMA_rules.json"
    hkma_rules = "Part 1 - AML monitoring/langchain-workflow/logs/HKMA_rules.json"
    output_path = "Part 1 - AML monitoring/langchain-workflow/langchain_modules/data/transactions.csv"

    result_df = process_transactions_multi(csv_path, mas_rules, finma_rules, hkma_rules, output_path)
