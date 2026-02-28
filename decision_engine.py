from models import db, Rule, Action, Event, AuditLog, Customer
from datetime import datetime
import numpy as np
import joblib
import json

# Load Models and Encoders (Ensure these are trained and saved via train_models.py)
try:
    xgb_model = joblib.load('xgboost_model.pkl')
    action_encoder = joblib.load('action_encoder.pkl')
    tier_encoder = joblib.load('tier_encoder.pkl')
    comm_encoder = joblib.load('comm_encoder.pkl')
except FileNotFoundError:
    print("Warning: ML models/encoders not found. Make sure to train models first.")

# Define financial costs of actions
ACTION_COSTS = {
    'none': 0.0,
    'apology_email': 0.10,   
    '10_credit': 10.0,       
    'refund_shipping': 15.0  
}

def log_audit(event_id, customer_id, action_taken, metrics):
    """Handles the immutable audit logging with cryptographic hashing."""
    audit_data = {
        'event_id': event_id,
        'customer_id': customer_id,
        'action_taken': action_taken,
        'optimization_metrics': metrics,
        'timestamp': datetime.utcnow().isoformat()
    }
    last_log = AuditLog.query.order_by(AuditLog.id.desc()).first()
    prev_hash = last_log.hash if last_log else '0'*64
    new_hash = AuditLog.compute_hash(prev_hash, datetime.utcnow(), audit_data)
    
    audit = AuditLog(
        previous_hash=prev_hash,
        data=audit_data,
        hash=new_hash
    )
    db.session.add(audit)

def process_event(event_id):
    """
    Prescriptive Decision Pipeline:
    Calculates expected utility of all actions and executes the mathematical optimum.
    """
    event = Event.query.get(event_id)
    if not event:
        return {'error': 'Event not found'}
    if event.processed:
        return {'message': 'Event already processed'}

    customer = Customer.query.get(event.customer_id)
    if not customer:
        return {'error': 'Customer not found'}

    # 1. Base State Representation
    t_encoded = tier_encoder.transform([customer.tier])[0]
    c_encoded = comm_encoder.transform([customer.communication_preference])[0]
    
    # Mocking past_issues and avg_order_value for the pipeline 
    # (In a full app, these would be fields on the Customer model)
    base_features = [
        t_encoded, 
        event.delay_hours, 
        getattr(customer, 'past_issues', 1), 
        getattr(customer, 'average_order_value', 100.0), 
        getattr(customer, 'tenure_months', 12), 
        c_encoded
    ]

    # 2. Calculate Baseline Churn (Action = 'none')
    none_encoded = action_encoder.transform(['none'])[0]
    X_baseline = np.array([base_features + [none_encoded]])
    P_baseline = xgb_model.predict_proba(X_baseline)[0][1]

    best_action = 'none'
    max_utility = 0.0
    action_metrics = []

    # 3. Prescriptive Optimization Loop (Expected Utility)
    for action_name, cost in ACTION_COSTS.items():
        if action_name == 'none': continue

        act_encoded = action_encoder.transform([action_name])[0]
        X_action = np.array([base_features + [act_encoded]])
        
        # Predict counterfactual churn
        P_action = xgb_model.predict_proba(X_action)[0][1]
        
        # E[U] = (P_baseline - P_action) * LTV - Cost
        delta_P = P_baseline - P_action
        expected_utility = (delta_P * customer.ltv_score) - cost
        
        action_metrics.append({
            'action': action_name,
            'cost': cost,
            'projected_churn': round(float(P_action), 4),
            'delta_P': round(float(delta_P), 4),
            'expected_utility': round(float(expected_utility), 2)
        })

        if expected_utility > max_utility:
            max_utility = expected_utility
            best_action = action_name

    # 4. Execute mathematically optimal action
    actions_taken = []
    if max_utility > 0 and best_action != 'none':
        action_record = Action(
            event_id=event.id,
            rule_id=None, # Bypassing static rules for dynamic ML optimization
            action_type=best_action,
            action_params={'cost': ACTION_COSTS[best_action], 'expected_roi': max_utility},
            status='success'
        )
        db.session.add(action_record)
        actions_taken.append(action_record)
        
    log_audit(event.id, customer.id, best_action, action_metrics)

    event.processed = True
    db.session.commit()

    return {
        'event_id': event.id,
        'customer_id': customer.id,
        'baseline_churn_risk': round(float(P_baseline), 4),
        'optimization_metrics': action_metrics,
        'selected_action': best_action,
        'projected_roi': round(float(max_utility), 2),
        'actions_taken': [{'id': a.id, 'type': a.action_type} for a in actions_taken]
    }