# LangChain Workflow (AML monitoring)

This folder contains a LangChain-based workflow prototype for ingesting regulatory circulars (e.g. MAS), extracting actionable monitoring criteria, and applying a lightweight rule-based AML scoring to transaction data.

Layout:
- `config/` - configuration for models and paths
- `data/raw` - raw ingested documents (PDFs, HTML saved files)
- `data/processed` - text files and parsed criteria
- `notebooks/` - demo and debugging notebooks
- `scripts/` - helper scripts to preprocess data and run the workflow
- `langchain_modules/` - chains, agents, tools, prompts, and LLM clients
- `tests/` - pytest unit tests

See `scripts/run_workflow.py` for a simple example of running the parser over processed text files.
