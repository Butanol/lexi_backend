"""LangChain-based parser that converts regulatory text into structured monitoring criteria.

Usage notes / assumptions:
- Expects an OpenAI-compatible API key in the environment variable OPENAI_API_KEY.
- Uses a prompt-template to instruct the model to return JSON only following the monitoring schema.
- This is intentionally conservative: it produces a JSON object containing a list of criteria. Each
  criterion contains fields useful for downstream scoring.
"""
import os
import json
from typing import List, Dict, Any

from langchain import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain


PROMPT = """
You are an assistant that converts regulatory clauses into structured monitoring criteria for
anti-money-laundering (AML) monitoring systems. For each clause provided, extract actionable
criteria as JSON. Output must be valid JSON and follow this schema:

{
  "criteria": [
    {
      "criterion_id": "string (stable id)",
      "title": "short title",
      "description": "short human-readable interpretation",
      "source": "source url or identifier",
      "triggers": [
         {"type": "keyword|behaviour|threshold|pattern", "value": "string"}
      ],
      "severity": "low|medium|high",
      "suggested_features": ["transaction_amount","counterparty_country","beneficial_owner_name", ...],
      "example_detection": "pseudo-SQL or description of detection logic"
    }
  ]
}

Produce concise and precise fields. If you cannot extract a particular field, return a reasonable
default (e.g. empty list or "medium").

EXAMPLES:

Input: "Customers should identify and verify beneficial owners where the customer is a legal person."

Output (JSON only):
{"criteria":[{"criterion_id":"MAS-EX-001","title":"Verify Beneficial Ownership for Legal Entities","description":"Require identification and verification of beneficial owners when the customer is a legal person.","source":"INPUT","triggers":[{"type":"keyword","value":"beneficial owner"},{"type":"behaviour","value":"customer_type == 'legal_entity'"}],"severity":"high","suggested_features":["customer_type","beneficial_owner_list","kyc_verification_status"],"example_detection":"SELECT * FROM transactions WHERE customer_type='legal_entity' AND (beneficial_owner_list IS NULL OR kyc_verification_status!='verified')"}]}

Now convert the following CLAUSE to JSON (only output JSON). Clause:
"""


def parse_text_to_criteria(raw_text: str, source: str = "INPUT", llm_api_key: str = None) -> Dict[str, Any]:
    """Call the LLM to convert raw regulatory text into structured criteria.

    Returns the parsed dictionary (criteria list). Raises ValueError if the model response cannot
    be decoded as JSON.
    """
    if llm_api_key is None:
        llm_api_key = os.environ.get("OPENAI_API_KEY")
    if not llm_api_key:
        raise RuntimeError("OPENAI_API_KEY is required in environment or llm_api_key argument")

    # Use a lightweight OpenAI model via LangChain. Adjust model name as needed.
    llm = OpenAI(openai_api_key=llm_api_key, temperature=0)

    # Build prompt with the clause and source marker
    prompt = PromptTemplate(
        input_variables=["clause", "source"],
        template=PROMPT + "\n\nClause:\n{clause}\n\nSource:{source}\n",
    )

    chain = LLMChain(llm=llm, prompt=prompt)
    response = chain.run({"clause": raw_text.strip(), "source": source})

    # Expect response to be JSON string
    try:
        parsed = json.loads(response)
    except Exception:
        # Try to recover by finding first { ... } block
        import re

        m = re.search(r"\{[\s\S]*\}\s*$", response)
        if m:
            parsed = json.loads(m.group(0))
        else:
            raise ValueError("Could not parse JSON from model response:\n" + response)

    # Normalize: ensure top-level 'criteria' exists
    if "criteria" not in parsed:
        parsed = {"criteria": []}

    # Attach source to each criterion if missing
    for c in parsed.get("criteria", []):
        if "source" not in c:
            c["source"] = source

    return parsed


if __name__ == "__main__":
    # quick demo when run directly
    demo_clause = (
        "Banks must identify and verify beneficial owners for customers that are legal persons;"
        " enhanced CDD is required for politically exposed persons (PEPs) and high-risk jurisdictions."
    )
    out = parse_text_to_criteria(demo_clause, source="MAS-demo")
    print(json.dumps(out, indent=2))
