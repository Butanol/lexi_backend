import json
from pathlib import Path

from ..langchain_modules.agents.text_parser_agent import parse_text_to_criteria


def test_parse_simple_clause():
    clause = "Customers should identify beneficial owners for legal persons."
    parsed = parse_text_to_criteria(clause, source="test")
    assert isinstance(parsed, dict)
    assert "criteria" in parsed
