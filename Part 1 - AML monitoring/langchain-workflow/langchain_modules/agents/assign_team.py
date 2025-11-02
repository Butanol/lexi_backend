import pandas as pd
from datetime import datetime

def assign_team_from_csv(input_csv: str, output_csv: str) -> pd.DataFrame:
    """
    Reads a transaction CSV and assigns each row to:
      - 'Front Office' if KYC/EDD/suitability issues exist
      - 'Legal and Compliance Team' if transaction is flagged
      - '' otherwise
    Uses kyc_last_completed vs kyc_due_date comparison instead of current date.
    """
    df = pd.read_csv(input_csv)

    # --- Normalize boolean columns ---
    bool_cols = [
        "edd_required", "edd_performed", "suitability_assessed",
        "product_complex", "is_advised", "product_has_va_exposure",
        "va_disclosure_provided", "cash_id_verified"
    ]
    for col in bool_cols:
        if col in df.columns:
            df[col] = (
                df[col].astype(str)
                .str.strip()
                .str.lower()
                .map({"true": True, "false": False, "1": True, "0": False})
                .fillna(False)
            )

    # --- Normalize date columns ---
    date_cols = ["kyc_due_date", "kyc_last_completed"]
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)

    # --- Assign team based on new logic ---
    def assign_team(row):
        # Condition 1: EDD required but not performed
        edd_issue = bool(row.get("edd_required")) and not bool(row.get("edd_performed"))

        # Condition 2: KYC outdated (last completed before due date)
        kyc_last = row.get("kyc_last_completed")
        kyc_due = row.get("kyc_due_date")
        kyc_issue = pd.notna(kyc_last) and pd.notna(kyc_due) and (kyc_last > kyc_due)

        # Condition 3: Suitability not assessed
        suitability_issue = not bool(row.get("suitability_assessed"))

        # Condition 4: Suspicious (flagged by model)
        flagged = row.get("flagged", 0)

        if flagged == 1:
            return "Legal and Compliance Team"
        elif edd_issue or kyc_issue or suitability_issue:
            return "Front Office"
        else:
            return ""

    df["assigned_team"] = df.apply(assign_team, axis=1)

    df.to_csv(output_csv, index=False)
    print(f"✅ Team assignment complete. Saved to: {output_csv}")

    return df


assign_team_from_csv(
    input_csv="Part 1 - AML monitoring/langchain-workflow/langchain_modules/data/transactions_final1.csv",
    output_csv="Part 1 - AML monitoring/langchain-workflow/langchain_modules/data/transactions_final2.csv"
)
