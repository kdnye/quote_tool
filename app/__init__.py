# app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from .models import db, User

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "info"
csrf = CSRFProtect()

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def create_app(config_class="config.Config"):
    app = Flask(__name__, template_folder="../templates")
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Blueprints
    from .auth import auth_bp
    from .admin import admin_bp
    from .quotes import quotes_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(quotes_bp, url_prefix="/quotes")

    # Admin API handles CSRF via custom header checks
    csrf.exempt(admin_bp)

    @app.route("/")
    def index():
        return "Quote Tool is running"

    return app
