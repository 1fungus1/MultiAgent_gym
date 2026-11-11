from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.models import Appointment, Coach, Course
from app.schemas import CoursePayload, CourseVO, PageResult
from app.services.query_service import list_courses, to_course_vo


def page_courses(
    db: Session, page_num: int, page_size: int, keyword: str | None
) -> PageResult[CourseVO]:
    current = max(page_num, 1)
    size = min(max(page_size, 1), 100)
    search_text = (keyword or "").strip()

    statement = select(Course, Coach.name).outerjoin(Coach, Course.coach_id == Coach.id)
    count_statement = select(func.count(Course.id))
    if search_text:
        statement = statement.where(Course.name.like(f"%{search_text}%"))
        count_statement = count_statement.where(Course.name.like(f"%{search_text}%"))

    total = int(db.scalar(count_statement) or 0)
    rows = db.execute(
        statement.order_by(Course.start_time, Course.id.desc())
        .offset((current - 1) * size)
        .limit(size)
    ).all()
    return PageResult(
        records=[to_course_vo(course, coach_name) for course, coach_name in rows],
        total=total,
        page_num=current,
        page_size=size,
    )


def _check_course(db: Session, course: Course) -> None:
    if not course.name or not course.name.strip():
        raise BusinessException("请输入课程名称")
    if course.coach_id is None:
        raise BusinessException("请选择授课教练")
    if db.get(Coach, course.coach_id) is None:
        raise BusinessException("授课教练不存在")
    if course.start_time is None or course.end_time is None:
        raise BusinessException("请选择课程时间")
    if course.start_time < datetime.now():
        raise BusinessException("课程开始时间不能早于当前时间")
    if course.start_time >= course.end_time:
        raise BusinessException("开始时间必须早于结束时间")
    if course.capacity is None or course.capacity <= 0:
        raise BusinessException("人数上限必须大于0")
    if course.booked_count is None or course.booked_count < 0:
        raise BusinessException("已预约人数不能小于0")
    if course.booked_count > course.capacity:
        raise BusinessException("已预约人数不能超过人数上限")


def create_course(db: Session, payload: CoursePayload) -> None:
    course = Course(
        name=payload.name,
        type=payload.type,
        coach_id=payload.coach_id,
        start_time=payload.start_time,
        end_time=payload.end_time,
        capacity=payload.capacity if payload.capacity is not None else 20,
        booked_count=payload.booked_count if payload.booked_count is not None else 0,
        status=payload.status if payload.status is not None else 1,
    )
    _check_course(db, course)
    db.add(course)
    db.flush()


def update_course(db: Session, course_id: int, payload: CoursePayload) -> None:
    course = db.get(Course, course_id)
    if course is None:
        raise BusinessException("课程不存在")
    if course.end_time and course.end_time < datetime.now():
        raise BusinessException("已结束的课程不能修改")

    changes = payload.model_dump(exclude_unset=True, exclude={"id"})
    for field, value in changes.items():
        setattr(course, field, value)
    _check_course(db, course)
    db.flush()


def delete_course(db: Session, course_id: int) -> None:
    course = db.get(Course, course_id)
    if course is None:
        raise BusinessException("课程不存在")
    reserved_count = int(
        db.scalar(
            select(func.count(Appointment.id)).where(
                Appointment.course_id == course_id,
                Appointment.status == "reserved",
            )
        )
        or 0
    )
    if reserved_count > 0:
        raise BusinessException("课程还有有效预约，不能删除")
    db.execute(delete(Appointment).where(Appointment.course_id == course_id))
    db.delete(course)
    db.flush()


def available_courses(db: Session) -> list[CourseVO]:
    now = datetime.now()
    statement = (
        select(Course, Coach.name)
        .outerjoin(Coach, Course.coach_id == Coach.id)
        .where(
            Course.status == 1,
            Course.start_time > now,
            Course.booked_count < Course.capacity,
        )
        .order_by(Course.start_time, Course.id.desc())
    )
    return [
        to_course_vo(course, coach_name)
        for course, coach_name in db.execute(statement).all()
    ]


def member_course_options(db: Session) -> list[CourseVO]:
    now = datetime.now()
    statement = (
        select(Course, Coach.name)
        .outerjoin(Coach, Course.coach_id == Coach.id)
        .where(
            Course.status == 1,
            Course.start_time > now,
        )
        .order_by(Course.start_time, Course.id.desc())
    )
    return [
        to_course_vo(course, coach_name)
        for course, coach_name in db.execute(statement).all()
    ]


def all_courses(db: Session) -> list[CourseVO]:
    return list_courses(db)
