
Part 1 — AML monitoring
========================

This folder contains tooling and prototypes for ingesting regulatory circulars
and converting them into monitoring criteria for AML risk scoring. See the
`langchain-workflow/` subfolder for the LangChain-based agent, downloaders,
and preprocessing scripts.

Environment variables
---------------------

The preprocessing pipeline can optionally translate extracted text using the
JigsawStack Text Translate API. The following environment variables control
that behavior:

- `JIGSAWSTACK_API_KEY` (required to enable translation)
	- A bearer API key string for the JigsawStack Translate service. If this
		variable is not set the preprocessing script will skip translation and
		save the raw extracted text.

- `JIGSAWSTACK_TRANSLATE_URL` (optional, defaults to the public endpoint)
	- The full HTTP(S) URL of the translate endpoint to use. Default:
		`https://api.jigsawstack.com/v1/translate`.
	- Use this to point the pipeline at a private deployment, staging instance,
		or a proxy that enforces additional security controls.

Quick run notes
---------------

- Place raw PDFs into `langchain-workflow/data/raw/` and run the preprocessing
	script to extract (and optionally translate) text into
	`langchain-workflow/data/processed/`.
- Ensure `JIGSAWSTACK_API_KEY` is present in your environment if you want
	translations to occur. The script handles missing keys gracefully.

