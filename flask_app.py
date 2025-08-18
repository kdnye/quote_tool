from flask import Flask
from routes.auth import auth_bp
from routes.quote import quote_bp
from routes.admin import admin_bp


def create_app():
    app = Flask(__name__)
    app.secret_key = 'change-me'
    app.register_blueprint(auth_bp)
    app.register_blueprint(quote_bp)
    app.register_blueprint(admin_bp)
    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
