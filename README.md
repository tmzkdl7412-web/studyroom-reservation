# 🏫 산업·데이터공학과 스터디룸 예약 시스템

홍익대학교 산업·데이터공학과 학생들이 **프로젝트실(단체석)** 과 **개인석**을 웹에서 예약·연장·취소할 수 있도록 만든 예약 서비스입니다.
로그인 없이 이름·학번·전화번호만으로 예약을 관리하며, 중복 예약과 시간 겹침을 서버에서 자동으로 차단합니다.

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-000000?logo=flask&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)
![Railway](https://img.shields.io/badge/Deploy-Railway-0B0D0E?logo=railway&logoColor=white)

## 주요 기능

| 기능 | 설명 |
|------|------|
| **프로젝트실(단체) 예약** | 프로젝트실 1·2, 7일치 × 24시간 시간표에서 빈 칸을 눌러 1~3시간 예약 (대표자 포함 최대 6명) |
| **개인석 예약** | 개인석 1~7번, 3일치 시간표 · 전체 좌석 현황 한눈에 보기 |
| **중복 예약 방지** | 같은 방·좌석의 시간 겹침 차단, 같은 학번의 단체실·개인석 동시 예약 차단 |
| **자정 넘김 처리** | 23시 시작 예약처럼 다음 날로 넘어가는 시간도 시간표에 올바르게 표시 |
| **시간 연장** | 이용 종료 **20분 전부터만** 1~2시간 연장 가능 (화면 + 서버 2중 검증, 뒤 예약과 겹치면 차단) |
| **예약 조회·취소** | 이름 + 학번 + 전화번호로 본인 예약을 조회하고 원하는 것만 골라 취소 |
| **안내 페이지** | 냉·난방 이용 안내, 문의사항 페이지 |

## 기술 스택

- **Backend**: Python 3.11, Flask 3.0, Flask-SQLAlchemy
- **Database**: PostgreSQL (배포) / SQLite (DB 주소가 없을 때 자동 대체)
- **Frontend**: Jinja2 템플릿 + HTML/CSS (모바일 대응)
- **Deploy**: Railway, Gunicorn (`Procfile`)

## 프로젝트 구조

```
studyroom-reservation/
├── app.py                 # 라우팅 및 예약·연장·취소 로직
├── wsgi.py                # Gunicorn 진입점
├── db/
│   ├── __init__.py        # Flask 앱 생성, DB 연결 설정
│   └── models.py          # Reservation(단체) / PersonalReservation(개인) 모델
├── templates/
│   ├── index.html         # 메인 화면
│   ├── group/             # 프로젝트실 시간표·예약 폼
│   ├── personal/          # 개인석 시간표·예약 폼·전체 현황
│   └── extend_*.html, cancel_*.html, contact.html, hvac_info.html
├── static/                # 로고, 마스코트 이미지
├── requirements.txt
├── runtime.txt
└── Procfile
```

## 실행 방법

```bash
pip install -r requirements.txt

# PostgreSQL 주소 설정 (단체석 예약 저장에 PostgreSQL 전용 쿼리를 사용합니다)
export DATABASE_URL="postgresql://user:password@localhost:5432/studyroom"
export SECRET_KEY="임의의-비밀키"

python app.py          # 개발 서버
# 또는
gunicorn wsgi:app      # 배포 환경과 동일
```

`DATABASE_URL`이 없으면 `instance/app.db`(SQLite)로 실행되며, 이 경우 화면 확인과 개인석 예약까지 동작합니다.

## 데이터 모델

- **Reservation** (프로젝트실): 방 번호, 날짜, 시작 시각, 이용 시간, 대표자 정보, 팀원(최대 5명)
- **PersonalReservation** (개인석): 좌석 번호, 날짜, 시작 시각, 이용 시간, 예약자 정보
- 조회가 잦은 `(방/좌석, 날짜)`, `(학번, 날짜)` 조합에 인덱스를 두어 시간표 조회 속도를 확보했습니다.
