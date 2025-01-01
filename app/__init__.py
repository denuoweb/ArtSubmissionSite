from flask import Flask, url_for as flask_url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

import os
import toml

# Load config
config = toml.load("config.toml")

# Initialize app
app = Flask(__name__, static_folder="static", static_url_path="/static")
app.config["SQLALCHEMY_DATABASE_URI"] = config["flask"]["SQLALCHEMY_DATABASE_URI"]
app.config["SECRET_KEY"] = config["flask"]["SECRET_KEY"]
app.config["UPLOAD_FOLDER"] = config["submissions"]["UPLOAD_FOLDER"]
app.config["APPLICATION_ROOT"] = "/badge_contest"

# Create Folders
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Database and Migrations
db = SQLAlchemy(app)
migrate = Migrate(app, db)

def custom_url_for(endpoint, **values):
    """Custom url_for that prepends APPLICATION_ROOT."""
    application_root = app.config.get("APPLICATION_ROOT", "")
    original_url = flask_url_for(endpoint, **values)

    # Only prepend APPLICATION_ROOT if it's not already in the URL
    if not original_url.startswith(application_root):
        return f"{application_root}{original_url}"

    return original_url

# Assign the custom_url_for to Jinja's global context
app.jinja_env.globals['url_for'] = custom_url_for

# Make custom_url_for available for import
app.custom_url_for = custom_url_for

from app import routes, models
