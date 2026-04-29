"""
Application entry point.

Creates the Flask app via the app factory and runs the development server.
For production, use: gunicorn "app:create_app()" --bind 0.0.0.0:5000
"""

import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from app import create_app

app = create_app()

if __name__ == "__main__":
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"

    app.run(host=host, port=port, debug=debug)
