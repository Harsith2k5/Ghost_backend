""" from flask import Flask, request, jsonify
from flask_cors import CORS
from config import Config
from models import db, Customer, Event, Rule, Action, AuditLog
from auth import require_auth
from decision_engine import process_event
from datetime import datetime, timedelta
import math
import json

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)
db.init_app(app)

# Create tables (in production use migrations)
with app.app_context():
    db.create_all()

# ------------------------------------------------------------
# ARCHITECTURE MODULE 1: Systemic Shock & Volatility Engine
# ------------------------------------------------------------

# ------------------------------------------------------------
@app.route('/api/simulate-scenario', methods=['POST'])
def simulate_scenario():
    
    data = request.get_json()
    scenario_id = data.get('scenario_id', 1)
    
    # Base costs
    costs = {'email': 0.10, 'credit': 10.0, 'refund': 15.0}

    # Set initial scenario variables
    if scenario_id == 1:
        # Standard: High LTV, moderate delay, no system shock, no fatigue
        ltv = 4500.0
        delay_hours = 12.0
        shock_ratio = 1.0
        fatigue_incidents = 0
        customer_tier = "Platinum"
    elif scenario_id == 2:
        # Shock: Low LTV, high delay, MASSIVE system shock (Blizzard)
        ltv = 800.0
        delay_hours = 48.0
        shock_ratio = 8.5
        fatigue_incidents = 0
        customer_tier = "Silver"
    else:
        # Fatigue: Moderate LTV, low delay, HIGH fatigue (Repeated failures)
        ltv = 2100.0
        delay_hours = 8.0
        shock_ratio = 0.9
        fatigue_incidents = 3
        customer_tier = "Gold"

    trace = []

    # 1. INGESTION MODULE
    trace.append({
        "module": "Context Ingestion",
        "title": "SAP Logistics & CRM Data",
        "details": f"Tier: {customer_tier}\nLTV: ${ltv:,.2f}\nDelay: {delay_hours} hours detected."
    })

    # 2. VOLATILITY ENGINE (Lagrange Math)
    kappa = 2.5
    lambda_penalty = max(0.0, kappa * (shock_ratio - 1.5))
    system_status = "CRITICAL (BUDGET BURN)" if lambda_penalty > 0 else "NOMINAL"
    
    trace.append({
        "module": "Volatility Engine",
        "title": "CFO Guardian (Constraint Math)",
        "details": f"Global Velocity: {shock_ratio}x\nStatus: {system_status}\nShadow Price (λ): {lambda_penalty:.2f}x penalty applied to costs."
    })

    # 3. FATIGUE ENGINE (Exponential Decay Math)
    k_decay = 0.8 # Decay constant
    fatigue_score = sum([math.exp(-k_decay * i) for i in range(fatigue_incidents)])
    
    trace.append({
        "module": "Fatigue Calculator",
        "title": "Temporal Decay Memory",
        "details": f"Past 30d Incidents: {fatigue_incidents}\nFatigue Score: {fatigue_score:.2f}\nAction Receptiveness heavily penalized."
    })

    # 4. PRESCRIPTIVE OPTIMIZER (Expected Utility Math)
    # Calculate base risk
    base_logit = -3.0 + (0.15 * delay_hours)
    
    # Calculate mathematically adjusted uplifts
    email_uplift = (-0.5 + (0.02 * delay_hours)) * (1 - min(fatigue_score, 0.95)) # Fatigue destroys email effectiveness
    credit_uplift = -1.5
    refund_uplift = -2.8 - (0.05 * delay_hours)

    def get_retain_prob(logit):
        return 1 - (1 / (1 + math.exp(-logit)))

    prob_none = get_retain_prob(base_logit)
    prob_email = get_retain_prob(base_logit + email_uplift)
    prob_credit = get_retain_prob(base_logit + credit_uplift)
    prob_refund = get_retain_prob(base_logit + refund_uplift)

    # Apply CFO Guardian penalty to costs: Cost * (1 + Lambda)
    adj_costs = {k: v * (1 + lambda_penalty) for k, v in costs.items()}

    # Calculate final utility: E[U] = (Retained_Prob * LTV) - Adjusted_Cost
    u_none = (prob_none * ltv) - 0
    u_email = (prob_email * ltv) - adj_costs['email']
    u_credit = (prob_credit * ltv) - adj_costs['credit']
    u_refund = (prob_refund * ltv) - adj_costs['refund']

    # Find mathematically optimal action
    utilities = {'Do Nothing': u_none, 'Apology Email': u_email, '$10 Store Credit': u_credit, 'Full Refund': u_refund}
    best_action = max(utilities, key=utilities.get)

    trace.append({
        "module": "S-Learner Optimizer",
        "title": "Expected Utility Maximization",
        "details": f"Calculated ROI:\nEmail: ${u_email:,.2f} (Cost: ${adj_costs['email']:.2f})\nCredit: ${u_credit:,.2f} (Cost: ${adj_costs['credit']:.2f})\nRefund: ${u_refund:,.2f} (Cost: ${adj_costs['refund']:.2f})",
        "decision": best_action
    })

    return jsonify({"timestamp": datetime.utcnow().isoformat(), "trace": trace})


@app.route('/api/metrics/system-shock', methods=['GET'])
@require_auth
def get_system_shock_index():
    
    now = datetime.utcnow()
    last_hour = now - timedelta(hours=1)
    last_24_hours = now - timedelta(hours=24)

    # Database aggregations
    events_last_hour = Event.query.filter(Event.timestamp >= last_hour).count()
    events_last_24 = Event.query.filter(Event.timestamp >= last_24_hours).count()

    # Calculate Baseline (Avoid division by zero)
    avg_hourly_baseline = (events_last_24 / 24.0) if events_last_24 > 0 else 1.0
    
    # Calculate Shock Ratio (Current velocity vs Baseline)
    shock_ratio = events_last_hour / avg_hourly_baseline

    # Calculate Lambda (λ) Penalty
    # If ratio is <= 1.5, penalty is 0. If it spikes, lambda scales aggressively.
    kappa_aggressiveness = 2.5 
    lambda_penalty = max(0.0, kappa_aggressiveness * (shock_ratio - 1.5))

    return jsonify({
        'timestamp': now.isoformat(),
        'events_last_hour': events_last_hour,
        'avg_hourly_baseline': round(avg_hourly_baseline, 2),
        'shock_ratio': round(shock_ratio, 2),
        'lambda_shadow_price': round(lambda_penalty, 4),
        'system_status': 'CRITICAL' if lambda_penalty > 1.0 else 'NOMINAL'
    })

# ------------------------------------------------------------
# Customer endpoints (With ARCHITECTURE MODULE 2 injected)
# ------------------------------------------------------------
@app.route('/api/customers/<int:customer_id>', methods=['GET'])
@require_auth
def get_customer(customer_id):
    
    customer = Customer.query.get(customer_id)
    if not customer:
        return jsonify({'error': 'Customer not found'}), 404

    # Calculate Temporal Apology Fatigue
    # Math: Sum of exp(-k * delta_t) for all past actions
    past_actions = db.session.query(Action, Event).join(Event).filter(
        Event.customer_id == customer_id,
        Action.status == 'success'
    ).all()

    fatigue_score = 0.0
    k_decay = 0.02 # Decay constant (approx 34 hours half-life)
    now = datetime.utcnow()

    for action, event in past_actions:
        delta_hours = (now - action.executed_at).total_seconds() / 3600.0
        # Exponential decay: recent actions spike the score, old actions fade
        fatigue_score += math.exp(-k_decay * delta_hours)

    return jsonify({
        'id': customer.id,
        'name': customer.name,
        'email': customer.email,
        'tier': customer.tier,
        'ltv_score': customer.ltv_score,
        'communication_preference': customer.communication_preference,
        'realtime_fatigue_index': round(fatigue_score, 4) # Fed directly into decision engine
    })

# ------------------------------------------------------------
# Event endpoints
# ------------------------------------------------------------
@app.route('/api/events', methods=['GET'])
@require_auth
def get_events():
    events = Event.query.order_by(Event.timestamp.desc()).limit(50).all()
    result = []
    for e in events:
        result.append({
            'id': e.id,
            'order_id': e.order_id,
            'customer_id': e.customer_id,
            'event_type': e.event_type,
            'delay_hours': e.delay_hours,
            'severity': e.severity,
            'timestamp': e.timestamp.isoformat(),
            'processed': e.processed,
            'actions': [{'id': a.id, 'type': a.action_type} for a in e.actions]
        })
    return jsonify(result)

@app.route('/api/events', methods=['POST'])
@require_auth
def create_event():
    data = request.get_json()
    required = ['order_id', 'customer_id', 'event_type']
    if not all(k in data for k in required):
        return jsonify({'error': 'Missing required fields'}), 400

    # Verify customer exists
    customer = Customer.query.get(data['customer_id'])
    if not customer:
        return jsonify({'error': 'Customer not found'}), 404

    event = Event(
        order_id=data['order_id'],
        customer_id=data['customer_id'],
        event_type=data['event_type'],
        delay_hours=data.get('delay_hours', 0.0),
        severity=data.get('severity', 'medium'),
        timestamp=datetime.utcnow(),
        processed=False
    )
    db.session.add(event)
    db.session.commit()

    # Trigger decision engine (which will now respect global constraints)
    result = process_event(event.id)

    return jsonify({
        'event_id': event.id,
        'status': 'created and processed',
        'decision': result
    }), 201

# ------------------------------------------------------------
# Rule endpoints (configuration)
# ------------------------------------------------------------
@app.route('/api/rules', methods=['GET'])
@require_auth
def get_rules():
    rules = Rule.query.order_by(Rule.priority).all()
    return jsonify([{
        'id': r.id,
        'name': r.name,
        'priority': r.priority,
        'conditions': r.conditions,
        'action_type': r.action_type,
        'action_params': r.action_params,
        'is_active': r.is_active
    } for r in rules])

@app.route('/api/rules', methods=['POST'])
@require_auth
def create_rule():
    data = request.get_json()
    required = ['name', 'conditions', 'action_type', 'action_params']
    if not all(k in data for k in required):
        return jsonify({'error': 'Missing required fields'}), 400

    rule = Rule(
        name=data['name'],
        priority=data.get('priority', 100),
        conditions=data['conditions'],
        action_type=data['action_type'],
        action_params=data['action_params'],
        is_active=data.get('is_active', True)
    )
    db.session.add(rule)
    db.session.commit()
    return jsonify({'id': rule.id, 'message': 'Rule created'}), 201

@app.route('/api/rules/<int:rule_id>', methods=['PUT'])
@require_auth
def update_rule(rule_id):
    rule = Rule.query.get(rule_id)
    if not rule:
        return jsonify({'error': 'Rule not found'}), 404
    data = request.get_json()
    rule.name = data.get('name', rule.name)
    rule.priority = data.get('priority', rule.priority)
    rule.conditions = data.get('conditions', rule.conditions)
    rule.action_type = data.get('action_type', rule.action_type)
    rule.action_params = data.get('action_params', rule.action_params)
    rule.is_active = data.get('is_active', rule.is_active)
    db.session.commit()
    return jsonify({'message': 'Rule updated'})

# ------------------------------------------------------------
# Audit endpoints
# ------------------------------------------------------------
@app.route('/api/audit', methods=['GET'])
@require_auth
def get_audit():
    logs = AuditLog.query.order_by(AuditLog.id.desc()).limit(100).all()
    return jsonify([{
        'id': l.id,
        'previous_hash': l.previous_hash,
        'timestamp': l.timestamp.isoformat(),
        'data': l.data,
        'hash': l.hash
    } for l in logs])

@app.route('/api/audit/verify', methods=['POST'])
@require_auth
def verify_audit():
    logs = AuditLog.query.order_by(AuditLog.id).all()
    valid = True
    for i, log in enumerate(logs):
        if i == 0:
            expected_prev = '0'*64
        else:
            expected_prev = logs[i-1].hash
        if log.previous_hash != expected_prev:
            valid = False
            break
        computed = AuditLog.compute_hash(log.previous_hash, log.timestamp, log.data)
        if computed != log.hash:
            valid = False
            break
    return jsonify({'valid': valid})

# ------------------------------------------------------------
# Action & Customer Collection endpoints
# ------------------------------------------------------------
@app.route('/api/customers', methods=['GET'])
@require_auth
def get_customers():
    customers = Customer.query.all()
    return jsonify([{
        'id': c.id,
        'name': c.name,
        'email': c.email,
        'tier': c.tier,
        'ltv_score': c.ltv_score,
        'communication_preference': c.communication_preference
    } for c in customers])

@app.route('/api/actions', methods=['GET'])
@require_auth
def get_actions():
    actions = Action.query.order_by(Action.executed_at.desc()).limit(50).all()
    return jsonify([{
        'id': a.id,
        'event_id': a.event_id,
        'rule_id': a.rule_id,
        'action_type': a.action_type,
        'action_params': a.action_params,
        'executed_at': a.executed_at.isoformat(),
        'status': a.status
    } for a in actions])

if __name__ == '__main__':
    app.run(debug=True, port=5000) """
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import pandas as pd
import joblib
import os
import math

app = Flask(__name__)
CORS(app)

# =====================================================================
# REAL ML MODEL INTEGRATION (S-LEARNER)
# =====================================================================
try:
    xgb_model = joblib.load('xgboost_model.pkl')
    tier_encoder = joblib.load('tier_encoder.pkl')
    comm_encoder = joblib.load('comm_encoder.pkl')
    action_encoder = joblib.load('action_encoder.pkl')
    MODELS_LOADED = True
except Exception as e:
    print(f"⚠️ WARNING: ML models not found. Error: {e}")
    MODELS_LOADED = False

# =====================================================================
# FRICTION & GOVERNANCE MODULE (From frictionscore.py)
# =====================================================================
DECISION_RULES = [
    {"risk_level": "High", "customer_tier": "Platinum", "action_type": "refund", "percentage": 0.20},
    {"risk_level": "High", "customer_tier": "Gold", "action_type": "refund", "percentage": 0.15},
    {"risk_level": "Medium", "customer_tier": "Platinum", "action_type": "credit", "percentage": 0.10},
    {"risk_level": "Medium", "customer_tier": "Gold", "action_type": "credit", "percentage": 0.07}
]

def calculate_friction_score(delay_hours, damage_severity, customer_tier, past_complaints):
    delay_score = min(delay_hours * 10, 100)
    damage_score = min(damage_severity * 10, 100)
    tier_mapping = {"Platinum": 100, "Gold": 70, "Silver": 40, "Bronze": 20}
    tier_score = tier_mapping.get(customer_tier, 40)
    complaint_score = min(past_complaints * 10, 100)
    
    friction_score = (delay_score * 0.4 + damage_score * 0.2 + tier_score * 0.2 + complaint_score * 0.2)
    return round(friction_score, 2)

def evaluate_decision(risk_level, customer_tier, order_value):
    for rule in DECISION_RULES:
        if rule["risk_level"] == risk_level and rule["customer_tier"] == customer_tier:
            return {"action_type": rule["action_type"], "amount": round(order_value * rule["percentage"], 2)}
    return {"action_type": "monitor", "amount": 0}

def apply_governance(action, customer_tier):
    amount = action["amount"]
    approval_required, approver_role = False, None
    if amount <= 500:
        approver_role = "Auto-Approved (System)"
    elif 500 < amount <= 2000:
        approver_role, approval_required = "CX_Manager", True
    elif amount > 2000:
        approver_role, approval_required = "Finance_Head", True

    if customer_tier == "Platinum" and action["action_type"] == "refund":
        approver_role, approval_required = "Regional_Director", True

    action.update({"approval_required": approval_required, "approver_role": approver_role})
    return action

# =====================================================================
# API ENDPOINT
# =====================================================================
@app.route('/api/simulate-scenario', methods=['POST'])
def simulate_scenario():
    data = request.get_json()
    scenario_id = data.get('scenario_id', 1)
    costs = {'do_nothing': 0.0, 'email': 0.10, 'credit': 10.0, 'refund': 15.0}

    # Parameters
    if scenario_id == 1:
        features = {'ltv': 4500.0, 'delay_hours': 12.0, 'shock_ratio': 1.0, 'fatigue': 0, 'tier': 'Platinum', 'damage': 5}
    elif scenario_id == 2:
        features = {'ltv': 800.0, 'delay_hours': 48.0, 'shock_ratio': 8.5, 'fatigue': 0, 'tier': 'Silver', 'damage': 8}
    else:
        # Fraud Suspicion: Low LTV, Minor Delay, but MASSIVE fatigue (past issues)
        features = {'ltv': 150.0, 'delay_hours': 2.0, 'shock_ratio': 1.0, 'fatigue': 8, 'tier': 'Bronze', 'damage': 0}

    trace = []

    # 1. INGESTION
    trace.append({
        "module": "Context Ingestion",
        "title": "SAP Logistics Data",
        "params": "Tier, LTV, Delay, Damage Severity",
        "details": f"Tier: {features['tier']}\nLTV: ${features['ltv']:,.2f}\nDelay: {features['delay_hours']}h\nDamage Level: {features['damage']}/10"
    })

    # 2. VOLATILITY ENGINE
    lambda_penalty = max(0.0, 2.5 * (features['shock_ratio'] - 1.5))
    trace.append({
        "module": "Volatility Engine",
        "title": "CFO Guardian",
        "params": "Live Event Velocity vs Baseline",
        "details": f"Global Velocity: {features['shock_ratio']}x\nStatus: {'CRITICAL' if lambda_penalty>0 else 'NOMINAL'}\nShadow Price (λ): {lambda_penalty:.2f}x penalty."
    })

    # 3. FATIGUE CALCULATOR
    fatigue_score = sum([math.exp(-0.8 * i) for i in range(features['fatigue'])])
    trace.append({
        "module": "Fatigue Ledger",
        "title": "Temporal Decay Memory",
        "params": "Past 30d Support Tickets",
        "details": f"Past Incidents: {features['fatigue']}\nCalculated Score: {fatigue_score:.2f}\nMath: Exponential Half-life decay."
    })

    # 4. FRICTION RISK CLASSIFIER (Newly added logic)
    f_score = calculate_friction_score(features['delay_hours'], features['damage'], features['tier'], features['fatigue'])
    risk_level = "High" if f_score >= 70 else "Medium" if f_score >= 40 else "Low"
    gov_decision = apply_governance(evaluate_decision(risk_level, features['tier'], features['ltv']), features['tier'])
    
    # FRAUD OVERRIDE: If they have absurdly high past issues, Governance locks it down.
    if features['fatigue'] >= 5:
        risk_level = "CRITICAL (FRAUD SUSPICION)"
        gov_decision['action_type'] = "halt auto-approvals"
        gov_decision['amount'] = 0.0
        gov_decision['approver_role'] = "Fraud_Resolution_Team"
    
    trace.append({
        "module": "Risk Governance",
        "title": "Friction Classifier",
        "params": "Friction Math & Approval Matrix",
        "details": f"Friction Score: {f_score}/100\nRisk Level: {risk_level}\nHardcoded Rule: {gov_decision['action_type'].title()} up to ${gov_decision['amount']}\nRequired Approver: {gov_decision['approver_role']}"
    })

    # 5. S-LEARNER OPTIMIZER
    adj_costs = {k: v * (1 + lambda_penalty) for k, v in costs.items()}
    utilities, details_str = {}, ""
    
    if MODELS_LOADED:
        for action_str in ['do_nothing', 'email', 'credit', 'refund']:
            try:
                t_enc = tier_encoder.transform([features['tier']])[0]
                c_enc = comm_encoder.transform(['email'])[0]
                a_enc = action_encoder.transform([action_str])[0] if action_str in action_encoder.classes_ else 0

                X_causal = pd.DataFrame([{'tier_encoded': t_enc, 'delay_hours': features['delay_hours'], 'past_issues': features['fatigue'], 'order_value': features['ltv'], 'customer_tenure_months': 24, 'comm_encoded': c_enc, 'action_encoded': a_enc}])
                retention_prob = 1.0 - xgb_model.predict_proba(X_causal)[0][1]
                expected_utility = (retention_prob * features['ltv']) - adj_costs[action_str]
                utilities[action_str] = expected_utility
                details_str += f"{action_str.title()}: E[U] = ${expected_utility:,.2f} ({retention_prob:.1%})\n"
            except: utilities[action_str] = -999
    else:
        details_str = "ML Loaded Fake Data"
        utilities = {'do_nothing': 100, 'email': 200, 'credit': 300, 'refund': 400}

    best_action_key = max(utilities, key=utilities.get)
    # Renamed 'do_nothing' to 'Claim Denied / Manual Review' for the UI
    display_actions = {'do_nothing': 'Claim Denied / Manual Review', 'email': 'Apology Email', 'credit': '$10 Store Credit', 'refund': 'Full Refund'}

    trace.append({
        "module": "S-Learner Optimizer",
        "title": "Expected Utility Math",
        "params": "Causal Inference via XGBoost",
        "details": details_str.strip(),
        "decision": display_actions.get(best_action_key, best_action_key.title())
    })

    return jsonify({"timestamp": datetime.utcnow().isoformat(), "trace": trace})

if __name__ == '__main__':
    app.run(debug=True, port=5000)