from flask import render_template, request, redirect, url_for, flash, session
from datetime import datetime, timedelta, timezone
from sqlalchemy import cast, Integer
from db import create_app, db
from db.models import Reservation, PersonalReservation

app = create_app()
KST = timezone(timedelta(hours=9))
# ---------------- 유틸 ----------------
def make_days(n=7):
    base = datetime.now(KST).replace(hour=0, minute=0, second=0, microsecond=0)
    return [(base + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(n + 1)]  # 🔹 +1 해서 다음날 포함


def hours_24():
    return list(range(24))

def expand_hours_with_date(date_str, start_hour, duration):
    """
    시작 시간과 지속시간(duration)을 받아,
    자정 넘는 경우 다음날로 자동 분리해서 반환.
    예: 2025-10-27, 23시, 3시간 → [(2025-10-27, 23), (2025-10-28, 0), (2025-10-28, 1)]
    """
    from datetime import datetime, timedelta

    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    result = []

    for i in range(duration):
        hour = start_hour + i
        if hour < 24:
            result.append((date_str, hour))
        else:
            next_date = (date_obj + timedelta(days=1)).strftime("%Y-%m-%d")
            result.append((next_date, hour - 24))
    return result


# ✅ flash 중복 방지 함수
def safe_flash(message, category=None):
    session.pop('_flashes', None)
    if category:
        flash(message, category=category)
    else:
        flash(message)

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
    room = str(request.args.get("room", "1")).strip()
    days = make_days(7)
    hours = hours_24()

    # ✅ 이번 주(7일치) 데이터만 불러오기
    reservations = Reservation.query.filter(
        Reservation.room == room,
        Reservation.date.in_(days)
    ).all()

    reserved = {d: set() for d in days}
    owners = {}

    for r in reservations:
        try:
            start = int(r.hour)
            dur = int(r.duration or 1)
            rname = (r.leader_name or "").strip()
            rid = (r.leader_id or "").strip().upper()
            label = f"{rid} {rname}" if rname and rname != rid else rid

            # ✅ 자정 넘는 예약까지 처리
            for d, h in expand_hours_with_date(r.date, start, dur):
                reserved.setdefault(d, set()).add(h)  # 🔹 다음날도 자동 추가
                owners[(d, h)] = label

        except Exception as e:
            print("⚠️ room_detail parse error:", e)

    return render_template(
        "group/room_detail.html",
        room=room,
        days=days,
        hours=hours,
        reserved=reserved,
        owners=owners
    )

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

    # ✅ 같은 사용자 개인석 중복 검사 (자정 넘김 포함)
    next_day = (datetime.strptime(date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    overlap_personal = PersonalReservation.query.filter(
        PersonalReservation.leader_id == leader_id,
        PersonalReservation.date.in_([date, next_day])
    ).all()

    for p in overlap_personal:
        for d, h in expand_hours_with_date(p.date, int(p.hour), int(p.duration or 1)):
            for td, th in expand_hours_with_date(date, hour, duration):
                if (d, h) == (td, th):
                    return render_template(
                        "error.html",
                        title="예약 불가",
                        message=f"⚠️ 개인석 예약과 시간이 겹칩니다.<br>프로젝트실 예약은 중복 불가합니다.",
                        back_url=url_for('index')
                    )

    # ✅ 단체실 내 중복 예약 검사 (자정 넘김 포함)
    existing = Reservation.query.filter(
        Reservation.room == room,
        Reservation.date.in_([date, next_day])
    ).all()

    target_hours = set(expand_hours_with_date(date, hour, duration))
    for r in existing:
        exists_hours = set(expand_hours_with_date(r.date, int(r.hour), int(r.duration or 1)))
        if target_hours & exists_hours:
            return render_template(
                "group/simple_msg.html",
                title="❌ 예약 불가",
                message=f"{r.date}일 {r.hour}시~{int(r.hour) + int(r.duration)}시까지 이미 예약이 있습니다.",
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

    return render_template(
        "group/simple_msg.html",
        title="✅ 예약 완료",
        message="예약이 성공적으로 완료되었습니다!",
        back_url=f"/room_detail?room={room}"
    )


# -------------------------------
# 🔸 개인석 예약 (Personal Seat)
# -------------------------------
@app.route("/personal_all")
def personal_all():
    days = make_days(3)
    hours = hours_24()
    reservations = PersonalReservation.query.filter(
        PersonalReservation.date.in_(days),
        PersonalReservation.seat.in_([str(i) for i in range(1, 8)])
    ).all()

    seats = {i: {"reserved": {d: set() for d in days}, "owners": {}} for i in range(1, 8)}
    for r in reservations:
        try:
            seat_num, start, dur = int(r.seat), int(r.hour), int(r.duration or 1)
            label = f"{(r.leader_id or '').upper()} {(r.leader_name or '').strip()}".strip()

            # ✅ 자정 넘는 경우도 반영
            for d, h in expand_hours_with_date(r.date, start, dur):
                seats[seat_num]["reserved"].setdefault(d, set()).add(h)
                seats[seat_num]["owners"][(d, h)] = label

        except Exception as e:
            print("⚠ personal_all parse error:", e)

    return render_template(
        "personal/personal_all.html",
        days=days, hours=hours, seats=seats
    )

@app.route("/personal_all")
def personal_all():
    days = make_days(3)
    hours = hours_24()
    reservations = PersonalReservation.query.filter(
        PersonalReservation.date.in_(days),
        PersonalReservation.seat.in_([str(i) for i in range(1, 8)])
    ).all()

    seats = {i: {"reserved": {d: set() for d in days}, "owners": {}} for i in range(1, 8)}
    for r in reservations:
        try:
            seat_num, start, dur = int(r.seat), int(r.hour), int(r.duration or 1)
            label = f"{(r.leader_id or '').upper()} {(r.leader_name or '').strip()}".strip()
            for h in expand_hours(start, dur):
                seats[seat_num]["reserved"][r.date].add(h)
                seats[seat_num]["owners"][(r.date, h)] = label
        except Exception as e:
            print("⚠ personal_all parse error:", e)

    return render_template(
        "personal/personal_all.html",
        days=days, hours=hours, seats=seats
    )

@app.route("/personal_reserve_form")
def personal_reserve_form():
    seat = request.args.get("seat")
    date = request.args.get("date")
    hour = int(request.args.get("hour"))
    return render_template("/personal/personal_reserve_form.html", seat=seat, date=date, hour=hour)

@app.route("/personal_reserve", methods=["POST"])
def personal_reserve():
    seat = request.form.get("seat")
    date = request.form.get("date")
    hour = int(request.form.get("hour"))
    duration = int(request.form.get("duration", 1))
    leader_name = request.form.get("leader_name", "").strip()
    leader_id = request.form.get("leader_id", "").strip().upper()
    leader_phone = request.form.get("leader_phone", "").strip()

    # ✅ 입력 검증
    if not leader_name or not leader_id or leader_name == leader_id:
        return render_template(
            "personal/simple_msg.html",
            title="❌ 예약 불가",
            message="대표자 이름과 학번을 올바르게 입력해주세요.",
            back_url=f"/personal_detail?seat={seat}"
        )

    start_hour = hour
    end_hour = hour + duration

    # ✅ 같은 사용자 단체실 중복 검사 (강화 버전)
    overlap_group = Reservation.query.filter(
        Reservation.leader_id == leader_id,
        Reservation.date == date
    ).all()

    for g in overlap_group:
        g_start = int(g.hour)
        g_end = g_start + int(g.duration or 1)
        # 겹치거나 딱 맞닿는 경우까지 차단
        if not (end_hour <= g_start or start_hour >= g_end):
            return render_template(
                "error.html",
                title="예약 불가",
                message=f"⚠️ 이미 같은 날짜({date})에 프로젝트실 예약이 있습니다.<br>개인석 예약은 중복 불가합니다.",
                back_url=f"/personal_detail?seat={seat}"
            )

    # ✅ 같은 개인석 시간대 중복 금지
    existing = PersonalReservation.query.filter(
        PersonalReservation.seat == seat,
        PersonalReservation.date == date
    ).all()

    target_hours = set(range(hour, hour + duration))
    for r in existing:
        s = int(r.hour)
        d = int(r.duration or 1)
        exists_hours = set(range(s, s + d))
        if target_hours & exists_hours:
            return render_template(
                "personal/simple_msg.html",
                title="❌ 예약 불가",
                message=f"{r.date}일 {r.hour}시~{int(r.hour) + int(r.duration)}시까지 이미 예약이 있습니다.",
                back_url=f"/personal_detail?seat={seat}"
            )

    # ✅ DB 저장
    new_resv = PersonalReservation(
        seat=seat,
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

    return render_template(
        "personal/simple_msg.html",
        title="✅ 예약 완료",
        message="예약이 성공적으로 완료되었습니다!",
        back_url=f"/personal_detail?seat={seat}"
    )

# -------------------------------
# 🔸 시간 연장 기능
# -------------------------------
@app.route("/extend_page", methods=["GET", "POST"])
def extend_page():
    """연장 페이지 — 종료 20분 전부터만 연장 가능 (1차 차단)"""
    now = datetime.now(KST)
    today = now.strftime("%Y-%m-%d")

    if request.method == "POST":
        name = request.form.get("leader_name", "").strip()
        sid = request.form.get("leader_id", "").strip().upper()

        # 현재 시간대에 진행 중인 예약만 탐색
        group = Reservation.query.filter(
            Reservation.leader_name == name, Reservation.leader_id == sid,
            Reservation.date == today,
            cast(Reservation.hour, Integer) <= now.hour,
            (cast(Reservation.hour, Integer) + cast(Reservation.duration, Integer)) > now.hour
        ).first()

        personal = PersonalReservation.query.filter(
            PersonalReservation.leader_name == name, PersonalReservation.leader_id == sid,
            PersonalReservation.date == today,
            cast(PersonalReservation.hour, Integer) <= now.hour,
            (cast(PersonalReservation.hour, Integer) + cast(PersonalReservation.duration, Integer)) > now.hour
        ).first()

        res = group or personal
        if not res:
            safe_flash("금일 연장 가능한 예약이 없습니다.<br>예약 종료 20분 전부터만 연장이 가능합니다.")
            return redirect(url_for("extend_page"))

        # ✅ 종료 시각 계산
        start_hour = int(res.hour)
        start_dt = datetime.strptime(
            f"{res.date} {start_hour}:00", "%Y-%m-%d %H:%M"
        ).replace(tzinfo=KST)
        end_dt = start_dt + timedelta(hours=int(res.duration))
        remaining = int((end_dt - now).total_seconds() // 60)

        # 디버깅 로그
        print(f"[extend_page] now={now}, start_dt={start_dt}, end_dt={end_dt}, remaining(min)={remaining}")

        # ✅ 20분 전이 아니면 연장 불가 (1차 차단)
        if remaining > 20:
            safe_flash("⚠️ 예약 종료 20분 전부터만 연장할 수 있습니다.")
            return redirect(url_for("extend_page"))

        # 경과 시간 표시
        elapsed = now - start_dt
        elapsed_str = f"{elapsed.seconds // 3600}시간 {(elapsed.seconds % 3600) // 60}분"

        res_type = "group" if isinstance(res, Reservation) else "personal"
        return render_template("extend_confirm.html", res=res, res_type=res_type, elapsed=elapsed_str)

    return render_template("extend_page.html")
    
@app.route("/extend_confirm", methods=["POST"])
def extend_confirm():
    """
    단체/개인 공통 연장 처리:
    - 20분 제한 2차 차단(직접 호출/우회 방지)
    - 23→00 자정 넘김 처리 (기존 예약 유지)
    - 뒤 시간대 겹침 검증
    - 성공 시 extend_success.html / 실패 시 extend_blocked.html
    """
    res_type = request.form.get("res_type")          # "group" or "personal"
    res_id = request.form.get("res_id", type=int)    # 예약 PK
    extend_hours = int(request.form.get("extend_hours", 0))

    # 모델 선택 및 조회
    Model = Reservation if res_type == "group" else PersonalReservation
    reservation = Model.query.filter_by(id=res_id).first()
    if not reservation:
        safe_flash("⚠️ 예약을 찾을 수 없습니다.")
        return redirect(url_for("extend_page"))

    now = datetime.now(KST)

    # 현재 예약의 시작/종료, 남은 시간 계산
    start_hour = int(reservation.hour)
    duration = int(reservation.duration)
    start_dt = datetime.strptime(
        f"{reservation.date} {start_hour}:00", "%Y-%m-%d %H:%M"
    ).replace(tzinfo=KST)
    end_dt = start_dt + timedelta(hours=duration)
    remaining = int((end_dt - now).total_seconds() // 60)

    # 디버깅 로그
    print(f"[extend_confirm] now={now}, start_dt={start_dt}, end_dt={end_dt}, remaining(min)={remaining}")

    # ✅ 20분 제한 (2차 차단: 직접 POST 우회 방지)
    if remaining > 20:
        safe_flash("⚠️ 예약 종료 20분 전부터만 연장할 수 있습니다.")
        return redirect(url_for("extend_page"))

    # 연장 구간 (end_dt ~ end_dt + extend_hours)
    new_start_hour = end_dt.hour
    new_end_dt = end_dt + timedelta(hours=extend_hours)
    new_date = new_end_dt.strftime("%Y-%m-%d")
    old_date = reservation.date

    # 겹침 검사 함수
    def has_overlap(model, date_str, start_h, dur):
        if model is Reservation:
            q = model.query.filter(
                model.room == reservation.room,
                model.date == date_str,
                cast(model.hour, Integer) < start_h + dur,
                (cast(model.hour, Integer) + cast(model.duration, Integer)) > start_h,
                model.id != reservation.id
            )
        else:
            q = model.query.filter(
                model.seat == reservation.seat,
                model.date == date_str,
                cast(model.hour, Integer) < start_h + dur,
                (cast(model.hour, Integer) + cast(model.duration, Integer)) > start_h,
                model.id != reservation.id
            )
        return q.first() is not None

    if extend_hours <= 0:
        safe_flash("연장 시간이 올바르지 않습니다.")
        return redirect(url_for("extend_page"))

    # 자정 넘김 여부
    crosses_midnight = (new_date != old_date) and (new_start_hour < start_hour)

    # 겹침 검사 대상
    check_date = old_date if not crosses_midnight else new_date
    check_start_hour = new_start_hour
    check_duration = extend_hours

    # 겹침 있으면 차단
    if has_overlap(Model, check_date, check_start_hour, check_duration):
        return render_template(
            "extend_blocked.html",
            message="⚠️ 연장 불가: 뒤 시간대에 이미 예약이 있습니다."
        )

    # DB 업데이트 (기존 예약 유지)
    if crosses_midnight:
        reservation.date = new_date
        reservation.duration = duration + extend_hours
    else:
        reservation.duration = duration + extend_hours

    db.session.commit()
    return render_template("extend_success.html", extend_hours=extend_hours)

# -------------------------------
# 🔸 예약 취소
# -------------------------------
@app.route("/cancel_all", methods=["GET", "POST"])
def cancel_all():
    if request.method == "GET":
        return render_template("cancel_all.html")

    leader_name = request.form.get("leader_name", "").strip()
    leader_id = request.form.get("leader_id", "").strip().upper()
    leader_phone = request.form.get("leader_phone", "").strip()

    if not leader_name or not leader_id or not leader_phone:
        safe_flash("⚠️ 이름, 학번, 전화번호를 모두 입력해주세요.")
        return redirect(url_for("cancel_all"))

    group_reservations = Reservation.query.filter_by(
        leader_name=leader_name, leader_id=leader_id, leader_phone=leader_phone
    ).order_by(Reservation.date, cast(Reservation.hour, Integer)).all()

    personal_reservations = PersonalReservation.query.filter_by(
        leader_name=leader_name, leader_id=leader_id, leader_phone=leader_phone
    ).order_by(PersonalReservation.date, cast(PersonalReservation.hour, Integer)).all()

    # ✅ 결과가 없더라도 결과 페이지에서 경고를 보여주도록 렌더링
    if not group_reservations and not personal_reservations:
        safe_flash("❌ 해당 정보로 예약된 내역이 없습니다.")
        return render_template(
            "cancel_all_result.html",
            group_reservations=[],
            personal_reservations=[],
            leader_name=leader_name,
            leader_id=leader_id,
            leader_phone=leader_phone
        )

    return render_template(
        "cancel_all_result.html",
        group_reservations=group_reservations,
        personal_reservations=personal_reservations,
        leader_name=leader_name,
        leader_id=leader_id,
        leader_phone=leader_phone
    )

@app.route("/cancel_all_confirm", methods=["POST"])
def cancel_all_confirm():
    selected_items = request.form.getlist("selected")
    leader_name = request.form.get("leader_name", "").strip()
    leader_id = request.form.get("leader_id", "").strip().upper()
    leader_phone = request.form.get("leader_phone", "").strip()

    if not selected_items:
        safe_flash("⚠️ 선택된 예약이 없습니다.")
        group_reservations = Reservation.query.filter_by(
            leader_name=leader_name, leader_id=leader_id
        ).order_by(Reservation.date, cast(Reservation.hour, Integer)).all()
        personal_reservations = PersonalReservation.query.filter_by(
            leader_name=leader_name, leader_id=leader_id
        ).order_by(PersonalReservation.date, cast(PersonalReservation.hour, Integer)).all()
        return render_template(
            "cancel_all_result.html",
            group_reservations=group_reservations,
            personal_reservations=personal_reservations,
            leader_name=leader_name,
            leader_id=leader_id,
            leader_phone=leader_phone
        )

    group_deleted, personal_deleted = 0, 0

    for item in selected_items:
        try:
            # ✅ value 형식: "group:3" 또는 "personal:7"
            type_, id_str = item.split(":", 1)
            target_id = int(id_str)

            if type_ == "group":
                deleted = Reservation.query.filter_by(
                    id=target_id,
                    leader_name=leader_name,
                    leader_id=leader_id
                ).delete(synchronize_session=False) or 0
                group_deleted += deleted

            elif type_ == "personal":
                deleted = PersonalReservation.query.filter_by(
                    id=target_id,
                    leader_name=leader_name,
                    leader_id=leader_id
                ).delete(synchronize_session=False) or 0
                personal_deleted += deleted

        except Exception as e:
            print("❌ 예약 취소 중 오류:", e)

    db.session.commit()
    total_deleted = group_deleted + personal_deleted

    if total_deleted > 0:
        safe_flash(f"✅ 선택한 {total_deleted}개의 예약이 취소되었습니다.")
    else:
        safe_flash("⚠️ 선택된 예약을 찾을 수 없거나 이미 삭제되었습니다.")

    # ✅ 삭제 후 남은 예약 다시 불러오기
    group_reservations = Reservation.query.filter_by(
        leader_name=leader_name, leader_id=leader_id
    ).order_by(Reservation.date, cast(Reservation.hour, Integer)).all()

    personal_reservations = PersonalReservation.query.filter_by(
        leader_name=leader_name, leader_id=leader_id
    ).order_by(PersonalReservation.date, cast(PersonalReservation.hour, Integer)).all()

    return render_template(
        "cancel_all_result.html",
        group_reservations=group_reservations,
        personal_reservations=personal_reservations,
        leader_name=leader_name,
        leader_id=leader_id,
        leader_phone=leader_phone
    )

@app.route("/cancel_all_result")
def cancel_all_result():
    return render_template("cancel_all_result.html")

# ---------------- 실행 ----------------
if __name__ == "__main__":
    app.run(debug=True)

