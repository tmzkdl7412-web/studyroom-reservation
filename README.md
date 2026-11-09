# 산업·데이터공학과 프로젝트실·개인석 예약 시스템

홍익대학교 산업·데이터공학과 학생들이 프로젝트실(단체)과 개인석을 웹에서 예약하고, 연장하고, 취소할 수 있게 만든 서비스입니다. 로그인 없이 이름, 학번, 전화번호로 예약을 관리하고, 겹치는 예약은 서버에서 막습니다.

배포 주소: https://hidestudyroom-reservation.up.railway.app/

## 기능

| 기능 | 내용 |
| --- | --- |
| 프로젝트실 예약 | 프로젝트실 1·2의 7일치 시간표에서 빈 시간을 눌러 1~3시간 예약. 대표자 포함 최대 6명 |
| 개인석 예약 | 개인석 1~7번의 3일치 시간표, 전체 좌석 현황 화면 |
| 중복 예약 방지 | 같은 방·좌석의 시간 겹침 차단. 같은 학번으로 프로젝트실과 개인석을 동시에 잡는 것도 차단 |
| 자정 넘김 처리 | 23시에 시작하는 예약처럼 다음 날로 넘어가는 시간도 시간표에 맞게 표시 |
| 시간 연장 | 이용 종료 20분 전부터 1~2시간 연장 가능. 화면과 서버 양쪽에서 확인하고, 뒤 예약과 겹치면 막음 |
| 조회·취소 | 이름, 학번, 전화번호로 내 예약을 찾아 골라서 취소 |
| 안내 페이지 | 냉난방 이용 안내, 문의 페이지 |

## 기술 스택

- Backend: Python 3.11, Flask 3.0, Flask-SQLAlchemy
- Database: PostgreSQL (배포), DB 주소가 없으면 SQLite로 실행
- Frontend: Jinja2 템플릿, HTML/CSS (모바일 화면 대응)
- 배포: Railway, Gunicorn

## 실행 방법

```bash
pip install -r requirements.txt

# 프로젝트실 예약 저장에 PostgreSQL 전용 쿼리를 사용합니다
export DATABASE_URL="postgresql://user:password@localhost:5432/studyroom"
export SECRET_KEY="임의의-비밀키"

python app.py          # 개발 서버
gunicorn wsgi:app      # 배포 환경과 같은 방식
```

`DATABASE_URL`이 없으면 `instance/app.db`(SQLite)로 실행됩니다. 이때는 화면 확인과 개인석 예약까지만 됩니다.

## 데이터 모델

- `Reservation`(프로젝트실): 방 번호, 날짜, 시작 시각, 이용 시간, 대표자 정보, 팀원(최대 5명)
- `PersonalReservation`(개인석): 좌석 번호, 날짜, 시작 시각, 이용 시간, 예약자 정보
- 자주 조회하는 (방/좌석, 날짜), (학번, 날짜) 조합에 인덱스를 걸었습니다.

## 구조

```
studyroom-reservation/
├── app.py            # 라우팅, 예약·연장·취소 로직
├── wsgi.py           # Gunicorn 진입점
├── db/
│   ├── __init__.py   # Flask 앱 생성, DB 연결
│   └── models.py     # Reservation, PersonalReservation 모델
├── templates/
│   ├── index.html
│   ├── group/        # 프로젝트실 시간표, 예약 폼
│   ├── personal/     # 개인석 시간표, 예약 폼, 전체 현황
│   └── extend_*.html, cancel_*.html, contact.html, hvac_info.html
├── static/           # 로고, 이미지
├── requirements.txt
├── runtime.txt
└── Procfile
```
