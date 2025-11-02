from gen_predictions_irl import add_suspicion_scores
from assign_team import assign_team_from_csv

def update_rules_irl(csv_input_path = "Part 1 - AML monitoring/langchain-workflow/langchain_modules/data/transactions_mock_1000_for_participants.csv", csv_output_path = "Part 1 - AML monitoring/langchain-workflow/langchain_modules/data/transactions_final.csv"):
    csv_path = csv_input_path

    add_suspicion_scores(
    input_csv= csv_input_path,
    output_csv="Part 1 - AML monitoring/langchain-workflow/langchain_modules/data/test_res100.csv"
    )
    
    assign_team_from_csv(
        input_csv="Part 1 - AML monitoring/langchain-workflow/langchain_modules/data/test_res100.csv",
        output_csv=csv_output_path
    )
    
if __name__ == "__main__":
    input = "Part 1 - AML monitoring/langchain-workflow/langchain_modules/data/transactions_mock_1000_for_participants(part 1).csv"
    output = "Part 1 - AML monitoring/langchain-workflow/langchain_modules/data/transactions_final_part1.csv"
    update_rules_irl(input, output)