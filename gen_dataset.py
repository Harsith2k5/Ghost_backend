"""
Synthetic Dataset Generation for Project Ghost 2.0 (Uplift Modeling)
Generates 10,000 samples with realistic causal treatment effects and mapped actions.
"""
import numpy as np
import pandas as pd
import random

# Set seed for reproducibility
np.random.seed(42)
random.seed(42)

N_SAMPLES = 10000
TIERS = ['Platinum', 'Gold', 'Silver', 'Bronze']
COMM_PREFS = ['email', 'sms', 'push']
# MUST match the exact strings the Flask backend sends!
ACTIONS = ['do_nothing', 'email', 'credit', 'refund']

# Generate synthetic base data
data = {
    'customer_id': range(1, N_SAMPLES + 1),
    'customer_tier': np.random.choice(TIERS, N_SAMPLES, p=[0.15, 0.25, 0.35, 0.25]),
    'delay_hours': np.random.exponential(scale=12.0, size=N_SAMPLES).clip(0, 72),
    'past_issues': np.random.poisson(lam=0.5, size=N_SAMPLES),
    # Adjusted LTV generation to match your UI scenarios ($800 - $5000)
    'order_value': np.random.uniform(500, 5000, size=N_SAMPLES), 
    'communication_preference': np.random.choice(COMM_PREFS, N_SAMPLES),
    'customer_tenure_months': np.random.gamma(shape=2, scale=12, size=N_SAMPLES).astype(int) + 1,
    'action_applied': np.random.choice(ACTIONS, N_SAMPLES)
}

df = pd.DataFrame(data)

# Encode categoricals for baseline logit calculation
tier_map = {'Platinum': 3, 'Gold': 2, 'Silver': 1, 'Bronze': 0}
df['tier_encoded'] = df['customer_tier'].map(tier_map)

# ---------------------------------------------------------
# 1. BASE CHURN CALCULATION (Pre-Action)
# Rebalanced so the logit stays between -3.0 and +3.0 generally
# ---------------------------------------------------------
logit = -2.0  
logit += 0.10 * df['delay_hours']        # Delays increase churn probability
logit += 1.50 * df['past_issues']        # Past issues (Fatigue) MASSIVELY increase churn
logit -= 0.40 * df['tier_encoded']       # Higher tiers are slightly more forgiving
logit -= 0.0002 * df['order_value']      # High LTV customers have slightly lower baseline churn
logit -= 0.02 * df['customer_tenure_months'] 

# ---------------------------------------------------------
# 2. MATHEMATICAL TREATMENT EFFECT (Uplift / Causal Inference)
# This teaches the XGBoost S-Learner WHAT to do and WHEN.
# ---------------------------------------------------------
treatment_effect = np.zeros(N_SAMPLES)

# A. Email: Works fine normally, but BACKFIRES if they have apology fatigue
email_mask = df['action_applied'] == 'email'
# If past_issues > 0, the +2.0 penalty ruins the -1.5 benefit
treatment_effect[email_mask] = -1.5 + (2.0 * df.loc[email_mask, 'past_issues'])

# B. Credit: Strong baseline effect, great for moderate delays
credit_mask = df['action_applied'] == 'credit'
treatment_effect[credit_mask] = -2.5 - (0.01 * df.loc[credit_mask, 'delay_hours'])

# C. Refund: The nuclear option. Cures almost anything, heavily reduces churn for massive delays
refund_mask = df['action_applied'] == 'refund'
treatment_effect[refund_mask] = -4.0 - (0.05 * df.loc[refund_mask, 'delay_hours'])

# D. Do Nothing: 0.0 effect (already handled by np.zeros)

# Apply treatment to the logit
logit += treatment_effect

# Convert to probability (Sigmoid function)
churn_prob = 1 / (1 + np.exp(-logit))
churn_prob = np.clip(churn_prob, 0.01, 0.99)

df['churn_probability'] = churn_prob
# Assign final 1 (Churn) or 0 (Retained) based on the calculated probability
df['churn_label'] = (np.random.random(N_SAMPLES) < churn_prob).astype(int)

# Drop temporary encoding
df.drop('tier_encoded', axis=1, inplace=True)

df.to_csv('churn_synthetic_dataset.csv', index=False)
print(f"Generated {N_SAMPLES} samples with fixed causal treatment effects.")