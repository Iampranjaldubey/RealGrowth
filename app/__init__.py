"""
Flask Application Factory.

Creates and configures the Flask app, registers blueprints,
initializes the data service, and sets up error handlers.
"""

import os
import logging

from flask import Flask
from flask_cors import CORS

from app.config import config_by_name
from app.errors import register_error_handlers
from app.services.data_service import DataService


def create_app(config_name=None):
    """
    Create and configure the Flask application.

    Args:
        config_name: One of 'development', 'production', or 'default'.
                     Falls back to FLASK_ENV environment variable.

    Returns:
        Configured Flask app instance.
    """
    # Determine configuration
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "default")

    app = Flask(
        __name__,
        static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), "static"),
        template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"),
    )

    # Load configuration
    app.config.from_object(config_by_name.get(config_name, config_by_name["default"]))

    # Set up logging
    logging.basicConfig(
        level=logging.DEBUG if app.config["DEBUG"] else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger = logging.getLogger(__name__)
    logger.info(f"Creating app with '{config_name}' configuration")

    # Enable CORS
    CORS(app, origins=app.config.get("CORS_ORIGINS", "*"))

    # Initialize the data service (single instance for the app lifecycle)
    data_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        app.config["DATA_DIR"],
    )
    app.config["DATA_SERVICE"] = DataService(data_dir)

    # Register error handlers
    register_error_handlers(app)

    # Register API v1 blueprint
    from app.routes.api import api_v1
    app.register_blueprint(api_v1)

    # Register page-serving routes
    _register_page_routes(app)

    logger.info("Application ready")
    return app


def _register_page_routes(app):
    """Register routes that serve Jinja2 HTML templates."""
    from flask import render_template

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/gdp")
    def page_gdp():
        return render_template("gdp.html")

    @app.route("/inflation")
    def page_inflation():
        return render_template("inflation.html")

    @app.route("/food")
    def page_food():
        return render_template("food.html")

    @app.route("/population")
    def page_population():
        return render_template("population.html")

    @app.route("/wages")
    def page_wages():
        return render_template("wages.html")

    @app.route("/debt")
    def page_debt():
        return render_template("debt.html")

    @app.route("/growth")
    def page_growth():
        return render_template("growth.html")
