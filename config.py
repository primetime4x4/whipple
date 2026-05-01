"""Env loading + paths."""
import os
from pathlib import Path

DATA_DIR = Path(os.getenv('WHIPPLE_DATA_DIR', '/app/data'))
DB_PATH = DATA_DIR / 'whipple.db'
BULLETINS_DIR = DATA_DIR / 'bulletins'
LOGS_DIR = DATA_DIR / 'logs'

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
GMAIL_CLIENT_ID = os.getenv('GMAIL_CLIENT_ID', '')
GMAIL_CLIENT_SECRET = os.getenv('GMAIL_CLIENT_SECRET', '')
GMAIL_REFRESH_TOKEN = os.getenv('GMAIL_REFRESH_TOKEN', '')
RECIPIENT_EMAIL = os.getenv('RECIPIENT_EMAIL', 'dillonl@gmail.com')

MANUAL_TRIGGER_PHRASE = os.getenv('MANUAL_TRIGGER_PHRASE', 'BREW IT NOW')

CORTEX_BASE_URL = os.getenv('CORTEX_BASE_URL', '')
CORTEX_API_KEY = os.getenv('CORTEX_API_KEY', '')

SECRET_KEY = os.getenv('SECRET_KEY', 'dev-only-change-in-prod')

PORT = int(os.getenv('PORT', '28813'))

# Per-section quotas for select() stage
SECTION_QUOTAS = {
    'energy_prices': 10,
    'geopolitical': 10,
    'climate': 7,
    'global_economy': 7,
    'renewables': 7,
    'briefs': 25,
}
SECTION_DISPLAY = {
    'energy_prices': 'Energy prices and production',
    'geopolitical': 'Geopolitical instability',
    'climate': 'Climate change',
    'global_economy': 'The global economy',
    'renewables': 'Renewables and new technologies',
    'briefs': 'The Briefs',
}

# Rate limits
GEMINI_RPM_LIMIT = 14  # margin under 15
GEMINI_RPD_LIMIT = 1450  # margin under 1500
