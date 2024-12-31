from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

import os
import toml

# Load config
config = toml.load("config.toml")

# Initialize app
app = Flask(__name__, static_folder="static")
app.config["SQLALCHEMY_DATABASE_URI"] = config["flask"]["SQLALCHEMY_DATABASE_URI"]
app.config["SECRET_KEY"] = config["flask"]["SECRET_KEY"]
app.config["UPLOAD_FOLDER"] = config["submissions"]["UPLOAD_FOLDER"]


# Create Folders
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Database and Migrations
db = SQLAlchemy(app)
migrate = Migrate(app, db)

from app import routes, models
