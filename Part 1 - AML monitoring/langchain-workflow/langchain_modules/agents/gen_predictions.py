import pandas as pd
import pickle
from typing import Optional

def add_suspicion_scores(
    input_csv: str,
    output_csv: Optional[str] = None,
    model_path: str = "Part 1 - AML monitoring/langchain-workflow/model/xgb_suspicion_model.pkl",
    encoders_path: str = "Part 1 - AML monitoring/langchain-workflow/model/label_encoders.pkl",
    threshold: float = 0.7
):
    """
    Adds suspicion confidence and flagged columns to a CSV of transactions.

    Args:
        input_csv (str): Path to input CSV file.
        output_csv (str, optional): Path to save the output CSV. Defaults to <input_csv>_with_predictions.csv.
        model_path (str): Path to the saved XGBoost model.
        encoders_path (str): Path to the saved label encoders.
        threshold (float): Probability threshold to flag suspicious transactions.
    """
    # ----------------------------
    # 1. Load original dataset
    # ----------------------------
    original_df = pd.read_csv(input_csv)
    df = original_df.copy()  # working copy

    # ----------------------------
    # 2. Prepare features for model
    # ----------------------------
    drop_cols = [
        "transaction_id",
        "customer_id",
        "risk_reasoning",
        "booking_datetime",
        "value_date",
        "narrative",
        "originator_name",
        "originator_account",
        "beneficiary_name",
        "beneficiary_account",
        "originator_country",
        "beneficiary_country",
        "suspicion_determined_datetime",
        "str_filed_datetime"
    ]
    X = df.drop(columns=[c for c in drop_cols if c in df.columns], errors="ignore")

    # ----------------------------
    # 3. Load saved model and encoders
    # ----------------------------
    with open(model_path, "rb") as f:
        model = pickle.load(f)

    with open(encoders_path, "rb") as f:
        label_encoders = pickle.load(f)

    # Encode categorical columns with saved encoders
    for col, le in label_encoders.items():
        if col in X.columns:
            X[col] = X[col].map(
                lambda x: le.transform([str(x)])[0] if str(x) in le.classes_ else -1
            )
        else:
            X[col] = 0

    # ----------------------------
    # 4. Make predictions
    # ----------------------------
    df["suspicion_confidence"] = model.predict_proba(X)[:, 1]
    df["flagged"] = (df["suspicion_confidence"] > threshold).astype(int)

    # ----------------------------
    # 5. Save output CSV
    # ----------------------------
    if output_csv is None:
        output_csv = input_csv.replace(".csv", "_with_predictions.csv")

    df.to_csv(output_csv, index=False)
    print(f"✅ Predictions added and saved to {output_csv}")
    return df

df_with_preds = add_suspicion_scores(
    input_csv="Part 1 - AML monitoring/langchain-workflow/langchain_modules/data/transactions.csv",
    output_csv="Part 1 - AML monitoring/langchain-workflow/langchain_modules/data/transactions_with_suspicion_score.csv"
)