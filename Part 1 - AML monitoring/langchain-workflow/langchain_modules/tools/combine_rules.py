import os
import json
import difflib
from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()

# ----------------------------
# CONFIGURATION
# ----------------------------
RULES_FOLDER = "Part 1 - AML monitoring/langchain-workflow/logs/HKMA"   # folder containing your rule files
OUTPUT_FILE = "Part 1 - AML monitoring/langchain-workflow/logs/HKMA_rules.json"

# Optional: use Groq to generate a final concise summary of all obligations
USE_GROQ_SUMMARY = True
GROQ_MODEL = "openai/gpt-oss-20b"

# Ensure Groq API key exists
if "GROQ_API_KEY" not in os.environ:
    os.environ["GROQ_API_KEY"] = "YOUR_GROQ_KEY"

# ----------------------------
# STEP 1: LOAD ALL JSON FILES
# ----------------------------
def load_all_rules(folder_path):
    all_rules = []
    summaries = []
    for filename in os.listdir(folder_path):
        if filename.endswith(".json"):
            with open(os.path.join(folder_path, filename), "r") as f:
                data = json.load(f)
                summaries.append(data.get("regulationsummary") or data.get("regulation_summary"))
                all_rules.extend(data.get("actionablerules") or data.get("actionable_rules", []))
    return summaries, all_rules


# ----------------------------
# STEP 2: DEDUPLICATE / MERGE RULES
# ----------------------------
def merge_similar_rules(rules):
    merged = []
    seen = set()
    for rule in rules:
        if rule["ruleid"] in seen:
            continue
        seen.add(rule["ruleid"])

        # Try to find very similar obligations (for fuzzy merge)
        matches = [r for r in rules if r["ruleid"] not in seen and 
                   difflib.SequenceMatcher(None, r["obligation"].lower(), rule["obligation"].lower()).ratio() > 0.85]

        for m in matches:
            # merge lists (union of risk signals, docs, etc.)
            rule["risksignalstomonitor"] = list(set(rule["risksignalstomonitor"] + m["risksignalstomonitor"]))
            rule["requireddocumentsorcontrols"] = list(set(rule["requireddocumentsorcontrols"] + m["requireddocumentsorcontrols"]))
            seen.add(m["ruleid"])

        merged.append(rule)
    return merged


# ----------------------------
# STEP 3: OPTIONALLY USE GROQ TO SUMMARIZE THE REGULATION
# ----------------------------
def generate_summary_with_groq(summaries, merged_rules):
    combined_text = "\n".join(summaries)
    prompt = f"""
You are a senior AML/CFT compliance officer.

Summarize the following combined regulations into a concise 3–6 sentence overview that captures their essence, without losing accuracy:

---
{combined_text}
---
"""
    validation_llm = ChatGroq(model=GROQ_MODEL, temperature=0)
    response = validation_llm.invoke([prompt])
    summary = response.content.strip() if hasattr(response, "content") else str(response)
    return summary


# ----------------------------
# MAIN WORKFLOW
# ----------------------------
if __name__ == "__main__":
    print("Loading and merging rule files...")
    all_summaries, all_rules = load_all_rules(RULES_FOLDER)
    merged_rules = merge_similar_rules(all_rules)

    if USE_GROQ_SUMMARY:
        print("Generating consolidated regulation summary using Groq...")
        final_summary = generate_summary_with_groq(all_summaries, merged_rules)
    else:
        # fallback: simple merge of all summaries
        final_summary = " ".join(all_summaries)[:2000]

    final_output = {
        "regulation_summary": final_summary,
        "actionable_rules": merged_rules
    }

    # ----------------------------
    # STEP 4: SAVE OUTPUT
    # ----------------------------
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w") as out:
        json.dump(final_output, out, indent=4, ensure_ascii=False)

    print(f"✅ Merged and summarized rules saved to {OUTPUT_FILE}")
    print(f"Total rules merged: {len(all_rules)} → {len(merged_rules)} unique")
