from flask import Flask, current_app, request, session, abort
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, user_logged_in, user_logged_out, user_loaded_from_request, current_user
from flask_wtf.csrf import CSRFProtect, CSRFError
from app.main import main_bp, get_rank_suffix
from app.auth import auth_bp
from app.admin import admin_bp
from app.utils import custom_url_for  # Import from utils

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
    app.config['SESSION_COOKIE_DOMAIN'] = False

    from app.models import db

    # Initialize database and migration
    migrate = Migrate(app, db)

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)

    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.judges_login"
    login_manager.login_message_category = "warning"
    login_manager.session_protection = "strong"  # Enforce stronger session protection
    
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User  # Local import to avoid circular dependency
        return User.query.get(int(user_id))


    @app.after_request
    def add_cache_control_headers(response):
        if 'no-store' not in response.headers.get('Cache-Control', ''):
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
            response.headers['Pragma'] = 'no-cache'
        return response


    # Assign the custom_url_for to Jinja's global context
    app.jinja_env.globals['url_for'] = custom_url_for

    # Make custom_url_for available for import
    app.custom_url_for = custom_url_for

    app.jinja_env.globals['get_rank_suffix'] = get_rank_suffix

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    return app