import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///ghost.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Mock API keys for external services (optional)
    MOCK_CRM_API_KEY = 'mock-crm-key'
    MOCK_LOGISTICS_API_KEY = 'mock-logistics-key'