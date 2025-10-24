import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app():
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))     # .../db
    PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, '..'))  # 프로젝트 루트
    DB_PATH = os.path.join(PROJECT_ROOT, 'studyroom.db')      # 로컬 개발용 SQLite 경로

    app = Flask(__name__,
        static_folder=os.path.join(PROJECT_ROOT, 'static'),
        template_folder=os.path.join(PROJECT_ROOT, 'templates'))

    app.secret_key = "supersecretkey"   # ✅ flash(), session 등에 필수

    # ✅ PostgreSQL 우선, 없으면 로컬 SQLite 사용
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{DB_PATH}"
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    # 모델 import
    from . import models

    # ✅ DB 자동 초기화 (PostgreSQL/SQLite 모두)
    with app.app_context():
        try:
            db.create_all()
            print("✅ 데이터베이스 연결 및 테이블 확인 완료")
        except Exception as e:
            print("❌ 데이터베이스 초기화 중 오류:", e)

    return app
