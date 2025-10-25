import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app():
    # ✅ 현재 디렉토리 기준으로 templates 경로 지정
    app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), '../templates'))

    database_url = os.getenv("DATABASE_URL")
    if database_url and database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.secret_key = os.getenv("SECRET_KEY", "studyroom-secret-key")

    db.init_app(app)

    with app.app_context():
        from db import models
        db.create_all()

    return app
