import os
import json
import importlib.util
from pathlib import Path
# reuse the PDF extraction helper from the preprocess pipeline instead of
# using PyMuPDF directly
from langchain_groq import ChatGroq
import re


# Define the prompt for the model to output only the JSON
PROMPT = """You are a senior AML/CFT Legal & Compliance Officer assisting a bank in interpreting regulatory requirements.

Your task is to convert regulatory or policy text into clear, structured, actionable compliance rules that can be used to evaluate and mitigate financial crime risk.

When summarizing, you MUST:
1. Preserve the regulatory meaning accurately.
2. Use plain language suitable for compliance analysts.
3. Convert obligations into *specific, testable rules* (i.e., something that can be monitored or audited).
4. Identify the *risk indicators* that the rule is intended to mitigate.
5. Highlight where Enhanced Due Diligence (EDD) is required.

Your output must **ONLY** follow this JSON schema exactly, without any additional text or commentary:

{
  "regulation_summary": "<3-6 sentence overview>",
  "actionable_rules": [
    {
      "rule_id": "<Unique short ID, e.g. MAS-CDD-01>",
      "obligation": "<What the institution must DO>",
      "who_it_applies_to": "<Customer type, product type, geography, etc.>",
      "risk_signals_to_monitor": [
        "<Behavior, profile, transaction pattern that raises risk>",
        "<Another risk signal>"
      ],
      "required_documents_or_controls": [
        "<Documents to collect, checks to run, approvals needed>"
      ],
      "requires_edd": "<Yes/No and why>"
    }
  ]
}

Below is the regulatory text to analyze:"""

# Set up the LLM model for Groq
validation_llm = ChatGroq(
    model="openai/gpt-oss-20b",
    temperature=0,
    max_tokens=None,  # Increase max tokens to allow for larger responses
    timeout=None,
    max_retries=2
)

def extract_pdf_text_via_preprocess(pdf_path):
    """Load the preprocess_data module and call its process_pdf() helper.

    This avoids duplicating extraction logic and ensures consistent text
    output across the project.
    """
    try:
        # Locate the preprocess_data.py file relative to this script. The
        # folder structure is: langchain-workflow/langchain_modules/agents/...
        # so parents[2] is the langchain-workflow directory.
        module_path = Path(__file__).resolve().parents[2] / "scripts" / "preprocess_data.py"
        spec = importlib.util.spec_from_file_location("preprocess_data", str(module_path))
        preprocess = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(preprocess)
        # Call the process_pdf function from the preprocess module
        return preprocess.process_pdf(Path(pdf_path))
    except Exception as e:
        print(f"Error extracting text via preprocess tool: {e}")
        return ""

# Extract text from the PDF
pdf_path = Path("./Part 1 - AML monitoring/langchain-workflow/logs/temp/HKMA_trimmed9.pdf")
pdf_text = extract_pdf_text_via_preprocess(pdf_path)

# Combine the PDF text with your custom prompt (you can adjust the prompt if needed)
messages = [PROMPT + "\n\n" + pdf_text]  # Add PDF content to prompt

# Send the request to the model
response = validation_llm.invoke(messages)

# Debug the response structure
print("Response type:", type(response))
print("Response content length:", len(response.content))

# Get the content of the response
response_content = response.content.strip()

# Debug: Ensure we received content from the model
if not response_content:
    print("Error: Empty response from the model.")
else:
    print(f"Response received (first 500 chars): {response_content[:500]}")  # Print the first 500 characters

# Clean the response if there are any unwanted characters
cleaned_response = re.sub(r'[^{}:\[\],\"0-9a-zA-Z\s-]', '', response_content)

# Debug: Print the cleaned response to check if it looks like valid JSON
print(f"Cleaned response (first 500 chars): {cleaned_response[:500]}")

# Check for potential truncation by verifying if it ends properly
if cleaned_response.strip().endswith('},'):
    cleaned_response = cleaned_response.strip()[:-1] + '}'

# Check if the cleaned response starts with '{' and ends with '}' to ensure it's valid JSON
if cleaned_response.startswith("{") and cleaned_response.endswith("}"):
    try:
        # Try parsing the content directly as JSON
        parsed_response = json.loads(cleaned_response)
        print("Parsed JSON response:")
        print(json.dumps(parsed_response, indent=4))  # Pretty print the parsed JSON
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON response: {e}")
        # Output the raw response for debugging
        print("Raw response (for debugging):", response_content)
        parsed_response = {}
else:
    print("Error: Response is not valid JSON. It doesn't start with '{' or end with '}'.")
    parsed_response = {}

# Ensure file path is correct and that we have permission to write to it
output_file = "Part 1 - AML monitoring/langchain-workflow/logs/curr_HKMA_rules9.json"

# Check if the directory exists before saving
output_dir = os.path.dirname(output_file)
if not os.path.exists(output_dir):
    print(f"Error: Directory {output_dir} does not exist.")
else:
    try:
        # Save JSON response only if it's valid
        if parsed_response:
            with open(output_file, "w") as json_file:
                json.dump(parsed_response, json_file, indent=4)
            print(f"Response successfully saved to {output_file}")
        else:
            print("Error: Parsed response is empty or invalid. Not saving to file.")
    except Exception as e:
        print(f"Error saving JSON to file: {e}")
