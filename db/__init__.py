import os
from flask import Flask, send_from_directory
from flask_sqlalchemy import SQLAlchemy

# ✅ SQLAlchemy 인스턴스 생성
db = SQLAlchemy()

def create_app():
    """Flask 앱 생성 및 DB 초기화"""
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    app = Flask(
        __name__,
        template_folder=os.path.join(BASE_DIR, 'templates'),
        static_folder=os.path.join(BASE_DIR, 'static'),
        static_url_path='/static'
    )

    # ✅ Railway 환경변수 불러오기
    database_url = os.getenv("DATABASE_URL")
    if database_url and database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    if not database_url:
        instance_dir = os.path.join(BASE_DIR, "instance")
        os.makedirs(instance_dir, exist_ok=True)
        database_url = f"sqlite:///{os.path.join(instance_dir, 'app.db')}"

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.secret_key = os.getenv("SECRET_KEY", "studyroom-secret-key")

    db.init_app(app)

    # ✅ import db.models → models.db 로 접근
    with app.app_context():
        from db import models
        models.db.create_all()
        print("✅ DB 테이블 생성 완료")

    # ✅ 정적 파일 직접 제공 (Railway PNG/CSS 깨짐 방지)
    @app.route('/static/<path:filename>')
    def static_files(filename):
        static_dir = os.path.join(BASE_DIR, 'static')
        return send_from_directory(static_dir, filename)

    return app
