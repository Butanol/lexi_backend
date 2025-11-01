"""Agent to parse regulatory clause text into structured monitoring criteria using a LangChain LLM.

This file is a slightly refactored copy of the original langchain_agent prototype so the
new project layout can import it from a predictable path.
"""
import os
import json
from typing import Dict, Any

from langchain import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain


PROMPT = """
You are an assistant that converts regulatory clauses into structured monitoring criteria for
anti-money-laundering (AML) monitoring systems. For each clause provided, extract actionable
criteria as JSON. Output must be valid JSON and follow this schema:

{...}  # prompt shortened in file for brevity
"""


def parse_text_to_criteria(raw_text: str, source: str = "INPUT", llm_api_key: str = None) -> Dict[str, Any]:
    if llm_api_key is None:
        llm_api_key = os.environ.get("OPENAI_API_KEY")
    if not llm_api_key:
        raise RuntimeError("OPENAI_API_KEY is required in environment or llm_api_key argument")

    llm = OpenAI(openai_api_key=llm_api_key, temperature=0)
    prompt = PromptTemplate(input_variables=["clause", "source"], template=PROMPT + "\n\nClause:\n{clause}\n\nSource:{source}\n")
    chain = LLMChain(llm=llm, prompt=prompt)
    response = chain.run({"clause": raw_text.strip(), "source": source})

    try:
        parsed = json.loads(response)
    except Exception:
        import re
        m = re.search(r"\{[\s\S]*\}\s*$", response)
        if m:
            parsed = json.loads(m.group(0))
        else:
            raise ValueError("Could not parse JSON from model response:\n" + response)

    if "criteria" not in parsed:
        parsed = {"criteria": []}

    for c in parsed.get("criteria", []):
        if "source" not in c:
            c["source"] = source

    return parsed


if __name__ == "__main__":
    demo_clause = (
        "Financial institutions must identify and verify beneficial owners for customers that are legal persons;"
        " enhanced CDD is required for politically exposed persons (PEPs) and high-risk jurisdictions."
    )
    out = parse_text_to_criteria(demo_clause, source="MAS-demo")
    print(json.dumps(out, indent=2))
