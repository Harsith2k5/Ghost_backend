"""
Train two lightweight churn prediction models (S-Learner for Uplift):
1. Logistic Regression (interpretable)
2. XGBoost (prescriptive / more accurate)
Saves models, scalers, and encoders for the decision engine.
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score, classification_report
import xgboost as xgb
import joblib
import warnings
warnings.filterwarnings('ignore')

# Load dataset
print("Loading synthetic dataset...")
df = pd.read_csv('churn_synthetic_dataset.csv')

# Feature engineering
# Encode categoricals
tier_encoder = LabelEncoder()
df['tier_encoded'] = tier_encoder.fit_transform(df['customer_tier'])  # 0:Bronze,1:Silver,2:Gold,3:Platinum

comm_encoder = LabelEncoder()
df['comm_encoded'] = comm_encoder.fit_transform(df['communication_preference'])  # 0:email,1:push,2:sms

# Encode the Action (THIS IS THE KEY FOR PRESCRIPTIVE ANALYTICS)
action_encoder = LabelEncoder()
df['action_encoded'] = action_encoder.fit_transform(df['action_applied']) 

# Select features (Now including the action)
feature_cols = [
    'tier_encoded',
    'delay_hours',
    'past_issues',
    'order_value',
    'customer_tenure_months',
    'comm_encoded',
    'action_encoded' # <-- The prescriptive feature
]

X = df[feature_cols]
y = df['churn_label']

# Train/test split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

# Scale features (important for logistic regression)
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# ---------- Logistic Regression ----------
print("\nTraining Logistic Regression...")
lr_model = LogisticRegression(C=1.0, max_iter=1000, random_state=42)
lr_model.fit(X_train_scaled, y_train)

# Predictions
y_pred_lr = lr_model.predict(X_test_scaled)
y_proba_lr = lr_model.predict_proba(X_test_scaled)[:, 1]

acc_lr = accuracy_score(y_test, y_pred_lr)
auc_lr = roc_auc_score(y_test, y_proba_lr)
print(f"Logistic Regression - Accuracy: {acc_lr:.4f}, AUC: {auc_lr:.4f}")
print(classification_report(y_test, y_pred_lr, digits=4))

# ---------- XGBoost (S-Learner) ----------
print("\nTraining Prescriptive XGBoost (S-Learner)...")
# Tuned specifically for probability calibration
xgb_model = xgb.XGBClassifier(
    n_estimators=150,
    max_depth=5,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    objective='binary:logistic',
    eval_metric='logloss'
)
xgb_model.fit(X_train, y_train)  # XGBoost doesn't need scaling

y_pred_xgb = xgb_model.predict(X_test)
y_proba_xgb = xgb_model.predict_proba(X_test)[:, 1]

acc_xgb = accuracy_score(y_test, y_pred_xgb)
auc_xgb = roc_auc_score(y_test, y_proba_xgb)
print(f"XGBoost - Accuracy: {acc_xgb:.4f}, AUC: {auc_xgb:.4f}")
print(classification_report(y_test, y_pred_xgb, digits=4))

# Save models and encoders/scaler
joblib.dump(lr_model, 'logistic_regression_model.pkl')
joblib.dump(xgb_model, 'xgboost_model.pkl')
joblib.dump(scaler, 'scaler.pkl')
joblib.dump(tier_encoder, 'tier_encoder.pkl')
joblib.dump(comm_encoder, 'comm_encoder.pkl')
joblib.dump(action_encoder, 'action_encoder.pkl') # <-- Saving the new encoder

print("\nAll models and encoders successfully saved for the Decision Engine.")