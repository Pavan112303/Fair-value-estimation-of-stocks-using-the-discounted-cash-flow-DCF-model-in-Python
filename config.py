"""
Configuration file for DCF Stock Valuation Tool
"""

import os

class Config:
    """Base configuration class"""
    
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dcf-valuation-tool-secret-key-2024'
    DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'
    
    # DCF Model parameters
    DEFAULT_RISK_FREE_RATE = 0.04  # 4%
    DEFAULT_MARKET_RISK_PREMIUM = 0.06  # 6%
    DEFAULT_TERMINAL_GROWTH_RATE = 0.025  # 2.5%
    DEFAULT_TAX_RATE = 0.25  # 25%
    
    # Analysis parameters
    DEFAULT_PROJECTION_YEARS = 5
    MAX_PROJECTION_YEARS = 10
    MIN_PROJECTION_YEARS = 3
    
    # Chart configuration
    CHART_COLORS = [
        '#2c3e50',  # Primary
        '#3498db',  # Secondary
        '#27ae60',  # Success
        '#f39c12',  # Warning
        '#e74c3c',  # Danger
        '#9b59b6',  # Purple
        '#1abc9c',  # Teal
        '#34495e'   # Dark
    ]
    
    # API configuration
    YAHOO_FINANCE_TIMEOUT = 30  # seconds
    MAX_RETRIES = 3
    
    # Popular stocks for quick selection
    POPULAR_STOCKS = [
        {'ticker': 'AAPL', 'name': 'Apple Inc.', 'sector': 'Technology'},
        {'ticker': 'MSFT', 'name': 'Microsoft Corporation', 'sector': 'Technology'},
        {'ticker': 'GOOGL', 'name': 'Alphabet Inc.', 'sector': 'Technology'},
        {'ticker': 'AMZN', 'name': 'Amazon.com Inc.', 'sector': 'Consumer Discretionary'},
        {'ticker': 'TSLA', 'name': 'Tesla Inc.', 'sector': 'Consumer Discretionary'},
        {'ticker': 'META', 'name': 'Meta Platforms Inc.', 'sector': 'Technology'},
        {'ticker': 'NVDA', 'name': 'NVIDIA Corporation', 'sector': 'Technology'},
        {'ticker': 'JPM', 'name': 'JPMorgan Chase & Co.', 'sector': 'Financial Services'},
        {'ticker': 'JNJ', 'name': 'Johnson & Johnson', 'sector': 'Healthcare'},
        {'ticker': 'V', 'name': 'Visa Inc.', 'sector': 'Financial Services'},
        {'ticker': 'PG', 'name': 'Procter & Gamble Co.', 'sector': 'Consumer Staples'},
        {'ticker': 'UNH', 'name': 'UnitedHealth Group Inc.', 'sector': 'Healthcare'},
        {'ticker': 'HD', 'name': 'Home Depot Inc.', 'sector': 'Consumer Discretionary'},
        {'ticker': 'MA', 'name': 'Mastercard Inc.', 'sector': 'Financial Services'},
        {'ticker': 'DIS', 'name': 'Walt Disney Co.', 'sector': 'Communication Services'}
    ]
    
    # Growth rate templates
    GROWTH_RATE_TEMPLATES = {
        'conservative': [0.05, 0.04, 0.03, 0.025, 0.02],
        'moderate': [0.08, 0.07, 0.06, 0.05, 0.04],
        'aggressive': [0.12, 0.10, 0.08, 0.06, 0.05],
        'declining': [0.10, 0.08, 0.06, 0.04, 0.02]
    }
    
    # Sensitivity analysis parameters
    SENSITIVITY_WACC_RANGE = (0.08, 0.15)
    SENSITIVITY_GROWTH_RANGE = (0.02, 0.08)
    SENSITIVITY_STEPS = 5

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'production-secret-key-change-this'

class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
