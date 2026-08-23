"""
RealGrowth API — Flask Application Factory.

Global Economic Data Dashboard backend with modular Blueprint architecture.
"""
import os
import logging
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
from flask_talisman import Talisman
from flask_compress import Compress
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Load environment variables from .env file
load_dotenv()

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app(config_name=None):
    """Create and configure the Flask application."""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)
    
    # Import config here to avoid circular imports if config ever depends on app
    from config import config_by_name
    app.config.from_object(config_by_name.get(config_name, config_by_name['default']))

    # Initialize production extensions
    # 1. CORS
    CORS(app, origins=app.config.get('CORS_ORIGINS', '*'))
    
    # 2. Content Compression (Gzip/Brotli)
    Compress(app)
    
    # 3. Security Headers (Talisman)
    # Allow inline scripts/styles for Swagger or basic debugging if needed, but strict for production
    csp = {
        'default-src': [
            '\'self\'',
        ]
    }
    # In development, we might not want to enforce HTTPS
    force_https = app.config.get('ENV') == 'production'
    Talisman(app, content_security_policy=csp, force_https=force_https)
    
    # 4. Rate Limiting
    # Using memory storage for simplicity; in prod, Redis is recommended
    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=["200 per day", "50 per hour"],
        storage_uri="memory://"
    )

    # Register Blueprints
    from api.gdp import gdp_bp
    from api.inflation import inflation_bp
    from api.food import food_bp
    from api.population import population_bp
    from api.wages import wages_bp
    from api.debt import debt_bp
    from api.growth import growth_bp
    from api.correlation import correlation_bp

    app.register_blueprint(gdp_bp)
    app.register_blueprint(inflation_bp)
    app.register_blueprint(food_bp)
    app.register_blueprint(population_bp)
    app.register_blueprint(wages_bp)
    app.register_blueprint(debt_bp)
    app.register_blueprint(growth_bp)
    app.register_blueprint(correlation_bp)

    # Health check / root endpoint
    @app.route('/')
    @limiter.exempt  # Health checks shouldn't be strictly rate-limited
    def health_check():
        return jsonify({
            'status': 'running',
            'name': 'RealGrowth API',
            'version': '2.0.0',
            'environment': config_name
        })

    # Global error handlers
    @app.errorhandler(404)
    def not_found(error):
        logger.warning(f"404 Not Found: {request.url}")
        return jsonify({'error': 'Endpoint not found', 'status': 404}), 404
        
    @app.errorhandler(429)
    def ratelimit_handler(e):
        logger.warning(f"Rate limit exceeded: {request.remote_addr}")
        return jsonify({'error': f'Rate limit exceeded {e.description}', 'status': 429}), 429

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"500 Internal Error: {error}")
        return jsonify({'error': 'Internal server error', 'status': 500}), 500

    logger.info(f"RealGrowth API started in {config_name} mode.")
    return app

# Expose global app object for Vercel and WSGI servers
app = create_app(os.environ.get('FLASK_ENV', 'production'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
