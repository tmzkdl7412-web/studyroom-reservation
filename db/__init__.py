import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app():
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))     # .../db
    PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, '..'))  # 프로젝트 루트
    DB_PATH = os.path.join(PROJECT_ROOT, 'studyroom.db')      # DB를 루트에 두는 게 현재 파일과 일치

    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    app = Flask(__name__, 
            static_folder=os.path.join(PROJECT_ROOT, 'static'),
            template_folder=os.path.join(PROJECT_ROOT, 'templates'))

    app.secret_key = "supersecretkey"   # ✅ flash(), session 등에 필수

    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    from . import models

    with app.app_context():
        if not os.path.exists(DB_PATH):
            db.create_all()
            print("✅ 데이터베이스가 초기화되었습니다.")
        else:
            print("✅ 기존 데이터베이스를 불러왔습니다.")

    return app
