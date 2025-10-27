import os
from flask import Flask, send_from_directory
from flask_sqlalchemy import SQLAlchemy

# ✅ 전역으로 db 선언
db = SQLAlchemy()

def create_app():
    """Flask 앱 및 DB 초기화"""
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    # ✅ Flask 앱 생성 (템플릿/정적 경로 설정)
    app = Flask(
        __name__,
        template_folder=os.path.join(BASE_DIR, 'templates'),
        static_folder=os.path.join(BASE_DIR, 'static'),
        static_url_path='/static'
    )

    # ✅ DB URL 불러오기
    database_url = os.getenv("DATABASE_URL")

    # Railway용 PostgreSQL URL 수정
    if database_url and database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    # ✅ 로컬 테스트용 SQLite fallback
    if not database_url:
        instance_dir = os.path.join(BASE_DIR, "instance")
        os.makedirs(instance_dir, exist_ok=True)
        database_url = f"sqlite:///{os.path.join(instance_dir, 'app.db')}"

    # ✅ 설정 적용
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.secret_key = os.getenv("SECRET_KEY", "studyroom-secret-key")

    # ✅ 전역 db 객체와 Flask 앱 연결
    global db
    db.init_app(app)

    # ✅ 모델 import 및 테이블 생성
    with app.app_context():
        import db.models  # 순환 참조 방지
        db.create_all()
        print("✅ DB 테이블 생성 완료")

    # ✅ 정적 파일 직접 제공 (Railway PNG/CSS 깨짐 방지)
    @app.route('/static/<path:filename>')
    def static_files(filename):
        static_dir = os.path.join(BASE_DIR, 'static')
        return send_from_directory(static_dir, filename)

    return app
