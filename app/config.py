"""
Application configuration classes.
Loads settings from environment variables via python-dotenv.
"""

import os


class Config:
    """Base configuration with defaults."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    DATA_DIR = os.environ.get("DATA_DIR", "data")
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")

    # Flask settings
    DEBUG = False
    TESTING = False


class DevelopmentConfig(Config):
    """Development configuration — debug mode enabled."""

    DEBUG = True


class ProductionConfig(Config):
    """Production configuration — debug off, strict settings."""

    DEBUG = False


# Map string names to config classes for easy lookup
config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
