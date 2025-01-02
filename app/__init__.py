from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, user_logged_in, user_logged_out, user_loaded_from_request, current_user
import os
import toml

# Load config
config = toml.load("config.toml")

# Initialize app
app = Flask(__name__, static_folder="static", static_url_path="/static")
app.config["SQLALCHEMY_DATABASE_URI"] = config["flask"]["SQLALCHEMY_DATABASE_URI"]
app.config["SECRET_KEY"] = config["flask"]["SECRET_KEY"]
app.config["UPLOAD_FOLDER"] = config["submissions"]["UPLOAD_FOLDER"]
app.config["APPLICATION_ROOT"] = config["flask"]["APPLICATION_ROOT"]
app.config['SESSION_COOKIE_SECURE'] = config["flask"]["SESSION_COOKIE_SECURE"]
app.config['SESSION_COOKIE_HTTPONLY'] = config["flask"]["SESSION_COOKIE_HTTPONLY"]
app.config['SESSION_COOKIE_SAMESITE'] = config["flask"]["SESSION_COOKIE_SAMESITE"]


# Create Folders
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Database and Migrations
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "judges_password"
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "warning"

@login_manager.user_loader
def load_user(user_id):
    from app.models import Judge
    try:
        user = Judge.query.get(int(user_id))
        if user:
            app.logger.debug(f"Loaded user: {user.name}, is_admin: {user.is_admin}")
        else:
            app.logger.warning(f"User with ID {user_id} not found.")
        return user
    except ValueError:
        app.logger.error(f"Invalid user ID: {user_id}")
    except Exception as e:
        app.logger.error(f"Error in load_user: {e}")
    return None

# Import custom_url_for from utils
from app.utils import custom_url_for

# Assign custom_url_for to Jinja global context
app.jinja_env.globals['url_for'] = custom_url_for

# Import routes and models AFTER db is initialized
from app import routes, models
