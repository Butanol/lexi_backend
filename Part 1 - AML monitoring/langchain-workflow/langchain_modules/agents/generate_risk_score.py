import os
import pandas as pd
import json
from datetime import datetime
from langchain_groq import ChatGroq
from typing import List, Dict, Tuple
import time

# Ensure the GROQ API key is set

# Set up the LLM model for Groq
validation_llm = ChatGroq(
    model="openai/gpt-oss-20b",
    temperature=0,
    max_tokens=2000,
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

def create_step1_context_prompt(rules: Dict, dataset_summary: Dict) -> str:
    """
    STEP 1: Establish context with rules and dataset overview.
    This gives the model understanding of the full landscape.
    """
    prompt = f"""You are an expert AML (Anti-Money Laundering) risk assessment system. You will be evaluating individual financial transactions against hard-enforced regulatory rules.

STEP 1: CONTEXT ESTABLISHMENT

ACTIONABLE RULES (Hard Limits):
{json.dumps(rules, indent=2)}

DATASET OVERVIEW:
- Total Transactions: {dataset_summary['total_transactions']}
- Transaction Amount Range: ${dataset_summary['min_amount']:.2f} - ${dataset_summary['max_amount']:.2f}
- Average Transaction: ${dataset_summary['avg_amount']:.2f}
- Date Range: {dataset_summary['date_range']}
- Unique Customers: {dataset_summary['unique_customers']}
- Unique Countries: {dataset_summary['unique_countries']}
{f"- High-Risk Countries Present: {', '.join(dataset_summary['high_risk_countries'][:10])}" if dataset_summary.get('high_risk_countries') else ""}

DATASET STATISTICS BY KEY FIELDS:
{json.dumps(dataset_summary.get('field_stats', {}), indent=2)}

YOUR TASK:
You will evaluate transactions ONE AT A TIME in the context of:
1. How close they are to violating the hard-limit rules above
2. The overall dataset patterns and norms
3. Comparative risk relative to other transactions in this dataset

RISK SCORING GUIDELINES (0-100):
- 0-20: Very Low Risk - Far from any thresholds (<50% of limits)
- 21-40: Low Risk - 50-70% of allowed thresholds
- 41-60: Medium Risk - 70-85% of allowed thresholds  
- 61-80: High Risk - 85-95% of allowed thresholds
- 81-100: Very High Risk - 95-99.9% close to rule violations

KEY PRINCIPLE: All transactions are technically compliant. Your score reflects PROXIMITY to rule violations, considering both absolute thresholds and relative patterns within this dataset.

Please acknowledge you understand the rules and dataset context. You will now receive individual transactions to evaluate."""
    
    return prompt

def create_step2_dataset_context_prompt(dataset: pd.DataFrame) -> str:
    """
    STEP 2: Provide aggregated dataset patterns and key transactions.
    This gives pattern context without overwhelming token limits.
    """
    # Generate aggregated patterns
    patterns = {}
    
    # Customer-level aggregations
    if 'customer_id' in dataset.columns:
        customer_agg = dataset.groupby('customer_id').agg({
            'amount': ['count', 'sum', 'mean', 'max']
        }).round(2)
        customer_agg.columns = ['_'.join(col).strip() for col in customer_agg.columns]
        patterns['customer_patterns'] = customer_agg.to_dict('index')
    
    # Country-level aggregations
    if 'country' in dataset.columns:
        country_agg = dataset.groupby('country').agg({
            'amount': ['count', 'sum', 'mean', 'max']
        }).round(2)
        country_agg.columns = ['_'.join(col).strip() for col in country_agg.columns]
        patterns['country_patterns'] = country_agg.to_dict('index')
    
    # Daily aggregations if date available
    date_col = None
    for col in ['transaction_date', 'date', 'timestamp']:
        if col in dataset.columns:
            date_col = col
            break
    
    if date_col:
        try:
            dataset[date_col] = pd.to_datetime(dataset[date_col])
            dataset['date_only'] = dataset[date_col].dt.date
            daily_agg = dataset.groupby('date_only').agg({
                'amount': ['count', 'sum', 'mean', 'max']
            }).round(2)
            daily_agg.columns = ['_'.join(col).strip() for col in daily_agg.columns]
            patterns['daily_patterns'] = {str(k): v for k, v in daily_agg.to_dict('index').items()}
        except:
            pass
    
    # Identify high-risk transactions (top 10 by amount)
    top_transactions = dataset.nlargest(10, 'amount')[['transaction_id', 'amount', 'customer_id', 'country']].to_dict('records') if 'amount' in dataset.columns else []
    
    # Identify transactions near thresholds (e.g., >$9000 for $10k threshold)
    near_threshold = dataset[dataset['amount'] > 9000].head(20).to_dict('records') if 'amount' in dataset.columns else []
    
    prompt = f"""STEP 2: DATASET PATTERNS AND KEY TRANSACTIONS

Instead of the full dataset, here are the aggregated patterns and key transactions to inform your risk assessments:

CUSTOMER TRANSACTION PATTERNS:
(Shows frequency and amounts per customer)
{json.dumps(list(patterns.get('customer_patterns', {}).items())[:30], indent=2)}
...and {max(0, len(patterns.get('customer_patterns', {})) - 30)} more customers

COUNTRY TRANSACTION PATTERNS:
(Shows frequency and amounts per country)
{json.dumps(patterns.get('country_patterns', {}), indent=2)}

DAILY TRANSACTION PATTERNS:
(Shows transaction volumes per day)
{json.dumps(list(patterns.get('daily_patterns', {}).items())[:15], indent=2)}
...and {max(0, len(patterns.get('daily_patterns', {})) - 15)} more days

TOP 10 HIGHEST-VALUE TRANSACTIONS:
{json.dumps(top_transactions, indent=2)}

TRANSACTIONS NEAR $10,000 THRESHOLD (>$9,000):
{json.dumps(near_threshold, indent=2)}

KEY INSIGHTS TO APPLY:
1. Use customer patterns to identify repeat transaction risks
2. Use country patterns to spot unusual geographic concentrations
3. Use daily patterns to identify clustering/frequency risks
4. Compare individual transactions to these aggregates
5. Transactions near thresholds warrant higher risk scores

You now have the pattern context. You will receive individual transactions to evaluate next."""
    
    return prompt

def create_step3_evaluation_prompt(transaction: Dict, transaction_index: int, total_transactions: int, 
                                   customer_context: Dict = None, country_context: Dict = None) -> str:
    """
    STEP 3: Evaluate a single transaction with relevant contextual information.
    """
    # Build contextual insights for this specific transaction
    context_insights = []
    
    if customer_context:
        context_insights.append(f"CUSTOMER CONTEXT: This customer has {customer_context.get('count', 0)} transactions, "
                               f"total value ${customer_context.get('sum', 0):.2f}, "
                               f"average ${customer_context.get('mean', 0):.2f}, "
                               f"max ${customer_context.get('max', 0):.2f}")
    
    if country_context:
        context_insights.append(f"COUNTRY CONTEXT: {transaction.get('country', 'Unknown')} has {country_context.get('count', 0)} transactions, "
                               f"total value ${country_context.get('sum', 0):.2f}, "
                               f"average ${country_context.get('mean', 0):.2f}")
    
    context_section = "\n".join(context_insights) if context_insights else "No additional context available"
    
    prompt = f"""STEP 3: TRANSACTION EVALUATION

Transaction {transaction_index + 1} of {total_transactions}:

TRANSACTION TO EVALUATE:
{json.dumps(transaction, indent=2)}

RELEVANT CONTEXT:
{context_section}

Based on the rules and dataset patterns provided earlier, evaluate this specific transaction.

EVALUATION CHECKLIST:
1. Amount Proximity: How close is the amount to daily/monthly thresholds?
2. Frequency Risk: Based on customer context, is this part of a risky pattern?
3. Geographic Risk: Based on country context, is this unusual or high-risk?
4. Pattern Analysis: How does this compare to this customer's typical behavior?
5. Compound Risk: Are multiple factors simultaneously approaching thresholds?
6. Comparative Risk: How does this rank in the dataset (refer to patterns from Step 2)?

OUTPUT FORMAT (JSON only, no other text):
{{
  "transaction_id": "{transaction.get('transaction_id', 'unknown')}",
  "risk_score": <integer 0-100>,
  "risk_factors": [
    "Specific factor 1 with percentages/numbers",
    "Specific factor 2 with percentages/numbers",
    "Specific factor 3 with percentages/numbers"
  ],
  "proximity_analysis": "Detailed explanation of proximity to rule violations with specific calculations",
  "comparative_analysis": "How this transaction compares to customer/country/dataset patterns"
}}

Return ONLY the JSON object, no additional text."""
    
    return prompt

def get_dataset_summary(df: pd.DataFrame) -> Dict:
    """Generate a statistical summary of the dataset."""
    summary = {
        'total_transactions': len(df),
        'min_amount': df['amount'].min() if 'amount' in df.columns else 0,
        'max_amount': df['amount'].max() if 'amount' in df.columns else 0,
        'avg_amount': df['amount'].mean() if 'amount' in df.columns else 0,
        'unique_customers': df['customer_id'].nunique() if 'customer_id' in df.columns else 0,
        'unique_countries': df['country'].nunique() if 'country' in df.columns else 0,
        'date_range': 'N/A',
        'field_stats': {}
    }
    
    # Add date range if available
    if 'transaction_date' in df.columns or 'date' in df.columns:
        date_col = 'transaction_date' if 'transaction_date' in df.columns else 'date'
        try:
            df[date_col] = pd.to_datetime(df[date_col])
            summary['date_range'] = f"{df[date_col].min()} to {df[date_col].max()}"
        except:
            pass
    
    # Add field-level statistics
    numeric_cols = df.select_dtypes(include=['number']).columns
    for col in numeric_cols:
        if col in df.columns:
            summary['field_stats'][col] = {
                'mean': float(df[col].mean()),
                'median': float(df[col].median()),
                'std': float(df[col].std()),
                'min': float(df[col].min()),
                'max': float(df[col].max())
            }
    
    # Identify high-risk countries if country column exists
    if 'country' in df.columns:
        high_risk_countries = ['North Korea', 'Iran', 'Syria', 'Cuba', 'Myanmar', 
                               'Afghanistan', 'Yemen', 'Sudan', 'Venezuela', 'Russia']
        present_high_risk = [c for c in high_risk_countries if c in df['country'].values]
        summary['high_risk_countries'] = present_high_risk
    
    return summary

def parse_single_transaction_response(response_text: str) -> Dict:
    """Parse the model's response for a single transaction."""
    try:
        # Try to find JSON object in the response
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}') + 1
        
        if start_idx == -1 or end_idx == 0:
            raise ValueError("No JSON object found in response")
        
        json_str = response_text[start_idx:end_idx]
        risk_assessment = json.loads(json_str)
        
        return risk_assessment
    except json.JSONDecodeError as e:
        print(f"    ✗ JSON parsing error: {e}")
        print(f"    Response preview: {response_text[:200]}")
        return None
    except Exception as e:
        print(f"    ✗ Error parsing response: {e}")
        return None

def invoke_llm(prompt: str, step_name: str = "") -> str:
    """Invoke the LLM and return response text."""
    try:
        response = validation_llm.invoke(prompt)
        
        # Extract response text (handle different response formats)
        if hasattr(response, 'content'):
            return response.content
        elif isinstance(response, dict) and 'text' in response:
            return response['text']
        else:
            return str(response)
    except Exception as e:
        print(f"    ✗ Error invoking LLM {step_name}: {e}")
        return None

def process_transactions(csv_file_path: str, json_file_path: str, output_file_path: str):
    """
    Main function to process transactions with multi-step prompting.
    Each transaction is evaluated individually with full dataset context.
    """
    print("=" * 70)
    print("AML RISK SCORING SYSTEM - Multi-Step Contextual Processing")
    print("=" * 70)
    
    # Load data
    print("\n[1/5] Loading data...")
    rules = load_actionable_rules(json_file_path)
    df = load_data(csv_file_path)
    print(f"    ✓ Loaded {len(df)} transactions")
    print(f"    ✓ Loaded {len(rules)} rule categories" if isinstance(rules, dict) else f"    ✓ Loaded rules")
    
    # Generate dataset summary
    print("\n[2/5] Generating dataset summary...")
    dataset_summary = get_dataset_summary(df)
    print(f"    ✓ Dataset summary created")
    print(f"    ✓ Amount range: ${dataset_summary['min_amount']:.2f} - ${dataset_summary['max_amount']:.2f}")
    print(f"    ✓ {dataset_summary['unique_customers']} unique customers")
    
    # STEP 1: Send context with rules and dataset summary
    print("\n[3/5] STEP 1: Establishing context with rules and dataset overview...")
    step1_prompt = create_step1_context_prompt(rules, dataset_summary)
    step1_response = invoke_llm(step1_prompt, "Step 1")
    if step1_response:
        print(f"    ✓ Context established")
        print(f"    Model response: {step1_response[:150]}...")
    else:
        print(f"    ✗ Failed to establish context")
        return
    
    time.sleep(1)  # Rate limiting
    
    # STEP 2: Send aggregated dataset patterns
    print("\n[4/5] STEP 2: Sending aggregated dataset patterns...")
    step2_prompt = create_step2_dataset_context_prompt(df)
    step2_response = invoke_llm(step2_prompt, "Step 2")
    if step2_response:
        print(f"    ✓ Dataset patterns provided")
        print(f"    Model response: {step2_response[:150]}...")
    else:
        print(f"    ✗ Failed to provide dataset patterns")
        return
    
    time.sleep(1)  # Rate limiting
    
    # Pre-compute aggregations for context
    print("\n[5/5] Pre-computing customer and country aggregations...")
    customer_agg_dict = {}
    country_agg_dict = {}
    
    if 'customer_id' in df.columns and 'amount' in df.columns:
        customer_agg = df.groupby('customer_id').agg({
            'amount': ['count', 'sum', 'mean', 'max']
        }).round(2)
        customer_agg.columns = ['count', 'sum', 'mean', 'max']
        customer_agg_dict = customer_agg.to_dict('index')
        print(f"    ✓ Computed patterns for {len(customer_agg_dict)} customers")
    
    if 'country' in df.columns and 'amount' in df.columns:
        country_agg = df.groupby('country').agg({
            'amount': ['count', 'sum', 'mean', 'max']
        }).round(2)
        country_agg.columns = ['count', 'sum', 'mean', 'max']
        country_agg_dict = country_agg.to_dict('index')
        print(f"    ✓ Computed patterns for {len(country_agg_dict)} countries")
    
    # STEP 3: Evaluate each transaction individually
    print(f"\nSTEP 3: Evaluating {len(df)} transactions individually...")
    print("-" * 70)
    
    all_risk_data = []
    total_transactions = len(df)
    
    for idx, row in df.iterrows():
        transaction = row.to_dict()
        
        print(f"\nTransaction {idx + 1}/{total_transactions}: ", end="")
        if 'transaction_id' in transaction:
            print(f"{transaction['transaction_id']}")
        else:
            print(f"Row {idx}")
        
        # Create evaluation prompt for this specific transaction
        step3_prompt = create_step3_evaluation_prompt(transaction, idx, total_transactions)
        step3_response = invoke_llm(step3_prompt, f"Step 3 - Txn {idx + 1}")
        
        if step3_response:
            # Parse the response
            risk_assessment = parse_single_transaction_response(step3_response)
            
            if risk_assessment:
                all_risk_data.append(risk_assessment)
                score = risk_assessment.get('risk_score', 'N/A')
                print(f"    ✓ Risk Score: {score}")
                if 'risk_factors' in risk_assessment and risk_assessment['risk_factors']:
                    print(f"    Top Factor: {risk_assessment['risk_factors'][0][:60]}...")
            else:
                # Add default assessment
                all_risk_data.append({
                    'transaction_id': transaction.get('transaction_id', f'row_{idx}'),
                    'risk_score': 50,
                    'risk_factors': ['Parsing error'],
                    'proximity_analysis': 'Could not parse model response',
                    'comparative_analysis': 'N/A'
                })
                print(f"    ✗ Using default score (50)")
        else:
            # Add default assessment
            all_risk_data.append({
                'transaction_id': transaction.get('transaction_id', f'row_{idx}'),
                'risk_score': 50,
                'risk_factors': ['Processing error'],
                'proximity_analysis': 'Model invocation failed',
                'comparative_analysis': 'N/A'
            })
            print(f"    ✗ Using default score (50)")
        
        # Rate limiting - small delay between requests
        if (idx + 1) % 10 == 0:
            print(f"\n    ... Processed {idx + 1}/{total_transactions} transactions ...")
            time.sleep(2)  # Longer pause every 10 transactions
        else:
            time.sleep(0.5)
    
    # Merge results with original dataframe
    print("\n" + "=" * 70)
    print("Finalizing results...")
    print("=" * 70)
    
    risk_df = pd.DataFrame(all_risk_data)
    
    if 'transaction_id' in df.columns:
        result_df = df.merge(risk_df, on='transaction_id', how='left')
    else:
        result_df = df.copy()
        for col in risk_df.columns:
            if col != 'transaction_id':
                result_df[col] = risk_df[col].values[:len(df)]
    
    # Save results
    result_df.to_csv(output_file_path, index=False)
    print(f"\n✓ Results saved to: {output_file_path}")
    
    # Print summary statistics
    print(f"\n{'=' * 70}")
    print("RISK ASSESSMENT SUMMARY")
    print("=" * 70)
    print(f"\nRisk Score Statistics:")
    print(f"  Mean:   {result_df['risk_score'].mean():.2f}")
    print(f"  Median: {result_df['risk_score'].median():.2f}")
    print(f"  Std Dev: {result_df['risk_score'].std():.2f}")
    print(f"  Min:    {result_df['risk_score'].min()}")
    print(f"  Max:    {result_df['risk_score'].max()}")
    
    print(f"\nRisk Distribution:")
    very_low = len(result_df[result_df['risk_score'] <= 20])
    low = len(result_df[(result_df['risk_score'] > 20) & (result_df['risk_score'] <= 40)])
    medium = len(result_df[(result_df['risk_score'] > 40) & (result_df['risk_score'] <= 60)])
    high = len(result_df[(result_df['risk_score'] > 60) & (result_df['risk_score'] <= 80)])
    very_high = len(result_df[result_df['risk_score'] > 80])
    
    print(f"  Very Low (0-20):    {very_low:4d} ({very_low/len(df)*100:5.1f}%)")
    print(f"  Low (21-40):        {low:4d} ({low/len(df)*100:5.1f}%)")
    print(f"  Medium (41-60):     {medium:4d} ({medium/len(df)*100:5.1f}%)")
    print(f"  High (61-80):       {high:4d} ({high/len(df)*100:5.1f}%)")
    print(f"  Very High (81-100): {very_high:4d} ({very_high/len(df)*100:5.1f}%)")
    
    print("\n" + "=" * 70)
    print("Processing Complete!")
    print("=" * 70)

# Example usage
if __name__ == "__main__":
    csv_file_path = 'Part 1 - AML monitoring/langchain-workflow/langchain_modules/data/transactions_mock_1000_for_participants.csv'
    json_file_path = 'Part 1 - AML monitoring/langchain-workflow/logs/curr_MAS_rules.json'
    output_file_path = 'Part 1 - AML monitoring/langchain-workflow/langchain_modules/data/transactions_with_risk_scores.csv'
    
    process_transactions(csv_file_path, json_file_path, output_file_path)