import pandas as pd
import pickle
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier

# ----------------------------
# 1. Load dataset
# ----------------------------
df = pd.read_csv("Part 1 - AML monitoring/langchain-workflow/langchain_modules/data/transactions.csv")

# Create binary label: suspicious or STR filed
df["is_suspicious"] = (
    df["suspicion_determined_datetime"].notna() | df["str_filed_datetime"].notna()
).astype(int)

# Drop columns not used for training
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
df = df.drop(columns=[c for c in drop_cols if c in df.columns], errors="ignore")

# ----------------------------
# 2. Encode categorical features
# ----------------------------
cat_cols = df.select_dtypes(include=["object"]).columns
label_encoders = {}
for col in cat_cols:
    le = LabelEncoder()
    df[col] = le.fit_transform(df[col].astype(str))
    label_encoders[col] = le

# ----------------------------
# 3. Prepare training data
# ----------------------------
X = df.drop(columns=["is_suspicious"])
y = df["is_suspicious"]

# ----------------------------
# 4. Train XGBoost on entire dataset
# ----------------------------
model = XGBClassifier(
    eval_metric="logloss",
    learning_rate=0.1,
    max_depth=6,
    n_estimators=300,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42
)

model.fit(X, y)

# ----------------------------
# 5. Save model and preprocessing
# ----------------------------
# Save XGBoost model
with open("Part 1 - AML monitoring/langchain-workflow/model/xgb_suspicion_model.pkl", "wb") as f:
    pickle.dump(model, f)

# Save label encoders
with open("Part 1 - AML monitoring/langchain-workflow/model/label_encoders.pkl", "wb") as f:
    pickle.dump(label_encoders, f)

print("✅ Model and label encoders saved successfully.")
