"""Run the LangChain workflow end-to-end:
- load processed docs
- call the parser chain to extract criteria
- save criteria to data/processed/criteria.json
"""
import json
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
PROCESSED.mkdir(parents=True, exist_ok=True)

# Import the parser agent (we keep a compact implementation under langchain_modules)
from ..langchain_modules.agents.text_parser_agent import parse_text_to_criteria


def run_all():
    out = {"criteria": []}
    for p in PROCESSED.glob("*.txt"):
        raw = p.read_text(encoding='utf-8')
        parsed = parse_text_to_criteria(raw, source=str(p.name))
        out["criteria"].extend(parsed.get("criteria", []))

    out_path = PROCESSED / "criteria.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote criteria to {out_path}")


if __name__ == "__main__":
    run_all()
