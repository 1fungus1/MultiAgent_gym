from datetime import datetime

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models import Appointment, Coach, Course, Member
from app.schemas import AppointmentVO, CourseVO


def course_time_status(course: Course, now: datetime | None = None) -> str:
    if course.status == 0:
        return "停课"
    current_time = now or datetime.now()
    if course.start_time and current_time < course.start_time:
        return "未开始"
    if course.end_time and current_time > course.end_time:
        return "已结束"
    return "进行中"


def to_course_vo(course: Course, coach_name: str | None) -> CourseVO:
    remaining = max(course.capacity - course.booked_count, 0)
    return CourseVO(
        id=course.id,
        name=course.name,
        type=course.type,
        coach_id=course.coach_id,
        coach_name=coach_name or "-",
        start_time=course.start_time,
        end_time=course.end_time,
        capacity=course.capacity,
        booked_count=course.booked_count,
        remaining=remaining,
        can_waitlist=bool(
            course.status == 1
            and course.start_time
            and course.start_time > datetime.now()
            and remaining == 0
        ),
        status=course.status,
        time_status=course_time_status(course),
    )


def course_rows_statement() -> Select:
    return (
        select(Course, Coach.name.label("coach_name"))
        .outerjoin(Coach, Course.coach_id == Coach.id)
        .order_by(Course.start_time, Course.id.desc())
    )


def appointment_rows_statement() -> Select:
    return (
        select(
            Appointment,
            Member.name.label("member_name"),
            Course.name.label("course_name"),
            Course.start_time.label("course_time"),
            Course.end_time.label("course_end_time"),
            Coach.name.label("coach_name"),
        )
        .outerjoin(Member, Appointment.member_id == Member.id)
        .outerjoin(Course, Appointment.course_id == Course.id)
        .outerjoin(Coach, Course.coach_id == Coach.id)
        .order_by(Appointment.create_time.desc(), Appointment.id.desc())
    )


def to_appointment_vo(row: object) -> AppointmentVO:
    (
        appointment,
        member_name,
        course_name,
        course_time,
        course_end_time,
        coach_name,
    ) = row  # type: ignore[misc]
    return AppointmentVO(
        id=appointment.id,
        member_id=appointment.member_id,
        member_name=member_name or "-",
        course_id=appointment.course_id,
        course_name=course_name or "-",
        coach_name=coach_name or "-",
        course_time=course_time,
        course_end_time=course_end_time,
        status=appointment.status,
        create_time=appointment.create_time,
        update_time=appointment.update_time,
    )


def list_courses(db: Session) -> list[CourseVO]:
    rows = db.execute(course_rows_statement()).all()
    return [to_course_vo(course, coach_name) for course, coach_name in rows]


def list_appointments(db: Session) -> list[AppointmentVO]:
    return [to_appointment_vo(row) for row in db.execute(appointment_rows_statement()).all()]
