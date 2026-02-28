from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import hashlib
import json

db = SQLAlchemy()

class Customer(db.Model):
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    tier = db.Column(db.String(20), nullable=False)  # Platinum, Gold, Silver
    ltv_score = db.Column(db.Float, default=0.0)  # lifetime value
    communication_preference = db.Column(db.String(20), default='email')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Event(db.Model):
    __tablename__ = 'events'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(50), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    event_type = db.Column(db.String(50))  # e.g., 'delay', 'damage', 'misroute'
    delay_hours = db.Column(db.Float, default=0.0)
    severity = db.Column(db.String(20))  # low, medium, high
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    processed = db.Column(db.Boolean, default=False)

    customer = db.relationship('Customer', backref='events')

class Rule(db.Model):
    __tablename__ = 'rules'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    priority = db.Column(db.Integer, default=100)  # lower number = higher priority
    # Conditions stored as JSON: e.g. {"delay_hours >": 2, "customer_tier": "Platinum"}
    conditions = db.Column(db.JSON, nullable=False)
    action_type = db.Column(db.String(50), nullable=False)  # 'refund', 'credit', 'notify'
    action_params = db.Column(db.JSON, nullable=False)  # e.g. {"amount": 10, "channel": "email"}
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Action(db.Model):
    __tablename__ = 'actions'
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    rule_id = db.Column(db.Integer, db.ForeignKey('rules.id'), nullable=True)
    action_type = db.Column(db.String(50))
    action_params = db.Column(db.JSON)
    executed_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='success')  # success, failed, pending

    event = db.relationship('Event', backref='actions')
    rule = db.relationship('Rule')

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    previous_hash = db.Column(db.String(64), nullable=False, default='0'*64)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    data = db.Column(db.JSON, nullable=False)  # stores the full record (event, decision, action)
    hash = db.Column(db.String(64), unique=True, nullable=False)

    @staticmethod
    def compute_hash(previous_hash, timestamp, data):
        content = f"{previous_hash}{timestamp.isoformat()}{json.dumps(data, sort_keys=True)}".encode('utf-8')
        return hashlib.sha256(content).hexdigest()