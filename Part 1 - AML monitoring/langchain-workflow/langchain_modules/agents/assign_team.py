import os
import json
from langchain_groq import ChatGroq

# Ensure the GROQ API key is set
if "GROQ_API_KEY" not in os.environ:
    os.environ["GROQ_API_KEY"] = ""

# Set up the LLM model for Groq
validation_llm = ChatGroq(
    model="openai/gpt-oss-20b",
    temperature=0,
    max_tokens=None,  # Increase max tokens to allow for larger responses
    timeout=None,
    max_retries=2
)

def create_triage_prompt(transaction: dict) -> str:
    """
    Generate a prompt for the LLM to assign a transaction to Front Office or Legal & Compliance.
    """
    prompt = f"""
You are an AML compliance expert.

A new transaction has been flagged for review. Here are its details:
{json.dumps(transaction, indent=2)}

TASK:
- Assign the transaction to one of the two teams:
  1. Front Office (routine review, low risk)
  2. Legal & Compliance (high risk, requires compliance intervention)

- Provide a confidence score (0-100) for your recommendation.
- Provide a short reasoning citing potential risk indicators, missing documentation, or red flags.

OUTPUT (JSON only):
{{
  "assigned_team": "<Front Office | Legal & Compliance>",
  "confidence_score": <integer 0-100>,
  "reasoning": "Short explanation of why this transaction was assigned"
}}
"""
    return prompt


def triage_transaction(transaction: dict, llm_model) -> dict:
    """
    Evaluate a single transaction and assign to appropriate team.
    """
    prompt = create_triage_prompt(transaction)
    response_text = validation_llm.invoke(prompt)  # reuse your existing robust LLM call

    try:
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        parsed = json.loads(response_text[json_start:json_end])
        return {
            "assigned_team": parsed.get("assigned_team", "Front Office"),
            "confidence_score": int(parsed.get("confidence_score", 50)),
            "reasoning": parsed.get("reasoning", "No reasoning provided")
        }
    except Exception as e:
        return {
            "assigned_team": "Front Office",
            "confidence_score": 50,
            "reasoning": f"Parse error: {str(e)} | Raw: {response_text[:300]}"
        }

if __name__ == "__main__":
    # Load one row as a dict
    df = pd.read_csv(csv_path)
    transaction = df.iloc[0].to_dict()

    result = triage_transaction(transaction, validation_llm)

    print("✅ Triage Result")
    print(f"Assigned Team: {result['assigned_team']}")
    print(f"Confidence Score: {result['confidence_score']}")
    print(f"Reasoning: {result['reasoning']}")
