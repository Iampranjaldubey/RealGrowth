
"""Application configuration."""

import os


class Config:
    """Base application configuration."""

    # Absolute path to the backend directory
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    # Absolute path to the CSV data directory
    DATA_DIR = os.path.join(BASE_DIR, "data")

    # CORS configuration
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")

    # Application mode
    DEBUG = False


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG = False

    # Set this environment variable in Docker/production
    # Example:
    # CORS_ORIGINS=https://your-frontend-domain.com
    CORS_ORIGINS = os.environ.get(
        "CORS_ORIGINS",
        "*"
    )


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}

