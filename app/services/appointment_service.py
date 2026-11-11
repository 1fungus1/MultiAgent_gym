from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BusinessException
from app.models import Appointment, AppointmentActionLog, Course
from app.schemas import AppointmentVO
from app.services.member_service import _require_member
from app.services.notification_service import notify_member
from app.services.query_service import appointment_rows_statement, to_appointment_vo


def _record_action(
    db: Session,
    *,
    appointment_id: int,
    member_id: int,
    course_id: int,
    action: str,
    detail: str,
    target_course_id: int | None = None,
) -> None:
    db.add(
        AppointmentActionLog(
            appointment_id=appointment_id,
            member_id=member_id,
            course_id=course_id,
            target_course_id=target_course_id,
            action=action,
            detail=detail,
        )
    )


def list_member_appointments(db: Session, related_id: int | None) -> list[AppointmentVO]:
    member = _require_member(db, related_id)
    statement = appointment_rows_statement().where(Appointment.member_id == member.id)
    return [to_appointment_vo(row) for row in db.execute(statement).all()]


def _validate_membership(member: Any) -> None:
    if member.status != 1:
        raise BusinessException("会员账号已禁用")
    if member.expire_time is None or member.expire_time < date.today():
        raise BusinessException("会员卡已过期，请续费后再预约")


def reserve(db: Session, related_id: int | None, course_id: int) -> None:
    member = _require_member(db, related_id)
    _validate_membership(member)
    course = db.scalar(
        select(Course).where(Course.id == course_id).with_for_update()
    )
    if course is None:
        raise BusinessException("课程不存在")
    if course.status != 1:
        raise BusinessException("课程已停课")
    if course.booked_count >= course.capacity:
        raise BusinessException("课程已满，可加入候补")

    existing = db.scalar(
        select(Appointment)
        .where(
            Appointment.member_id == member.id,
            Appointment.course_id == course_id,
        )
        .with_for_update()
    )
    if existing is not None:
        if existing.status == "reserved":
            raise BusinessException("该会员已预约过该课程")
        existing.status = "reserved"
        existing.update_time = datetime.now()
        appointment = existing
    else:
        appointment = Appointment(
            member_id=member.id,
            course_id=course_id,
            status="reserved",
        )
        db.add(appointment)

    course.booked_count += 1
    course.update_time = datetime.now()
    try:
        db.flush()
        _record_action(
            db,
            appointment_id=appointment.id,
            member_id=member.id,
            course_id=course_id,
            action="reserve",
            detail=f"预约课程：{course.name}",
        )
        db.flush()
    except IntegrityError as exception:
        raise BusinessException("该会员已预约过该课程") from exception


def join_waitlist(db: Session, related_id: int | None, course_id: int) -> None:
    member = _require_member(db, related_id)
    _validate_membership(member)
    course = db.scalar(
        select(Course).where(Course.id == course_id).with_for_update()
    )
    if course is None or course.status != 1:
        raise BusinessException("课程不存在或已停课")
    if not course.start_time or course.start_time <= datetime.now():
        raise BusinessException("课程已开始，无法加入候补")
    if course.booked_count < course.capacity:
        raise BusinessException("课程仍有名额，请直接预约")

    appointment = db.scalar(
        select(Appointment)
        .where(
            Appointment.member_id == member.id,
            Appointment.course_id == course_id,
        )
        .with_for_update()
    )
    if appointment is not None and appointment.status in {
        "reserved",
        "waitlisted",
        "pending_confirmation",
        "checked_in",
    }:
        messages = {
            "reserved": "您已经预约该课程",
            "waitlisted": "您已经在该课程候补队列中",
            "pending_confirmation": "您已有待确认的候补名额",
            "checked_in": "您已经签到该课程",
        }
        raise BusinessException(messages[appointment.status])

    now = datetime.now()
    if appointment is None:
        appointment = Appointment(
            member_id=member.id,
            course_id=course_id,
            status="waitlisted",
            create_time=now,
            update_time=now,
        )
        db.add(appointment)
    else:
        appointment.status = "waitlisted"
        appointment.create_time = now
        appointment.update_time = now
    db.flush()
    _record_action(
        db,
        appointment_id=appointment.id,
        member_id=member.id,
        course_id=course_id,
        action="waitlist",
        detail=f"加入候补：{course.name}",
    )
    queue_position = int(
        db.scalar(
            select(func.count(Appointment.id)).where(
                Appointment.course_id == course_id,
                Appointment.status == "waitlisted",
                Appointment.create_time <= now,
            )
        )
        or 1
    )
    notify_member(
        db,
        member_id=member.id,
        type="waitlist_joined",
        title="已加入课程候补",
        content=(
            f"您已加入“{course.name}”候补队列，当前排位约第"
            f" {queue_position} 位。"
        ),
        related_id=appointment.id,
    )
    db.flush()


def _promote_waitlist(db: Session, course: Course) -> Appointment | None:
    if course.status != 1 or not course.start_time or course.start_time <= datetime.now():
        return None
    next_appointment = db.scalar(
        select(Appointment)
        .where(
            Appointment.course_id == course.id,
            Appointment.status == "waitlisted",
        )
        .order_by(Appointment.create_time, Appointment.id)
        .limit(1)
        .with_for_update()
    )
    if next_appointment is None:
        return None
    next_appointment.status = "pending_confirmation"
    next_appointment.update_time = datetime.now()
    course.booked_count += 1
    _record_action(
        db,
        appointment_id=next_appointment.id,
        member_id=next_appointment.member_id,
        course_id=course.id,
        action="waitlist_offer",
        detail=f"候补递补：{course.name}",
    )
    notify_member(
        db,
        member_id=next_appointment.member_id,
        type="waitlist_offer",
        title="候补名额已释放",
        content=(
            f"“{course.name}”已有空余名额，请在"
            f" {settings.waitlist_offer_minutes} 分钟内确认预约。"
        ),
        related_id=next_appointment.id,
    )
    return next_appointment


def cancel(db: Session, appointment_id: int, member_id: int | None, admin: bool) -> None:
    appointment = db.scalar(
        select(Appointment)
        .where(Appointment.id == appointment_id)
        .with_for_update()
    )
    if appointment is None:
        raise BusinessException("预约不存在")
    if not admin and appointment.member_id != member_id:
        raise BusinessException("不能取消别人的预约")
    if appointment.status != "reserved":
        raise BusinessException("该预约已取消")

    course = db.scalar(
        select(Course)
        .where(Course.id == appointment.course_id)
        .with_for_update()
    )
    appointment.status = "canceled"
    appointment.update_time = datetime.now()
    if course is not None and course.booked_count > 0:
        course.booked_count -= 1
        course.update_time = datetime.now()
    _record_action(
        db,
        appointment_id=appointment.id,
        member_id=appointment.member_id,
        course_id=appointment.course_id,
        action="cancel",
        detail=f"取消预约：{course.name if course else appointment.course_id}",
    )
    if course is not None:
        _promote_waitlist(db, course)
    db.flush()


def confirm_waitlist_offer(
    db: Session,
    appointment_id: int,
    member_id: int | None,
) -> None:
    appointment = db.scalar(
        select(Appointment)
        .where(Appointment.id == appointment_id)
        .with_for_update()
    )
    if appointment is None:
        raise BusinessException("候补记录不存在")
    if appointment.member_id != member_id:
        raise BusinessException("不能确认别人的候补名额")
    if appointment.status != "pending_confirmation":
        raise BusinessException("当前没有待确认的候补名额")
    expires_at = appointment.update_time + timedelta(
        minutes=settings.waitlist_offer_minutes
    )
    if expires_at < datetime.now():
        raise BusinessException("候补确认已超时，名额已释放")
    course = db.scalar(
        select(Course)
        .where(Course.id == appointment.course_id)
        .with_for_update()
    )
    if course is None or course.status != 1:
        raise BusinessException("课程不存在或已停课")
    appointment.status = "reserved"
    appointment.update_time = datetime.now()
    _record_action(
        db,
        appointment_id=appointment.id,
        member_id=appointment.member_id,
        course_id=appointment.course_id,
        action="waitlist_confirm",
        detail=f"确认候补预约：{course.name}",
    )
    notify_member(
        db,
        member_id=appointment.member_id,
        type="waitlist_confirmed",
        title="候补预约已确认",
        content=f"您已成功预约“{course.name}”。",
        related_id=appointment.id,
    )
    db.flush()


def decline_waitlist_offer(
    db: Session,
    appointment_id: int,
    member_id: int | None,
) -> None:
    appointment = db.scalar(
        select(Appointment)
        .where(Appointment.id == appointment_id)
        .with_for_update()
    )
    if appointment is None:
        raise BusinessException("候补记录不存在")
    if appointment.member_id != member_id:
        raise BusinessException("不能放弃别人的候补名额")
    if appointment.status not in {"waitlisted", "pending_confirmation"}:
        raise BusinessException("当前记录不在候补状态")
    was_offer = appointment.status == "pending_confirmation"
    appointment.status = "canceled"
    appointment.update_time = datetime.now()
    course = db.scalar(
        select(Course)
        .where(Course.id == appointment.course_id)
        .with_for_update()
    )
    if was_offer and course is not None and course.booked_count > 0:
        course.booked_count -= 1
        if course.start_time and course.start_time > datetime.now():
            _promote_waitlist(db, course)
    _record_action(
        db,
        appointment_id=appointment.id,
        member_id=appointment.member_id,
        course_id=appointment.course_id,
        action="waitlist_decline",
        detail=f"退出候补：{course.name if course else appointment.course_id}",
    )
    db.flush()


def expire_waitlist_offers(db: Session) -> int:
    cutoff = datetime.now() - timedelta(minutes=settings.waitlist_offer_minutes)
    appointments = list(
        db.scalars(
            select(Appointment)
            .where(
                Appointment.status == "pending_confirmation",
                Appointment.update_time < cutoff,
            )
            .order_by(Appointment.update_time)
            .with_for_update()
        ).all()
    )
    for appointment in appointments:
        appointment.status = "canceled"
        appointment.update_time = datetime.now()
        course = db.scalar(
            select(Course)
            .where(Course.id == appointment.course_id)
            .with_for_update()
        )
        if course is not None and course.booked_count > 0:
            course.booked_count -= 1
            if course.start_time and course.start_time > datetime.now():
                _promote_waitlist(db, course)
        notify_member(
            db,
            member_id=appointment.member_id,
            type="waitlist_expired",
            title="候补确认已超时",
            content="您未在规定时间内确认候补名额，名额已顺延给下一位会员。",
            related_id=appointment.id,
        )
        _record_action(
            db,
            appointment_id=appointment.id,
            member_id=appointment.member_id,
            course_id=appointment.course_id,
            action="waitlist_expire",
            detail="候补确认超时",
        )
    return len(appointments)


def change_course(
    db: Session,
    appointment_id: int,
    member_id: int,
    new_course_id: int,
) -> None:
    appointment = db.scalar(
        select(Appointment)
        .where(Appointment.id == appointment_id)
        .with_for_update()
    )
    if appointment is None:
        raise BusinessException("预约不存在")
    if appointment.member_id != member_id:
        raise BusinessException("不能修改别人的预约")
    if appointment.status != "reserved":
        raise BusinessException("该预约已取消，无法改约")
    if appointment.course_id == new_course_id:
        raise BusinessException("新课程与原课程相同")

    locked_courses = {
        course.id: course
        for course in db.scalars(
            select(Course)
            .where(Course.id.in_([appointment.course_id, new_course_id]))
            .order_by(Course.id)
            .with_for_update()
        ).all()
    }
    target_course = locked_courses.get(new_course_id)
    old_course = locked_courses.get(appointment.course_id)
    if target_course is None:
        raise BusinessException("新课程不存在")
    if target_course.status != 1:
        raise BusinessException("新课程已停课")
    if target_course.booked_count >= target_course.capacity:
        raise BusinessException("新课程已满")

    existing_target = db.scalar(
        select(Appointment)
        .where(
            Appointment.member_id == member_id,
            Appointment.course_id == new_course_id,
        )
        .with_for_update()
    )
    if existing_target is not None and existing_target.status == "reserved":
        raise BusinessException("该会员已预约新课程")

    appointment.status = "canceled"
    appointment.update_time = datetime.now()
    if old_course is not None and old_course.booked_count > 0:
        old_course.booked_count -= 1
        old_course.update_time = datetime.now()

    if existing_target is not None:
        existing_target.status = "reserved"
        existing_target.update_time = datetime.now()
    else:
        db.add(
            Appointment(
                member_id=member_id,
                course_id=new_course_id,
                status="reserved",
            )
        )
    target_course.booked_count += 1
    target_course.update_time = datetime.now()
    try:
        db.flush()
        _record_action(
            db,
            appointment_id=appointment.id,
            member_id=member_id,
            course_id=appointment.course_id,
            target_course_id=new_course_id,
            action="change",
            detail=(
                f"改约：{old_course.name if old_course else appointment.course_id}"
                f" -> {target_course.name}"
            ),
        )
        db.flush()
    except IntegrityError as exception:
        raise BusinessException("改约失败，请刷新预约后重试") from exception
