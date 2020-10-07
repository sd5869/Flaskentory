import os

import psycopg2
from flask import Flask, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from wtforms import Form, validators

app = Flask(__name__)
app.config["demo"] = os.environ.get("IS_DEMO", True)
app.config["is_production"] = os.environ.get("IS_PRODUCTION", False)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "0012345679")
app.config["GA_TRACKING_ID"] = os.environ.get("GA_TRACKING_ID", None)

# set bootswatch theme
app.config["FLASK_ADMIN_SWATCH"] = os.environ.get(
    "FLASK_ADMIN_SWATCH", "lumen"
)  #'lumen' 'paper'

# db config
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "postgresql://flaskentory:flaskentory@localhost/flaskentory"
)
app.config["SQLALCHEMY_ECHO"] = not (app.config["is_production"])
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True
db = SQLAlchemy(app)
engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])


@app.route("/favicon.ico")
def favicon():
    return redirect(url_for("static", filename="favicon.ico"))
