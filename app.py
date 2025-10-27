from flask import render_template, request, redirect, url_for, flash, session
from datetime import datetime, timedelta, timezone
from sqlalchemy import cast, Integer
from db import create_app, db
from db.models import Reservation, PersonalReservation

app = create_app()
KST = timezone(timedelta(hours=9))

# ---------------- 유틸 ----------------
def make_days(n=7):
    """✅ 오늘부터 n일치 날짜 리스트 생성 (한국 시간 기준)"""
    base = datetime.now(KST).replace(hour=0, minute=0, second=0, microsecond=0)
    return [(base + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(n)]

def hours_24():
    return list(range(24))

def expand_hours(start_hour, duration):
    return [h for h in range(start_hour, start_hour + duration) if 0 <= h < 24]

def safe_flash(message, category=None):
    session.pop('_flashes', None)
    if category:
        flash(message, category=category)
    else:
        flash(message)

# ✅ 추가: 겹침 비교 헬퍼
def is_overlap(start1, end1, start2, end2):
    """두 구간이 겹치면 True 반환"""
    return not (end1 <= start2 or start1 >= end2)

# ---------------- 홈/메인 ----------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

# -------------------------------
# 🔹 단체석 예약 (Project Room)
# -------------------------------
@app.route("/room_detail")
def room_detail():
    room = request.args.get("room", "1")
    days = make_days(7)
    hours = hours_24()

    # ✅ 이번 주(7일치) + 다음날 1일 추가로 불러오기 (자정 넘김 대응)
    days_with_next = days + [
        (datetime.strptime(days[-1], "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    ]

    reservations = Reservation.query.filter(
        Reservation.room == room,
        Reservation.date.in_(days_with_next)
    ).all()

    reserved = {d: set() for d in days}
    owners = {}

    for r in reservations:
        try:
            start = int(r.hour)
            dur = int(r.duration or 1)
            end = start + dur

            rname = (r.leader_name or "").strip()
            rid = (r.leader_id or "").strip().upper()
            label = f"{rid} {rname}" if rname and rname != rid else rid

            # ✅ 일반 시간대
            if end <= 24:
                for h in expand_hours(start, dur):
                    if r.date in reserved:
                        reserved[r.date].add(h)
                        owners[(r.date, h)] = label

            # ✅ 자정 넘김(24시 초과)인 경우 → 다음날로 일부 반영 (중복 방지)
            else:
                next_date = (datetime.strptime(r.date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
                # 오늘 날짜 부분
                for h in range(start, 24):
                    if r.date in reserved:
                        reserved[r.date].add(h)
                        owners[(r.date, h)] = label
                # 다음날 부분 (이미 표시된 항목 제외)
                if next_date in reserved:
                    for h in range(0, end - 24):
                        if (next_date, h) not in owners:
                            reserved[next_date].add(h)
                            owners[(next_date, h)] = label + " (연장)"

        except Exception as e:
            print("⚠ hour/duration parse error:", e)

    return render_template(
        "group/room_detail.html",
        room=room,
        days=days,
        hours=hours,
        reserved=reserved,
        owners=owners
    )

# ✅ 수정된 reserve_group
@app.route("/reserve", methods=["POST"])
def reserve_group():
    room = request.form.get("room")
    date = request.form.get("date")
    hour = int(request.form.get("hour"))
    duration = int(request.form.get("duration", 1))

    leader_name = request.form.get("leader_name", "").strip()
    leader_id = request.form.get("leader_id", "").strip().upper()
    leader_phone = request.form.get("leader_phone", "").strip()

    # ✅ 입력 검증
    if not leader_name or not leader_id or leader_name == leader_id:
        return render_template(
            "group/simple_msg.html",
            title="❌ 예약 불가",
            message="대표자 이름과 학번을 올바르게 입력해주세요.",
            back_url=f"/room_detail?room={room}"
        )

    start_hour = hour
    end_hour = hour + duration
    crosses_midnight = end_hour > 24
    next_date = (datetime.strptime(date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    end_hour_mod = end_hour % 24  # 다음날 시각

    # ✅ 개인석 예약 겹침 검사 (시간 기준)
    overlap_personal = PersonalReservation.query.filter(
        PersonalReservation.leader_id == leader_id,
        PersonalReservation.date.in_([date, next_date])
    ).all()

    for p in overlap_personal:
        p_start = int(p.hour)
        p_end = p_start + int(p.duration or 1)
        if p.date == date and is_overlap(start_hour, end_hour, p_start, p_end):
            return render_template(
                "error.html",
                title="예약 불가",
                message=f"⚠️ 이미 {p.date}일 {p.hour}시~{p_end}시 개인석 예약이 있습니다.<br>프로젝트실 예약은 중복 불가합니다.",
                back_url=f"/room_detail?room={room}"
            )
        if crosses_midnight and p.date == next_date and is_overlap(0, end_hour_mod, p_start, p_end):
            return render_template(
                "error.html",
                title="예약 불가",
                message=f"⚠️ 이미 {next_date}일 {p.hour}시~{p_end}시 개인석 예약이 있습니다.<br>프로젝트실 예약은 중복 불가합니다.",
                back_url=f"/room_detail?room={room}"
            )

    # ✅ 단체실 내 중복 예약 검사
    existing = Reservation.query.filter(
        Reservation.room == room,
        Reservation.date.in_([date, next_date])
    ).all()

    for r in existing:
        r_start = int(r.hour)
        r_end = r_start + int(r.duration or 1)
        if r.date == date and is_overlap(start_hour, end_hour, r_start, r_end):
            return render_template(
                "group/simple_msg.html",
                title="❌ 예약 불가",
                message=f"{r.date}일 {r.hour}시~{r_end}시 이미 예약되어 있습니다.",
                back_url=f"/room_detail?room={room}"
            )
        if crosses_midnight and r.date == next_date and is_overlap(0, end_hour_mod, r_start, r_end):
            return render_template(
                "group/simple_msg.html",
                title="❌ 예약 불가",
                message=f"{next_date}일 {r.hour}시~{r_end}시 이미 예약되어 있습니다.",
                back_url=f"/room_detail?room={room}"
            )

    # ✅ DB 저장
    new_resv = Reservation(
        room=room,
        date=date,
        hour=str(hour),
        leader_name=leader_name,
        leader_id=leader_id,
        leader_phone=leader_phone,
        total_people=1,
        duration=duration
    )
    db.session.add(new_resv)
    db.session.commit()

    # ✅ 로그
    if crosses_midnight:
        print(f"✅ DB 커밋 완료: {room} / {date} {hour}시~다음날 {end_hour_mod}시 ({leader_id})")
    else:
        print(f"✅ DB 커밋 완료: {room} / {date} {hour}시~{end_hour}시 ({leader_id})")

    return render_template(
        "group/simple_msg.html",
        title="✅ 예약 완료",
        message="예약이 성공적으로 완료되었습니다!",
        back_url=f"/room_detail?room={room}"
    )
