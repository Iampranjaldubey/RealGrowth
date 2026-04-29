"""
Structured error handlers for the Flask application.
Returns consistent JSON error responses for all HTTP error codes.
"""

from flask import jsonify


def register_error_handlers(app):
    """Register JSON error handlers on the Flask app."""

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            "status": "error",
            "message": str(error.description) if hasattr(error, "description") else "Bad request"
        }), 400

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            "status": "error",
            "message": "The requested resource was not found"
        }), 404

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f"Internal server error: {error}")
        return jsonify({
            "status": "error",
            "message": "An internal server error occurred"
        }), 500
