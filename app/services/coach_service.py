from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.models import Coach, Course
from app.schemas import CoachPayload, CoachVO, PageResult


def list_coaches(db: Session) -> list[Coach]:
    return list(db.scalars(select(Coach).order_by(Coach.id.desc())).all())


def page_coaches(
    db: Session, page_num: int, page_size: int, keyword: str | None
) -> PageResult[CoachVO]:
    current = max(page_num, 1)
    size = min(max(page_size, 1), 100)
    search_text = (keyword or "").strip()

    statement = select(Coach)
    count_statement = select(func.count(Coach.id))
    if search_text:
        statement = statement.where(Coach.name.like(f"%{search_text}%"))
        count_statement = count_statement.where(Coach.name.like(f"%{search_text}%"))

    total = int(db.scalar(count_statement) or 0)
    records = list(
        db.scalars(
            statement.order_by(Coach.id.desc())
            .offset((current - 1) * size)
            .limit(size)
        ).all()
    )
    return PageResult(
        records=[CoachVO.model_validate(coach) for coach in records],
        total=total,
        page_num=current,
        page_size=size,
    )


def create_coach(db: Session, payload: CoachPayload) -> None:
    if not payload.name:
        raise BusinessException("教练姓名不能为空")
    coach = Coach(
        name=payload.name,
        phone=payload.phone,
        specialty=payload.specialty,
        entry_date=payload.entry_date,
        status=payload.status if payload.status is not None else 1,
    )
    db.add(coach)
    db.flush()


def update_coach(db: Session, coach_id: int, payload: CoachPayload) -> None:
    coach = db.get(Coach, coach_id)
    if coach is None:
        raise BusinessException("教练不存在")
    changes = payload.model_dump(exclude_unset=True, exclude={"id"})
    for field, value in changes.items():
        setattr(coach, field, value)
    if not coach.name:
        raise BusinessException("教练姓名不能为空")
    db.flush()


def delete_coach(db: Session, coach_id: int) -> None:
    coach = db.get(Coach, coach_id)
    if coach is None:
        raise BusinessException("教练不存在")
    course_count = int(
        db.scalar(select(func.count(Course.id)).where(Course.coach_id == coach_id)) or 0
    )
    if course_count > 0:
        raise BusinessException("该教练已有课程关联，不能删除")
    db.delete(coach)
    db.flush()
