"""Legacy launcher for the Flask application.

This script preserves the previous entry point name used by packaging
tools while delegating execution to the Flask app defined in
``flask_app.py``.
"""

from flask_app import app


if __name__ == "__main__":
    app.run()

