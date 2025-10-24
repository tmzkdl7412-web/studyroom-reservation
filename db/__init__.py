# db/__init__.py
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app():
    # ✅ Flask 앱 생성 (templates, static 폴더 경로 명시)
    app = Flask(
        __name__,
        template_folder="../templates",  # 상위 폴더의 templates 인식
        static_folder="../static"        # 상위 폴더의 static 인식
    )

    # ✅ PostgreSQL URI 설정
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        "postgresql://studyroom_db_tcbr_user:"
        "pWMguz9gtllDmvSAjCLkL4avcugRd0kC@"
        "dpg-d3tu7nje5dus73999eb0-a.oregon-postgres.render.com/"
        "studyroom_db_tcbr"
    )

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.secret_key = "studyroom-secret-key"

    # ✅ DB 초기화
    db.init_app(app)

    # ✅ 테이블 자동 생성
    with app.app_context():
        from db import models  # 모델 import
        db.create_all()

    return app
