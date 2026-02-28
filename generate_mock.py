from app import app
from models import db, Customer, Rule
import random

def generate_mock_data():
    with app.app_context():
        # Clear existing data (optional)
        db.drop_all()
        db.create_all()

        # Customers
        customers = [
            Customer(name='Alice Johnson', email='alice@example.com', tier='Platinum', ltv_score=12500.0, communication_preference='email'),
            Customer(name='Bob Smith', email='bob@example.com', tier='Gold', ltv_score=5400.0, communication_preference='sms'),
            Customer(name='Charlie Brown', email='charlie@example.com', tier='Silver', ltv_score=2300.0, communication_preference='email'),
            Customer(name='Diana Prince', email='diana@example.com', tier='Platinum', ltv_score=22000.0, communication_preference='email'),
            Customer(name='Evan Wright', email='evan@example.com', tier='Gold', ltv_score=6700.0, communication_preference='sms'),
        ]
        db.session.add_all(customers)
        db.session.commit()

        # Rules
        rules = [
            Rule(
                name='Platinum delay > 1h → $10 credit',
                priority=10,
                conditions={"delay_hours >": 1, "customer_tier": "Platinum"},
                action_type='credit',
                action_params={"amount": 10, "channel": "email", "message": "Sorry for the delay, here's $10 credit!"}
            ),
            Rule(
                name='Gold delay > 2h → notify only',
                priority=20,
                conditions={"delay_hours >": 2, "customer_tier": "Gold"},
                action_type='notify',
                action_params={"channel": "email", "message": "Your order is delayed, but it's on its way!"}
            ),
            Rule(
                name='Any delay > 3h → $5 credit for Silver',
                priority=30,
                conditions={"delay_hours >": 3, "customer_tier": "Silver"},
                action_type='credit',
                action_params={"amount": 5, "channel": "email"}
            ),
            Rule(
                name='Severe delay (5h+) any tier → refund shipping',
                priority=5,
                conditions={"delay_hours >": 5},
                action_type='refund',
                action_params={"amount": "shipping", "channel": "email"}
            ),
        ]
        db.session.add_all(rules)
        db.session.commit()

        print("Mock data generated successfully!")

if __name__ == '__main__':
    generate_mock_data()