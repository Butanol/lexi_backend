from gen_risk_score import process_transactions_multi
from gen_predictions import add_suspicion_scores
from assign_team import assign_team_from_csv

def update_rules(csv_input_path = "Part 1 - AML monitoring/langchain-workflow/langchain_modules/data/transactions_mock_1000_for_participants.csv", csv_output_path = "Part 1 - AML monitoring/langchain-workflow/langchain_modules/data/transactions_final.csv"):
    csv_path = csv_input_path
    mas_rules = "Part 1 - AML monitoring/langchain-workflow/logs/MAS_rules.json"
    finma_rules = "Part 1 - AML monitoring/langchain-workflow/logs/FINMA_rules.json"
    hkma_rules = "Part 1 - AML monitoring/langchain-workflow/logs/HKMA_rules.json"
    output_path = "Part 1 - AML monitoring/langchain-workflow/langchain_modules/data/transactions.csv"

    process_transactions_multi(csv_path, mas_rules, finma_rules, hkma_rules, output_path)

    add_suspicion_scores(
    input_csv="Part 1 - AML monitoring/langchain-workflow/langchain_modules/data/transactions.csv",
    output_csv="Part 1 - AML monitoring/langchain-workflow/langchain_modules/data/test_res.csv"
    )
    
    assign_team_from_csv(
        input_csv="Part 1 - AML monitoring/langchain-workflow/langchain_modules/data/test_res.csv",
        output_csv=csv_output_path
    )
    
if __name__ == "__main__":
    input = "Part 1 - AML monitoring/langchain-workflow/langchain_modules/data/transactions.csv"
    output = "Part 1 - AML monitoring/langchain-workflow/langchain_modules/data/transactions_final.csv"
    update_rules(input, output)