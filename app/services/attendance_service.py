import base64
import io
from datetime import UTC, datetime, timedelta

import jwt
import qrcode
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BusinessException
from app.models import Appointment, Course
from app.schemas import CheckinVO
from app.services.appointment_service import _record_action, _require_member
from app.services.notification_service import notify_member

CHECKIN_AUDIENCE = "multiagent-gym-checkin"


def create_checkin_payload(db: Session, course_id: int) -> dict:
    course = db.get(Course, course_id)
    if course is None:
        raise BusinessException("课程不存在")
    now = datetime.now(UTC)
    expire_seconds = max(settings.checkin_token_seconds, 20)
    payload = {
        "typ": "course_checkin",
        "aud": CHECKIN_AUDIENCE,
        "courseId": course.id,
        "iat": now,
        "exp": now + timedelta(seconds=expire_seconds),
    }
    token = jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    checkin_url = (
        f"{settings.frontend_public_url.rstrip('/')}/member/checkin?token={token}"
    )
    qr = qrcode.QRCode(version=1, box_size=8, border=2)
    qr.add_data(checkin_url)
    qr.make(fit=True)
    image = qr.make_image(fill_color="#0f172a", back_color="white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    data_url = (
        "data:image/png;base64,"
        + base64.b64encode(buffer.getvalue()).decode("ascii")
    )
    return {
        "courseId": course.id,
        "courseName": course.name,
        "token": token,
        "checkinUrl": checkin_url,
        "qrCode": data_url,
        "expiresAt": payload["exp"].isoformat(),
    }


def check_in(db: Session, related_id: int | None, token: str) -> CheckinVO:
    member = _require_member(db, related_id)
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            audience=CHECKIN_AUDIENCE,
            options={"require": ["exp", "iat", "courseId"]},
        )
    except jwt.PyJWTError as exception:
        raise BusinessException("签到码无效或已过期，请扫描最新二维码") from exception
    if payload.get("typ") != "course_checkin":
        raise BusinessException("签到码类型无效")

    course_id = int(payload["courseId"])
    appointment = db.scalar(
        select(Appointment)
        .where(
            Appointment.member_id == member.id,
            Appointment.course_id == course_id,
        )
        .with_for_update()
    )
    if appointment is None or appointment.status not in {"reserved", "checked_in"}:
        raise BusinessException("没有找到该课程的有效的预约")
    course = db.scalar(
        select(Course).where(Course.id == course_id).with_for_update()
    )
    if course is None or not course.start_time:
        raise BusinessException("课程不存在")
    now = datetime.now()
    open_at = course.start_time - timedelta(
        minutes=settings.checkin_open_minutes_before
    )
    close_at = course.start_time + timedelta(
        minutes=settings.checkin_close_minutes_after
    )
    if now < open_at:
        raise BusinessException("签到尚未开放")
    if now > close_at:
        raise BusinessException("签到时间已结束")
    if appointment.status == "checked_in":
        return CheckinVO(
            appointment_id=appointment.id,
            course_id=course.id,
            course_name=course.name,
            checked_in_at=appointment.update_time,
        )

    appointment.status = "checked_in"
    appointment.update_time = now
    _record_action(
        db,
        appointment_id=appointment.id,
        member_id=member.id,
        course_id=course.id,
        action="checkin",
        detail=f"扫码签到：{course.name}",
    )
    notify_member(
        db,
        member_id=member.id,
        type="checkin_success",
        title="课程签到成功",
        content=f"您已完成“{course.name}”签到。",
        related_id=appointment.id,
    )
    db.flush()
    return CheckinVO(
        appointment_id=appointment.id,
        course_id=course.id,
        course_name=course.name,
        checked_in_at=now,
    )


def mark_no_shows(db: Session, now: datetime | None = None) -> int:
    if not settings.no_show_auto_enabled:
        return 0
    current = now or datetime.now()
    cutoff = current - timedelta(minutes=settings.no_show_grace_minutes)
    lookback = current - timedelta(days=max(settings.no_show_lookback_days, 1))
    rows = db.execute(
        select(Appointment, Course)
        .join(Course, Appointment.course_id == Course.id)
        .where(
            Appointment.status == "reserved",
            Course.end_time.is_not(None),
            Course.end_time < cutoff,
            Course.end_time >= lookback,
        )
        .with_for_update()
    ).all()
    for appointment, course in rows:
        appointment.status = "no_show"
        appointment.update_time = current
        _record_action(
            db,
            appointment_id=appointment.id,
            member_id=appointment.member_id,
            course_id=course.id,
            action="no_show",
            detail=f"未签到爽约：{course.name}",
        )
        notify_member(
            db,
            member_id=appointment.member_id,
            type="no_show",
            title="课程爽约记录",
            content=f"您未完成“{course.name}”签到，本次课程已记为爽约。",
            related_id=appointment.id,
        )
    return len(rows)
