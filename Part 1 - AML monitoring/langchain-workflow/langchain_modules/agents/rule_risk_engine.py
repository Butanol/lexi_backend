# gens the risk using rules when a csv is generated

def generate_risk_using_rules(file_path, rules):
    import pandas as pd

    df = pd.read_csv(file_path)
    risk_results = []

    for _, row in df.iterrows():
        transaction_risks = []
        for rule in rules:
            if eval(rule['condition'], {}, row.to_dict()):
                transaction_risks.append(rule['risk_level'])
        overall_risk = max(transaction_risks) if transaction_risks else 'Low'
        risk_results.append(overall_risk)

    df['risk_level'] = risk_results
    return df
    
    
    