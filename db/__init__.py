import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)

    # ✅ 환경변수에서 DB URL 불러오기
    database_url = os.getenv("DATABASE_URL")
    if database_url and database_url.startswith("postgres://"):
        # 🩵 Railway는 postgres://로 시작하지만, SQLAlchemy는 postgresql://를 요구함
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.secret_key = os.getenv("SECRET_KEY", "studyroom-secret-key")

    db.init_app(app)

    # ✅ 테이블 생성
    with app.app_context():
        from db import models
        db.create_all()

    return app
