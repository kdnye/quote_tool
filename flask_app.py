from flask import Flask
from flask_login import LoginManager
from routes.auth import auth_bp
from routes.quote import quote_bp
from routes.admin import admin_bp
from db import Session, User


def create_app():
    app = Flask(__name__)
    app.secret_key = "change-me"
    app.register_blueprint(auth_bp)
    app.register_blueprint(quote_bp)
    app.register_blueprint(admin_bp)

    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        db = Session()
        user = db.get(User, int(user_id))
        db.close()
        return user

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
