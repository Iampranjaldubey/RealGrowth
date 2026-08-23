"""Application configuration."""
import os


class Config:
    """Base configuration."""
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*')
    DEBUG = False


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'https://yourdomain.com')


config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
