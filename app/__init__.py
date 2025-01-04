from flask import Flask, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, user_logged_in, user_logged_out, user_loaded_from_request, current_user
from flask_wtf.csrf import CSRFProtect,CSRFError, generate_csrf
from app.main import main_bp

import os
import toml

# Load configuration
config = toml.load("config.toml")

csrf = CSRFProtect()


def create_app():
    app = Flask(__name__, static_folder="static", static_url_path="/static")
    app.config["SQLALCHEMY_DATABASE_URI"] = config["flask"]["SQLALCHEMY_DATABASE_URI"]
    app.config["SECRET_KEY"] = config["flask"]["SECRET_KEY"]
    app.config["UPLOAD_FOLDER"] = config["submissions"]["UPLOAD_FOLDER"]
    app.config["APPLICATION_ROOT"] = config["flask"]["APPLICATION_ROOT"]
    app.config['SESSION_COOKIE_SECURE'] = False
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    
    from app.models import db

    # Initialize database and migration
    migrate = Migrate(app, db)

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    app.register_blueprint(main_bp)

    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "main.judges_password"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "warning"
    login_manager.session_protection = "strong"

    @login_manager.user_loader
    def load_user(user_id):
        from app.models import Judge  # Local import to avoid circular dependency
        return Judge.query.get(int(user_id))

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        # Flash an error message
        flash('Your session expired or the CSRF token is invalid. Please try again.', 'warning')
        
        # Regenerate a new CSRF token
        session['csrf_token'] = generate_csrf()

        # Redirect to the previous page or fallback to home
        next_url = request.referrer or url_for('main.index')
        return redirect(next_url)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    return app