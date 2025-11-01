import os
from langchain import OpenAI


def get_llm(api_key: str = None, model: str = None, temperature: float = 0.0):
    if api_key is None:
        api_key = os.environ.get("OPENAI_API_KEY")
    if api_key is None:
        raise RuntimeError("OPENAI_API_KEY required")
    return OpenAI(openai_api_key=api_key, temperature=temperature)
