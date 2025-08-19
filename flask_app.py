"""Flask application factory.

This version uses the raw SQLAlchemy models from ``db.py`` and the
blueprints defined under the ``routes`` package."""
from flask import Flask
from flask_login import LoginManager

from config import Config
from db import Session, User
from routes.auth import auth_bp
from routes.quote import quote_bp
from routes.admin import admin_bp

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "info"


@login_manager.user_loader
def load_user(user_id: str):
    """Return a user instance for Flask-Login."""
    with Session() as session:
        return session.get(User, int(user_id))


def create_app(config_class: type[Config] = Config) -> Flask:
    """Application factory used by tests and ``__main__``."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    login_manager.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(quote_bp)
    app.register_blueprint(admin_bp)

    return app


app = create_app()

if __name__ == "__main__":  # pragma: no cover - manual run helper
    app.run(debug=True, host="0.0.0.0", port=5000)
