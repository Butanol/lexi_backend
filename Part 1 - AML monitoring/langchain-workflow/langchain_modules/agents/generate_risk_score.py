import os
import pandas as pd
import json
from datetime import datetime
from langchain_groq import ChatGroq
from typing import Dict
import time

# Set up the LLM model for Groq
validation_llm = ChatGroq(
    model="openai/gpt-oss-20b",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2
)

def load_actionable_rules(json_file_path: str) -> Dict:
    """Load actionable rules from JSON file."""
    with open(json_file_path, 'r') as f:
        return json.load(f)

def load_data(csv_file_path: str) -> pd.DataFrame:
    """Load dataset from CSV."""
    return pd.read_csv(csv_file_path)

def create_risk_scoring_prompt(transaction: Dict, rules: Dict) -> str:
    """
    Create a region-agnostic prompt to evaluate a transaction against rules.
    Score reflects how close the transaction is to violating the rules.
    """
    # Extract regulator info if available
    regulator = transaction.get('regulator', 'Unknown Regulator')
    jurisdiction = transaction.get('booking_jurisdiction', 'Unknown Jurisdiction')
    
    prompt = f"""You are an expert AML (Anti-Money Laundering) risk assessment system. Evaluate the following financial transaction against the provided regulatory rules for {regulator} in {jurisdiction}.

REGULATORY RULES FOR {regulator}:
{json.dumps(rules, indent=2)}

TRANSACTION TO EVALUATE:
{json.dumps(transaction, indent=2)}

TASK:
Assess the risk score (0-100) for this transaction based on how close it comes to violating the regulatory rules provided above.

SCORING GUIDELINES:
- 0-25: Very Low Risk - Transaction is far from any rule violations (<50% of thresholds)
- 26-45: Low Risk - Transaction uses 50-70% of regulatory thresholds
- 46-65: Medium Risk - Transaction uses 70-85% of thresholds OR has documentation gaps
- 66-85: High Risk - Transaction uses 85-95% of thresholds OR missing critical compliance requirements
- 86-100: Very High Risk - Transaction is near violation or violates multiple requirements


EVALUATION APPROACH:
1. Review ALL rules in the provided regulatory framework
2. Check transaction against each applicable rule's thresholds and requirements
3. Identify any missing documentation or compliance gaps
4. Consider cumulative risk from multiple factors
5. Calculate proximity to each threshold as a percentage
6. Assign higher scores for:
   - Amounts near regulatory thresholds
   - Missing required documentation (CDD, KYC, EDD, SOW)
   - High-risk customer profiles (PEPs, high-risk jurisdictions)
   - Incomplete SWIFT/wire transfer information
   - Digital asset transactions without proper disclosure
   - Any suspicious patterns or red flags

OUTPUT FORMAT (JSON only, no other text):
{{
  "risk_score": <integer 0-100>,
  "risk_reasoning": "Detailed explanation of the risk score. For scores 41+, explain SPECIFIC reasons including: which rules are at risk, exact threshold percentages, missing documentation, red flags, and suspicious indicators. Be comprehensive and specific with numbers and rule references."
}}

IMPORTANT INSTRUCTIONS:
- For Medium to Very High risk scores (41-100), provide DETAILED reasoning with specific rule references
- Include exact calculations (e.g., "Amount is 92% of threshold X")
- List ALL missing documentation and compliance gaps
- Identify ALL suspicious patterns or red flags
- Reference specific rule IDs from the regulatory framework
- Be thorough - this reasoning will be used for compliance review

Return ONLY the JSON object with risk_score and risk_reasoning fields. No additional text."""
    
    return prompt
import json
import time

def parse_risk_response(response_text: str, transaction_id: str) -> dict:
    """Parse the model's response robustly and extract risk score and reasoning."""
    try:
        # Attempt to extract the first valid JSON object
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        if json_start == -1 or json_end == 0:
            return {
                'risk_score': 50,
                'risk_reasoning': f"⚠ No JSON found. Raw response: {response_text[:500]}"
            }
        
        json_str = response_text[json_start:json_end]
        parsed = json.loads(json_str)
        
        # Normalize fields
        risk_score = parsed.get('risk_score', 50)
        # Ensure it's an integer
        try:
            risk_score = int(risk_score)
        except (TypeError, ValueError):
            risk_score = 50

        # Handle multiple possible keys for reasoning
        reasoning = parsed.get('risk_reasoning') or parsed.get('risk_reason') or parsed.get('reasoning') or parsed.get('reason') or "No reasoning provided"
        
        return {
            'risk_score': risk_score,
            'risk_reasoning': reasoning
        }

    except json.JSONDecodeError as e:
        return {
            'risk_score': 50,
            'risk_reasoning': f"⚠ JSON decode error: {str(e)}. Raw response: {response_text[:500]}"
        }
    except Exception as e:
        return {
            'risk_score': 50,
            'risk_reasoning': f"⚠ Parsing error: {str(e)}. Raw response: {response_text[:500]}"
        }

def invoke_llm(prompt: str, max_retries: int = 3) -> str:
    """Invoke LLM robustly with retry and backoff."""
    for attempt in range(max_retries):
        try:
            response = validation_llm.invoke(prompt)
            if hasattr(response, 'content'):
                return response.content
            elif isinstance(response, dict) and 'text' in response:
                return response['text']
            else:
                return str(response)
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff: 1,2,4s
                print(f"⚠ LLM error (attempt {attempt+1}/{max_retries}): {str(e)[:50]}... Retrying in {wait_time}s")
                time.sleep(wait_time)
            else:
                print(f"✗ LLM failed after {max_retries} attempts: {str(e)[:100]}")
                return None
    return None


def evaluate_transaction(transaction: Dict, rules: Dict) -> Dict:
    """
    Evaluate a single transaction against the rules and return risk assessment.
    
    Args:
        transaction: Dictionary containing transaction data
        rules: Dictionary containing regulatory rules
    
    Returns:
        Dictionary with risk_score and risk_reasoning
    """
    # Create prompt
    prompt = create_risk_scoring_prompt(transaction, rules)
    
    # Get LLM response
    response_text = invoke_llm(prompt)
    
    if response_text:
        # Parse the response
        transaction_id = transaction.get('transaction_id', 'unknown')
        risk_assessment = parse_risk_response(response_text, transaction_id)
        return risk_assessment
    else:
        # Return default assessment on LLM error
        return {
            'risk_score': 50,
            'risk_reasoning': 'LLM invocation failed - manual review required'
        }

def process_transactions(csv_file_path: str, json_file_path: str, output_file_path: str):
    """
    Process all transactions in the CSV file, evaluating each against the rules.
    Outputs original data plus risk_score and risk_reasoning columns.
    
    Args:
        csv_file_path: Path to CSV file containing transactions
        json_file_path: Path to JSON file containing regulatory rules
        output_file_path: Path to save the output CSV with risk scores
    """
    print("=" * 80)
    print("AML RISK SCORING SYSTEM")
    print("=" * 80)
    
    # Load data
    print("\n[1/3] Loading data...")
    rules = load_actionable_rules(json_file_path)
    df = load_data(csv_file_path)
    
    # Determine regulator from rules or data
    regulator_name = "Regulator"
    if isinstance(rules, dict):
        regulator_name = rules.get('regulator', 'Regulator')
        if 'regulator' in df.columns and not df['regulator'].isna().all():
            regulator_name = df['regulator'].mode()[0] if len(df['regulator'].mode()) > 0 else regulator_name
    
    print(f"    ✓ Loaded {len(df)} transactions")
    print(f"    ✓ Loaded {regulator_name} regulatory rules")
    
    # Process each transaction
    print(f"\n[2/3] Evaluating {len(df)} transactions...")
    print("-" * 80)
    
    risk_scores = []
    risk_reasonings = []
    
    total_transactions = len(df)
    
    for idx, row in df.iterrows():
        transaction = row.to_dict()
        
        # Convert any Timestamp objects to strings for JSON serialization
        for key, value in transaction.items():
            if pd.isna(value):
                transaction[key] = None
            elif isinstance(value, (pd.Timestamp, datetime)):
                transaction[key] = str(value)
        
        # Display progress
        print(f"\n[{idx + 1}/{total_transactions}] ", end="")
        if 'transaction_id' in transaction:
            print(f"{transaction['transaction_id']}")
        else:
            print(f"Row {idx}")
        
        # Evaluate transaction
        risk_assessment = evaluate_transaction(transaction, rules)
        
        # Store results
        risk_scores.append(risk_assessment['risk_score'])
        risk_reasonings.append(risk_assessment['risk_reasoning'])
        
        # Display results
        score = risk_assessment['risk_score']
        print(f"    Risk Score: {score}", end="")
        
        # Add risk level indicator
        if score <= 20:
            print(" (Very Low)")
        elif score <= 40:
            print(" (Low)")
        elif score <= 60:
            print(" (Medium)")
        elif score <= 80:
            print(" (High)")
        else:
            print(" (Very High)")
        
        # Show brief reasoning for medium+ risk
        if score >= 41:
            reasoning_preview = risk_assessment['risk_reasoning'][:80]
            print(f"    Reason: {reasoning_preview}...")
        
        # Rate limiting to prevent API throttling
        if (idx + 1) % 10 == 0:
            print(f"\n    ... Processed {idx + 1}/{total_transactions} transactions ...")
            time.sleep(3)  # Longer pause every 10 transactions
        elif (idx + 1) % 5 == 0:
            time.sleep(1.5)  # Medium pause every 5 transactions
        else:
            time.sleep(1)  # Standard delay between requests
    
    # Add new columns to dataframe
    print("\n" + "=" * 80)
    print("[3/3] Finalizing results...")
    print("=" * 80)
    
    df['risk_score'] = risk_scores
    df['risk_reasoning'] = risk_reasonings
    
    # Save results
    df.to_csv(output_file_path, index=False)
    print(f"\n✓ Results saved to: {output_file_path}")
    print(f"✓ Added 2 new columns: 'risk_score' and 'risk_reasoning'")
    
    # Print summary statistics
    print(f"\n{'=' * 80}")
    print("RISK ASSESSMENT SUMMARY")
    print("=" * 80)
    
    print(f"\nRisk Score Statistics:")
    print(f"  Mean:   {df['risk_score'].mean():.2f}")
    print(f"  Median: {df['risk_score'].median():.2f}")
    print(f"  Std Dev: {df['risk_score'].std():.2f}")
    print(f"  Min:    {df['risk_score'].min()}")
    print(f"  Max:    {df['risk_score'].max()}")
    
    print(f"\nRisk Distribution:")
    very_low = len(df[df['risk_score'] <= 20])
    low = len(df[(df['risk_score'] > 20) & (df['risk_score'] <= 40)])
    medium = len(df[(df['risk_score'] > 40) & (df['risk_score'] <= 60)])
    high = len(df[(df['risk_score'] > 60) & (df['risk_score'] <= 80)])
    very_high = len(df[df['risk_score'] > 80])
    
    total = len(df)
    print(f"  Very Low (0-20):    {very_low:4d} ({very_low/total*100:5.1f}%)")
    print(f"  Low (21-40):        {low:4d} ({low/total*100:5.1f}%)")
    print(f"  Medium (41-60):     {medium:4d} ({medium/total*100:5.1f}%)")
    print(f"  High (61-80):       {high:4d} ({high/total*100:5.1f}%)")
    print(f"  Very High (81-100): {very_high:4d} ({very_high/total*100:5.1f}%)")
    
    print(f"\n⚠ Transactions requiring review (Medium+ Risk): {medium + high + very_high} ({(medium + high + very_high)/total*100:.1f}%)")
    
    print("\n" + "=" * 80)
    print("Processing Complete!")
    print("=" * 80)
    
    return df

# Example usage
if __name__ == "__main__":
    csv_file_path = 'Part 1 - AML monitoring/langchain-workflow/langchain_modules/data/hi.csv'
    json_file_path = 'Part 1 - AML monitoring/langchain-workflow/logs/curr_MAS_rules.json'
    output_file_path = 'Part 1 - AML monitoring/langchain-workflow/langchain_modules/data/transactions_with_risk_scores.csv'
    
    result_df = process_transactions(csv_file_path, json_file_path, output_file_path)