"""
ML Churn Prediction Module
Loads trained XGBoost model (or falls back to logistic regression) to predict churn probability.
Includes feature preprocessing and optional ensemble.
"""

import joblib
import numpy as np
import os

# Load models and encoders at module load
MODEL_DIR = os.path.dirname(__file__)

try:
    # Try loading XGBoost first (more accurate)
    xgb_model = joblib.load(os.path.join(MODEL_DIR, 'xgboost_model.pkl'))
    scaler = joblib.load(os.path.join(MODEL_DIR, 'scaler.pkl'))
    tier_encoder = joblib.load(os.path.join(MODEL_DIR, 'tier_encoder.pkl'))
    comm_encoder = joblib.load(os.path.join(MODEL_DIR, 'comm_encoder.pkl'))
    model = xgb_model
    use_scaling = False  # XGBoost doesn't need scaling
    print("Loaded XGBoost churn model.")
except:
    try:
        # Fallback to logistic regression
        lr_model = joblib.load(os.path.join(MODEL_DIR, 'logistic_regression_model.pkl'))
        scaler = joblib.load(os.path.join(MODEL_DIR, 'scaler.pkl'))
        tier_encoder = joblib.load(os.path.join(MODEL_DIR, 'tier_encoder.pkl'))
        comm_encoder = joblib.load(os.path.join(MODEL_DIR, 'comm_encoder.pkl'))
        model = lr_model
        use_scaling = True
        print("Loaded Logistic Regression churn model.")
    except:
        print("No trained model found. Using fallback random predictor.")
        model = None

def predict_churn_probability(customer_tier, delay_hours, past_issues=0, order_value=90, customer_tenure_months=12, communication_preference='email'):
    """
    Predict churn probability based on customer and event features.
    All arguments except customer_tier and delay_hours are optional with defaults.
    """
    if model is None:
        # Fallback random (as before)
        import random
        base = 0.1
        if customer_tier == 'Platinum':
            base += 0.05
        elif customer_tier == 'Gold':
            base += 0.03
        base += min(delay_hours * 0.02, 0.3)
        base += past_issues * 0.1
        return min(base + random.uniform(-0.05, 0.05), 1.0)

    # Encode categoricals
    try:
        tier_enc = tier_encoder.transform([customer_tier])[0]
    except:
        # If unknown tier, default to median (Silver=1)
        tier_enc = 1

    try:
        comm_enc = comm_encoder.transform([communication_preference])[0]
    except:
        comm_enc = 0  # email default

    # Build feature vector (order must match training)
    features = np.array([[
        tier_enc,
        delay_hours,
        past_issues,
        order_value,
        customer_tenure_months,
        comm_enc
    ]])

    # Scale if needed
    if use_scaling:
        features = scaler.transform(features)

    # Predict probability
    proba = model.predict_proba(features)[0, 1]
    return float(proba)